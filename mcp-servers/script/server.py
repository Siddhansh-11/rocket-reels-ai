import asyncio
import json
import os
from typing import Dict, Any, List
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from mcp.types import Tool, TextContent
import anthropic
import textstat
import re

# Initialize MCP server
server = Server("script-writer")

# Initialize Anthropic client
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Reel writing principles
REEL_WRITING_PRINCIPLES = """
1. Hook in first 3 seconds - question, shocking fact, or bold claim
2. One idea per sentence, max 15 words
3. Active voice only
4. Pattern interrupts every 7-10 seconds
5. Clear CTA in final 5 seconds
6. Write for 8th grade reading level
7. Use power words and emotional triggers
8. Create visual cues in the script
"""

PROVEN_TEMPLATES = {
    "problem_solution": {
        "structure": "Hook → Problem → Agitate → Solution → CTA",
        "timing": [3, 10, 10, 30, 7]  # seconds for each section
    },
    "listicle": {
        "structure": "Hook → Number promise → Points → Recap → CTA",
        "timing": [3, 5, 40, 7, 5]
    },
    "story": {
        "structure": "Hook → Setup → Conflict → Resolution → Lesson → CTA",
        "timing": [3, 10, 15, 20, 7, 5]
    },
    "educational": {
        "structure": "Hook → Why it matters → Key points → Example → CTA",
        "timing": [3, 7, 35, 10, 5]
    }
}

# High-performing hook templates
HOOK_TEMPLATES = [
    "Stop scrolling! This {topic} will {benefit}",
    "99% of people don't know this about {topic}",
    "The {adjective} truth about {topic} that nobody talks about",
    "POV: You just discovered {discovery}",
    "Warning: This {topic} hack might {outcome}",
    "I was today years old when I learned {fact}",
    "{number} {topic} mistakes you're making right now",
    "This {time_period} {topic} trend is changing everything"
]

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available script writing tools"""
    return [
        Tool(
            name="generate_script",
            description="Generate script following reel best practices",
            inputSchema={
                "type": "object",
                "properties": {
                    "plan": {
                        "type": "object",
                        "description": "Content plan from planner",
                        "properties": {
                            "hook": {"type": "string"},
                            "main_points": {"type": "array"},
                            "cta": {"type": "string"}
                        }
                    },
                    "style": {
                        "type": "string",
                        "description": "Script style",
                        "enum": ["energetic", "calm", "humorous", "serious", "inspirational"],
                        "default": "energetic"
                    },
                    "template": {
                        "type": "string",
                        "description": "Script template to use",
                        "enum": ["problem_solution", "listicle", "story", "educational"],
                        "default": "educational"
                    }
                },
                "required": ["plan"]
            }
        ),
        Tool(
            name="polish_script",
            description="Polish and optimize an existing script",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "Script to polish"
                    },
                    "focus": {
                        "type": "string",
                        "description": "What to focus on",
                        "enum": ["hooks", "pacing", "clarity", "emotion"],
                        "default": "pacing"
                    }
                },
                "required": ["script"]
            }
        ),
        Tool(
            name="validate_script",
            description="Validate script against best practices",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "Script to validate"
                    }
                },
                "required": ["script"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list:
    """Handle tool execution"""
    
    if name == "generate_script":
        style = arguments.get("style", "energetic")
        template = arguments.get("template", "educational")
        result = await generate_script(arguments["plan"], style, template)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "polish_script":
        focus = arguments.get("focus", "pacing")
        result = await polish_script(arguments["script"], focus)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "validate_script":
        result = await validate_script(arguments["script"])
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def generate_script(plan: Dict[str, Any], style: str, template: str) -> Dict[str, Any]:
    """Generate script following reel best practices"""
    
    # Get template structure
    template_info = PROVEN_TEMPLATES.get(template, PROVEN_TEMPLATES["educational"])
    
    # Load example scripts (would be from a database in production)
    examples = get_example_scripts(style, template)
    
    prompt = f"""
    {REEL_WRITING_PRINCIPLES}
    
    Template: {template_info['structure']}
    Style: {style}
    
    Examples of successful {style} scripts:
    {examples}
    
    Now write a {style} script for:
    - Hook suggestion: {plan.get('hook', '')}
    - Main points: {json.dumps(plan.get('main_points', []))}
    - CTA: {plan.get('cta', '')}
    
    Requirements:
    1. Total duration: 30-60 seconds when spoken
    2. Use conversational language
    3. Include [VISUAL: description] cues for each scene
    4. Mark [PAUSE] for dramatic effect
    5. Use ALL CAPS for emphasis words
    6. End with clear action item
    
    Format the script with clear section markers.
    """
    
    message = anthropic_client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1500,
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}]
    )
    
    script = message.content[0].text
    
    # Validate the generated script
    validation = await validate_script(script)
    
    # Calculate speaking duration (average 150 words per minute)
    word_count = len(script.split())
    estimated_duration = (word_count / 150) * 60  # seconds
    
    return {
        "script": script,
        "template_used": template,
        "style": style,
        "word_count": word_count,
        "estimated_duration": round(estimated_duration, 1),
        "sections": parse_script_sections(script),
        "visual_cues": extract_visual_cues(script),
        "emphasis_words": extract_emphasis_words(script),
        "validation": validation,
        "quality_score": calculate_quality_score(validation)
    }

async def polish_script(script: str, focus: str) -> Dict[str, Any]:
    """Polish and optimize an existing script"""
    
    polish_prompts = {
        "hooks": "Make the opening hook more compelling and attention-grabbing",
        "pacing": "Improve pacing with better rhythm and pattern interrupts",
        "clarity": "Simplify language and make ideas clearer",
        "emotion": "Add more emotional triggers and power words"
    }
    
    prompt = f"""
    Polish this reel script with focus on: {polish_prompts.get(focus, 'overall improvement')}
    
    Current script:
    {script}
    
    {REEL_WRITING_PRINCIPLES}
    
    Maintain the same core message but enhance the {focus}.
    Keep visual cues and timing markers.
    """
    
    message = anthropic_client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1500,
        temperature=0.6,
        messages=[{"role": "user", "content": prompt}]
    )
    
    polished_script = message.content[0].text
    
    # Compare before and after
    original_validation = await validate_script(script)
    new_validation = await validate_script(polished_script)
    
    return {
        "original_script": script,
        "polished_script": polished_script,
        "focus": focus,
        "improvements": {
            "readability": new_validation["readability_score"] - original_validation["readability_score"],
            "hook_strength": new_validation["hook_strength"] - original_validation["hook_strength"],
            "cta_clarity": new_validation["cta_clarity"] - original_validation["cta_clarity"]
        },
        "new_validation": new_validation
    }

async def validate_script(script: str) -> Dict[str, Any]:
    """Check script against best practices"""
    
    # Analyze hook (first 50 characters)
    hook_text = script[:100]
    hook_strength = analyze_hook(hook_text)
    
    # Calculate readability
    readability_score = textstat.flesch_reading_ease(script)
    grade_level = textstat.flesch_kincaid_grade(script)
    
    # Check CTA clarity (last 150 characters)
    cta_text = script[-150:]
    cta_clarity = check_cta(cta_text)
    
    # Analyze pacing
    sentences = script.split('.')
    avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
    
    # Count pattern interrupts (visual cues, pauses, emphasis)
    pattern_interrupts = len(re.findall(r'\[VISUAL:|PAUSE|\b[A-Z]{2,}\b', script))
    
    # Check for power words
    power_words = ["stop", "now", "free", "new", "proven", "secret", "instant", "discover", "transform", "breakthrough"]
    power_word_count = sum(1 for word in power_words if word.lower() in script.lower())
    
    return {
        "hook_strength": hook_strength,
        "readability_score": round(readability_score, 1),
        "grade_level": round(grade_level, 1),
        "cta_clarity": cta_clarity,
        "avg_sentence_length": round(avg_sentence_length, 1),
        "pattern_interrupts": pattern_interrupts,
        "power_word_count": power_word_count,
        "issues": identify_issues(script, readability_score, grade_level, avg_sentence_length),
        "strengths": identify_strengths(script, hook_strength, cta_clarity, power_word_count)
    }

def analyze_hook(hook_text: str) -> float:
    """Analyze hook strength (0-100)"""
    score = 50  # Base score
    
    # Check for question
    if '?' in hook_text:
        score += 10
    
    # Check for numbers
    if any(char.isdigit() for char in hook_text):
        score += 10
    
    # Check for power words in hook
    hook_power_words = ["stop", "warning", "secret", "mistake", "truth"]
    if any(word in hook_text.lower() for word in hook_power_words):
        score += 15
    
    # Check for direct address
    if any(word in hook_text.lower() for word in ["you", "your"]):
        score += 10
    
    # Length check (should be concise)
    if len(hook_text.split()) <= 10:
        score += 5
    
    return min(score, 100)

def check_cta(cta_text: str) -> float:
    """Check CTA clarity (0-100)"""
    score = 50  # Base score
    
    # Check for action verbs
    action_verbs = ["click", "follow", "share", "comment", "save", "try", "start", "get", "join"]
    if any(verb in cta_text.lower() for verb in action_verbs):
        score += 20
    
    # Check for urgency
    urgency_words = ["now", "today", "immediately", "before", "limited"]
    if any(word in cta_text.lower() for word in urgency_words):
        score += 15
    
    # Check for specificity
    if any(char.isdigit() for char in cta_text) or "step" in cta_text.lower():
        score += 15
    
    return min(score, 100)

def parse_script_sections(script: str) -> List[Dict[str, str]]:
    """Parse script into sections based on structure"""
    sections = []
    
    # Simple parsing based on line breaks and markers
    current_section = {"content": "", "type": "intro"}
    
    for line in script.split('\n'):
        if line.strip():
            if any(marker in line.upper() for marker in ["HOOK:", "PROBLEM:", "SOLUTION:", "CTA:"]):
                if current_section["content"]:
                    sections.append(current_section)
                section_type = line.split(':')[0].lower() if ':' in line else "content"
                current_section = {"content": line, "type": section_type}
            else:
                current_section["content"] += "\n" + line
    
    if current_section["content"]:
        sections.append(current_section)
    
    return sections

def extract_visual_cues(script: str) -> List[str]:
    """Extract visual cues from script"""
    visual_pattern = r'\[VISUAL:\s*([^\]]+)\]'
    return re.findall(visual_pattern, script)

def extract_emphasis_words(script: str) -> List[str]:
    """Extract emphasized words (all caps)"""
    emphasis_pattern = r'\b[A-Z]{2,}\b'
    return re.findall(emphasis_pattern, script)

def calculate_quality_score(validation: Dict[str, Any]) -> float:
    """Calculate overall quality score (0-100)"""
    scores = [
        validation["hook_strength"],
        validation["readability_score"] / 100 * 80,  # Normalize to 0-80
        validation["cta_clarity"],
        min(validation["pattern_interrupts"] * 10, 50),  # Cap at 50
        min(validation["power_word_count"] * 5, 25)  # Cap at 25
    ]
    
    # Penalties
    if validation["grade_level"] > 9:
        scores.append(-10)
    if validation["avg_sentence_length"] > 15:
        scores.append(-5)
    
    return max(0, min(100, sum(scores) / len([s for s in scores if s > 0]) * 1.2))

def identify_issues(script: str, readability: float, grade_level: float, avg_sentence_length: float) -> List[str]:
    """Identify potential issues with the script"""
    issues = []
    
    if readability < 60:
        issues.append("Readability too low - simplify language")
    if grade_level > 9:
        issues.append(f"Grade level too high ({grade_level}) - target 8th grade")
    if avg_sentence_length > 15:
        issues.append(f"Sentences too long (avg {avg_sentence_length} words)")
    if len(script.split()) > 180:
        issues.append("Script too long - aim for under 180 words")
    if len(script.split()) < 80:
        issues.append("Script too short - aim for 80-180 words")
    
    return issues

def identify_strengths(script: str, hook_strength: float, cta_clarity: float, power_word_count: int) -> List[str]:
    """Identify strengths of the script"""
    strengths = []
    
    if hook_strength > 70:
        strengths.append("Strong opening hook")
    if cta_clarity > 70:
        strengths.append("Clear call-to-action")
    if power_word_count >= 3:
        strengths.append(f"Good use of power words ({power_word_count})")
    if '[VISUAL:' in script:
        strengths.append("Includes visual direction")
    if '[PAUSE]' in script:
        strengths.append("Uses strategic pauses")
    
    return strengths

def get_example_scripts(style: str, template: str) -> str:
    """Get example scripts for the given style and template"""
    # In production, these would come from a database of high-performing scripts
    examples = {
        "energetic": {
            "educational": """
[VISUAL: Close-up of shocked face]
Stop scrolling! 99% of people are using ChatGPT WRONG.

[VISUAL: Screen recording of ChatGPT]
Here's the SECRET pros don't want you to know...

[PAUSE]

[VISUAL: Split screen comparison]
Instead of basic prompts, use THIS framework:
1. Give it a ROLE
2. Provide CONTEXT  
3. Specify the OUTPUT format

[VISUAL: Real example being typed]
Watch this: "You're an expert copywriter. Write 5 hooks for my fitness app targeting busy moms. Format as bullet points."

[VISUAL: Amazing results appearing]
BOOM! Professional-level content in seconds.

[VISUAL: Call-to-action overlay]
Save this NOW and follow for more AI hacks that'll 10x your productivity!
"""
        }
    }
    
    return examples.get(style, {}).get(template, "No examples available")

async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="script-writer",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())