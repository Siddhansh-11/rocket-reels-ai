from langchain_core.tools import tool
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import HumanMessage
from typing import Dict, Any, List
import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Deepseek LLM for script generation
deepseek_model = ChatLiteLLM(
    model="deepseek/deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    max_tokens=4000,
    temperature=0.5
)

@tool
async def generate_youtube_script(
    article_content: str,
    article_title: str,
    platform: str = "youtube",
    duration: int = 60
) -> str:
    """
    Generate a voiceover-friendly YouTube script in Varun Mayya's style from article content using AI.
    
    Args:
        article_content: The actual article content to base the script on
        article_title: Title of the article
        platform: Target platform (youtube, tiktok, etc.)
        duration: Target duration in seconds
        
    Returns:
        Plain text script optimized for voiceover
    """
    try:
        print(f"Generating {platform} script in Varun Mayya's style from article content...")
        print(f"Article title: {article_title}")
        print(f"Content length: {len(article_content)} characters")
        
        # Clean and prepare the article content
        clean_content = clean_article_content(article_content)
        clean_title = clean_article_title(article_title)
        
        # Calculate target word count based on duration
        if duration <= 30:
            target_words = 75
        elif duration <= 60:
            target_words = 150
        elif duration <= 180:
            target_words = 450
        else:
            target_words = 900
        
        # Create the script generation prompt
        # Replace your existing script_prompt with this improved version:

        script_prompt = f"""You are an expert YouTube script writer who emulates Varun Mayya's engaging, conversational, and energetic style, creating voiceover-friendly content that captivates a tech-savvy audience.

        Your task is to create a compelling {duration}-second YouTube script based on this article content, styled like Varun Mayya's videos.

        ARTICLE TITLE: {clean_title}

        ARTICLE CONTENT:
        {clean_content}

        SCRIPT REQUIREMENTS:
        - Target duration: {duration} seconds (~{target_words} words)
        - Platform: {platform.upper()}
        - Style: Engaging, conversational, energetic, and relatable, like Varun Mayya. Use short, punchy sentences and address the audience directly (e.g., "you"). Simplify technical concepts for a broad audience and include storytelling elements to make it exciting.
        - Include a strong hook in the first 5 seconds that poses a question or bold statement to grab attention.
        - Use natural, spoken language that sounds clear when read aloud.
        - Focus on the most engaging insights from the article, avoiding generic templates.
        - Avoid emoticons, bold text, or formatting markers (e.g., **, *, -).
        - Use plain text with section headers in square brackets (e.g., [0-5s: HOOK]).
        - Base the script ENTIRELY on the provided article content, using specific details, companies, or features mentioned.
        - Do NOT include metadata (e.g., timestamps, source links, or publication details) in the script.
        - Make the content feel personal, like you're explaining it to a friend excited about tech.

        CRITICAL SPACING REQUIREMENTS:
        - ALWAYS ensure proper spacing between all words
        - NEVER merge words together (e.g., avoid "gadgetit's" - write "gadget it's")
        - ALWAYS add spaces after punctuation before the next word
        - Double-check that every sentence flows naturally with proper spacing
        - Pay special attention to compound words and contractions

        SCRIPT STRUCTURE:
        [0-5s: HOOK]
        [5-15s: INTRODUCTION] 
        [15-45s: MAIN CONTENT]
        [45-60s: CONCLUSION/CTA]

        STRICT FORMATTING RULES:
        1. Use EXACTLY these section headers with proper spacing and capitalization
        2. Each section must contain at least 2 sentences
        3. Never combine sections
        4. Maintain proper spacing between ALL words and punctuation
        5. Do not include any timestamps beyond the section headers
        6. Do not include any metadata (e.g., source links, publication details)
        7. Do not include any emoticons or formatting markers
        8. Carefully proofread each sentence to ensure no words are merged together

        OUTPUT FORMAT:
        Return ONLY the plain text script with the specified section headers, like this:
        [0-5s: HOOK]
        Hook content here with proper spacing between all words

        [5-15s: INTRODUCTION]
        Introduction content here with proper spacing between all words

        [15-45s: MAIN CONTENT]
        Main content here with proper spacing between all words

        [45-60s: CONCLUSION/CTA]
        Conclusion and call to action here with proper spacing between all words

        FINAL CHECK: Before outputting, read through your entire script and verify that:
        - Every word is properly separated by spaces
        - No words are accidentally merged together
        - Punctuation is followed by appropriate spacing
        - The script reads naturally when spoken aloud

        If the article content is long or complex, summarize the 3-5 most engaging points (e.g., key features, real-world impacts, or exciting developments). Do not include any additional text, metadata, or notes outside the script structure."""
        
        # Generate script using Deepseek
        print("Calling DeepSeek LLM for script generation...")
        response = await deepseek_model.ainvoke([HumanMessage(content=script_prompt)])
        generated_script = response.content.strip()
        
        print(f"Raw LLM response: {generated_script[:200]}...")
        print(f"Generated script length: {len(generated_script)} characters")
        
        # Validate and clean the script
        clean_script = clean_generated_script(generated_script, clean_content, clean_title, duration)
        
        if not clean_script or clean_script.count("Placeholder content") >= 3:
            print("Falling back to basic script generation due to invalid LLM response")
            clean_script = generate_fallback_script(clean_content, clean_title, duration)
        
        return clean_script
        
    except Exception as e:
        print(f"Error generating script: {str(e)}")
        clean_content = clean_article_content(article_content)
        clean_title = clean_article_title(article_title)
        return generate_fallback_script(clean_content, clean_title, duration)

def clean_article_content(content: str) -> str:
    """Clean and prepare article content for script generation"""
    if not content:
        return "No content provided"
    
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'Skip to main content', '', content)
    content = re.sub(r'Cookie policy|Privacy policy|Terms of service', '', content, flags=re.IGNORECASE)
    content = re.sub(r'Stay organized with collections\s*Save and categorize content based on your preferences\.?', '', content)
    # Remove metadata like timestamps and source info
    content = re.sub(r'Latest Update\s*\d{1,2}/\d{1,2}/\d{4}\s*\d{1,2}:\d{2}:\d{2}\s*[AP]M', '', content)
    content = re.sub(r'\(source:.*?\)', '', content)
    
    if len(content) > 2000:  # Reduced to focus on key content
        content = content[:2000] + "..."
    
    return content.strip()

def clean_article_title(title: str) -> str:
    """Clean and prepare article title"""
    if not title:
        return "Technology News"
    
    title = re.sub(r'Stay organized with collections\s*Save and categorize content based on your preferences\.?', '', title)
    title = re.sub(r'\s*\|\s*AI News Detail\s*\|\s*Blockchain\.News', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    
    if len(title) < 5:
        title = "Technology News"
    
    return title

def clean_generated_script(script: str, article_content: str, article_title: str, duration: int) -> str:
    """Clean and properly format the generated script"""
    if not script:
        return generate_fallback_script(article_content, article_title, duration)
    
    # Remove emojis and unwanted characters
    script = re.sub(r'[🚀✅🔥📝📊🎬🎙️—–]', '', script)
    
    # Define the section headers in correct order
    section_headers = [
        '[0-5s: HOOK]',
        '[5-15s: INTRODUCTION]', 
        '[15-45s: MAIN CONTENT]',
        '[45-60s: CONCLUSION/CTA]'
    ]
    
    # Extract content for each section
    sections = {}
    
    # Split script by potential section markers and clean them
    for header in section_headers:
        # Try multiple variations of the header format
        patterns = [
            re.escape(header),
            re.escape(header).replace(r'\-', r'\s*\-\s*').replace(r'\:', r'\s*\:\s*'),
            re.escape(header).replace(r'\[', r'\[\s*').replace(r'\]', r'\s*\]'),
            header.replace('[', r'\[\s*').replace(']', r'\s*\]').replace(':', r'\s*:\s*').replace('-', r'\s*\-\s*')
        ]
        
        content_found = False
        for pattern in patterns:
            # Look for the section header and extract content until next section or end
            regex_pattern = f'({pattern})(.*?)(?=\[|$)'
            match = re.search(regex_pattern, script, re.DOTALL | re.IGNORECASE)
            
            if match:
                content = match.group(2).strip()
                if content and len(content) > 10:  # Ensure meaningful content
                    sections[header] = content
                    content_found = True
                    break
        
        # If no content found, try to extract from fallback
        if not content_found:
            sections[header] = generate_fallback_section(header, article_content, article_title, duration)
    
    # Reconstruct the script in proper format
    formatted_script = []
    
    for header in section_headers:
        content = sections.get(header, generate_fallback_section(header, article_content, article_title, duration))
        
        # Clean the content
        content = clean_section_content(content)
        
        # Add the section
        formatted_script.append(header)
        formatted_script.append(content)
        formatted_script.append("")  # Empty line for spacing
    
    # Join and clean up final formatting
    result = '\n'.join(formatted_script).strip()
    
    # Remove any duplicate section headers that might appear in content
    for header in section_headers:
        # Remove header if it appears in the middle of content
        pattern = f'\n{re.escape(header)}\n'
        if result.count(pattern) > 1:
            # Keep only the first occurrence
            parts = result.split(pattern)
            result = pattern.join([parts[0]] + [part.replace(header, '').strip() for part in parts[1:]])
    
    return result

def clean_section_content(content: str) -> str:
    """Clean individual section content"""
    if not content:
        return "Content not available"
    
    # Fix spacing issues
    content = re.sub(r'\s+', ' ', content)
    
    # Fix punctuation spacing
    content = re.sub(r'\s+([,.!?;:])', r'\1', content)  # Remove space before punctuation
    content = re.sub(r'([,.!?;:])(?=[A-Za-z])', r'\1 ', content)  # Add space after punctuation
    
    # Fix common spacing issues
    content = re.sub(r"(\w)'(\w)", r"\1'\2", content)  # Fix contractions
    content = re.sub(r'\s*-\s*', ' - ', content)  # Fix dash spacing
    
    # Remove any section headers that might be embedded in content
    section_patterns = [
        r'\[\d+\s*-\s*\d+s\s*:\s*[A-Z/]+\]',
        r'\[.*?HOOK.*?\]',
        r'\[.*?INTRODUCTION.*?\]', 
        r'\[.*?MAIN CONTENT.*?\]',
        r'\[.*?CONCLUSION.*?\]'
    ]
    
    for pattern in section_patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)
    
    return content.strip()

def generate_fallback_section(section: str, article_content: str, article_title: str, duration: int) -> str:
    """Generate a fallback section in Varun Mayya's style"""
    # Extract key points from content
    sentences = re.split(r'[.!?]', article_content)[:5]
    sentences = [s.strip() for s in sentences if s.strip()]
    key_points = sentences[:3] if len(sentences) >= 3 else sentences + ["Exciting developments in AI!"] * (3 - len(sentences))
    
    if section == '[0-5s: HOOK]':
        return f"Can {article_title.split(':')[0]} change how you work forever?"
    elif section == '[5-15s: INTRODUCTION]':
        return f"Hey, it’s time to talk about {article_title.split(':')[0]}. This is a big deal in tech, and it could affect your job!"
    elif section == '[15-45s: MAIN CONTENT]':
        return f"Here’s the deal: {key_points[0]}. Plus, {key_points[1].lower()}. And get this: {key_points[2].lower()}. It’s wild to think how this could shake things up!"
    elif section == '[45-60s: CONCLUSION/CTA]':
        return f"Want to know more about {article_title.split(':')[0]}? Hit the link below and subscribe for the latest tech scoops!"
    return "Placeholder content for this section"

def generate_fallback_script(article_content: str, article_title: str, duration: int) -> str:
    """Generate a basic script in Varun Mayya's style when LLM fails"""
    sections = [
        '[0-5s: HOOK]',
        '[5-15s: INTRODUCTION]',
        '[15-45s: MAIN CONTENT]',
        '[45-60s: CONCLUSION/CTA]'
    ]
    script = []
    
    for section in sections:
        script.append(section)
        script.append(generate_fallback_section(section, article_content, article_title, duration))
    
    return '\n\n'.join(script).strip()

@tool
async def generate_script_variations(
    base_script: str,
    num_variations: int = 3,
    style_variations: List[str] = None
) -> str:
    """
    Generate multiple variations of a script for A/B testing.
    
    Args:
        base_script: The original script to create variations from
        num_variations: Number of variations to generate
        style_variations: List of style adjustments (e.g., ["more casual", "more technical"])
        
    Returns:
        Plain text script variations
    """
    try:
        if style_variations is None:
            style_variations = ["more casual and conversational", "more technical and detailed", "more energetic and enthusiastic"]
        
        variations = []
        
        for i, style in enumerate(style_variations[:num_variations]):
            variation_prompt = f"""Take this YouTube script and rewrite it to be {style}, while keeping the same core information and structure, in Varun Mayya's engaging, conversational style:

ORIGINAL SCRIPT:
{base_script}

STYLE ADJUSTMENT: {style}

Rewrite the script maintaining the same key information but adjusting the tone and delivery style. Keep it the same length and maintain the section structure ([0-5s: HOOK], [5-15s: INTRODUCTION], etc.). Use plain text with no emoticons or formatting markers."""

            response = await deepseek_model.ainvoke([HumanMessage(content=variation_prompt)])
            clean_variation = clean_generated_script(response.content, "", "", 60)
            variations.append(f"VARIATION {i+1} - {style.upper()}:\n{clean_variation}\n")
        
        return '\n\n'.join(variations).strip()
        
    except Exception as e:
        return f"Error generating variations: {str(e)}"

@tool
async def optimize_script_for_platform(
    script: str,
    target_platform: str,
    target_duration: int = None
) -> str:
    """
    Optimize an existing script for a specific platform.
    
    Args:
        script: The script to optimize
        target_platform: Platform to optimize for (youtube, tiktok, instagram, linkedin)
        target_duration: Target duration in seconds
        
    Returns:
        Plain text platform-optimized script
    """
    try:
        platform_specs = {
            "tiktok": {"max_duration": 60, "style": "fast-paced, trendy, hook-heavy"},
            "youtube": {"max_duration": 600, "style": "informative, engaging, detailed"},
            "instagram": {"max_duration": 90, "style": "visual-first, catchy, lifestyle-focused"},
            "linkedin": {"max_duration": 120, "style": "professional, insightful, business-focused"}
        }
        
        specs = platform_specs.get(target_platform.lower(), platform_specs["youtube"])
        duration = target_duration or specs["max_duration"]
        
        optimization_prompt = f"""Optimize this script for {target_platform.upper()} in Varun Mayya's engaging, conversational style:

ORIGINAL SCRIPT:
{script}

PLATFORM REQUIREMENTS:
- Target Duration: {duration} seconds
- Platform Style: {specs['style']}
- Max Duration: {specs['max_duration']} seconds

Rewrite the script to be perfect for {target_platform}, maintaining the core information but adjusting length, pacing, and style for maximum engagement. Use plain text with section headers ([0-5s: HOOK], [5-15s: INTRODUCTION], etc.) and no emoticons or formatting markers."""

        response = await deepseek_model.ainvoke([HumanMessage(content=optimization_prompt)])
        optimized_script = clean_generated_script(response.content, "", "", duration)
        
        return optimized_script
        
    except Exception as e:
        return f"Error optimizing script: {str(e)}"

# Export tools
script_generation_tools = [
    generate_youtube_script,
    generate_script_variations,
    optimize_script_for_platform
]