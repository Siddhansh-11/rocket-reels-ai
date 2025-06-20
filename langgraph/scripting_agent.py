# scripting_agent.py
import random
from typing import Dict, List, Any
from langchain_core.tools import tool
import re
import json

class ContentClassifier:
    def analyze_input(self, topic: str, context: Dict) -> str:
        """Determine content type based on article data."""
        title = context.get('title', '').lower()
        content = context.get('content', '').lower()
        topic = topic.lower()
        
        if any(keyword in title + content for keyword in ['vs', 'compared', 'versus', 'better than']):
            return 'comparison'
        elif any(keyword in title + content for keyword in ['trend', 'trending', 'future', 'prediction']):
            return 'trend_analysis'
        elif any(keyword in title + content for keyword in ['how to', 'tutorial', 'guide', 'step']):
            return 'tutorial'
        elif any(keyword in title + content for keyword in ['reaction', 'opinion', 'thoughts', 'analysis']):
            return 'reaction'
        elif any(keyword in title + content for keyword in ['story', 'case study', 'journey']):
            return 'storytelling'
        return 'announcement'  # Default to announcement for new tech developments

class TemplateSelector:
    def __init__(self):
        self.templates = {
            'announcement': {
                'structure': """
**Hook**: {hook}
**Context**: {context}
**Revelation**: {revelation}
**Impact**: {impact}
**Call to Action**: Follow for more tech disruptions!
""",
                'populate': lambda data: {
                    'hook': data['hook'],
                    'context': f"While everyone was focused on {data['topic']},",
                    'revelation': f"{data.get('source', 'A major company')} just announced {data['topic']}.",
                    'impact': f"This means {data.get('key_points', ['game-changing advancements in the tech industry'])[0]}."
                }
            },
            'reaction': {
                'structure': """
**Opening**: {hook}
**Setup**: {setup}
**Analysis**: {analysis}
**Implications**: {implications}
**Call to Action**: What do you think? Share your thoughts below!
""",
                'populate': lambda data: {
                    'hook': data['hook'],
                    'setup': f"In a recent development, {data.get('source', 'industry leaders')} revealed {data['topic']}.",
                    'analysis': f"Here's why this matters: {data.get('key_points', ['significant impact on the industry'])[0]}.",
                    'implications': f"This could completely change {data.get('category', 'the tech landscape')}."
                }
            },
            'tutorial': {
                'structure': """
**Hook**: {hook}
**Problem**: {problem}
**Solution**: {solution}
**Step-by-Step**: {tutorial}
**Results**: {results}
**Call to Action**: Try it yourself and share your results!
""",
                'populate': lambda data: {
                    'hook': data['hook'],
                    'problem': f"Struggling with {data['topic']}?",
                    'solution': f"Here's the exact method to master {data['topic']}.",
                    'tutorial': '\n'.join([f"Step {i+1}: {point}" for i, point in enumerate(data.get('key_points', ['Follow these proven steps']))]),
                    'results': f"This approach can save you {data.get('word_count', 300)//60} minutes daily."
                }
            },
            'trend_analysis': {
                'structure': """
**Hook**: {hook}
**Trend Overview**: {trend}
**Deep Analysis**: {deep_dive}
**Future Predictions**: {future}
**Call to Action**: Stay ahead of the curve with our insights!
""",
                'populate': lambda data: {
                    'hook': data['hook'],
                    'trend': f"Everyone's talking about {data['topic']}, but here's what they're missing.",
                    'deep_dive': data.get('summary', 'This trend is reshaping the entire industry landscape.'),
                    'future': f"In the next 12 months, this trend will lead to {data.get('key_points', ['unprecedented opportunities'])[0]}."
                }
            },
            'comparison': {
                'structure': """
**Hook**: {hook}
**Setup**: {setup}
**Comparison Criteria**: {criteria}
**Detailed Analysis**: {analysis}
**Final Verdict**: {verdict}
**Call to Action**: Which option do you prefer? Let us know!
""",
                'populate': lambda data: {
                    'hook': data['hook'],
                    'setup': f"{data['topic']} vs the competition: what's really the best choice?",
                    'criteria': "We'll compare based on performance, cost, and user experience.",
                    'analysis': data.get('summary', 'Here\'s our comprehensive analysis of all options.'),
                    'verdict': f"{data['topic']} emerges as the winner for {data.get('key_points', ['superior performance and value'])[0]}."
                }
            },
            'storytelling': {
                'structure': """
**Hook**: {hook}
**The Journey**: {journey}
**The Challenge**: {struggle}
**The Breakthrough**: {solution}
**The Transformation**: {transformation}
**Call to Action**: What's your success story? Share it below!
""",
                'populate': lambda data: {
                    'hook': data['hook'],
                    'journey': f"The story of {data['topic']} begins with an ambitious vision.",
                    'struggle': data.get('summary', 'They faced seemingly impossible technical challenges.'),
                    'solution': f"The breakthrough came when they discovered {data.get('key_points', ['an innovative approach'])[0]}.",
                    'transformation': "This led to revolutionary changes in the industry."
                }
            }
        }
    
    def select_template(self, content_type: str, context: Dict) -> Dict:
        """Select and populate the template based on content type."""
        template = self.templates.get(content_type, self.templates['announcement'])
        return {
            'structure': template['structure'],
            'populated': template['populate'](context)
        }

class HookGenerator:
    def __init__(self):
        self.hook_types = {
            'curiosity': ["What if I told you...", "Can you imagine...", "Ever wondered...", "You won't believe..."],
            'problem': ["Struggling with...", "Tired of...", "Fed up with...", "Still dealing with..."],
            'secret': ["Here's what nobody tells you...", "The hidden truth about...", "Industry insiders know...", "The secret behind..."],
            'urgency': ["This changes everything...", "You need to see this...", "Breaking news:", "This just happened..."],
            'controversy': ["Everyone's wrong about...", "The opposite is true...", "This will shock you...", "Prepare to be surprised..."]
        }

    def create_hook(self, content_type: str, topic: str) -> str:
        """Generate a compelling hook based on content type."""
        hook_type_map = {
            'announcement': 'urgency',
            'reaction': 'curiosity',
            'tutorial': 'problem',
            'trend_analysis': 'secret',
            'comparison': 'controversy',
            'storytelling': 'curiosity'
        }
        
        hook_type = hook_type_map.get(content_type, 'curiosity')
        hooks = self.hook_types.get(hook_type, self.hook_types['curiosity'])
        return f"{random.choice(hooks)} {topic}?"

class ScriptOptimizer:
    def optimize_for_platform(self, script: str, platform: str, content_data: Dict) -> str:
        """Optimize script for specific platform timing and style."""
        word_count = len(script.split())
        
        if platform.lower() == 'tiktok':
            # 15-60 seconds (~75-200 words)
            if word_count > 200:
                script = script[:1500] + "\n**[Optimized for TikTok - Fast & Engaging]**"
        elif platform.lower() == 'youtube':
            # 8-15 minutes (~1200-2000 words)
            if word_count < 1200:
                script += f"\n\n**Extended Content**: {content_data.get('content', '')[:1000]}..."
        elif platform.lower() == 'instagram':
            # 30-60 seconds (~150-300 words)
            if word_count > 300:
                script = script[:2000] + "\n**[Optimized for Instagram Reels]**"
        elif platform.lower() == 'linkedin':
            # Professional tone, 2-3 minutes (~400-600 words)
            if word_count > 600:
                script = script[:3500] + "\n**[Professional Insights for LinkedIn]**"
        
        return script

class ScriptingAgent:
    def __init__(self):
        self.classifier = ContentClassifier()
        self.selector = TemplateSelector()
        self.hook_generator = HookGenerator()
        self.optimizer = ScriptOptimizer()
    
    def generate_script(self, input_data: Dict) -> str:
        """Generate a viral script based on input article data."""
        # Step 1: Analyze content type
        content_type = self.classifier.analyze_input(
            input_data.get('topic', input_data.get('title', '')),
            input_data
        )

        # Step 2: Select and populate template
        template_data = self.selector.select_template(content_type, input_data)
        template = template_data['structure']
        populated_data = template_data['populated']

        # Step 3: Generate hook
        hook = self.hook_generator.create_hook(content_type, input_data.get('topic', input_data.get('title', '')))

        # Step 4: Populate template
        populated_data['hook'] = hook
        script = template.format(**populated_data)

        # Step 5: Optimize for platform
        platform = input_data.get('platform', 'youtube')
        final_script = self.optimizer.optimize_for_platform(script, platform, input_data)

        return final_script

@tool
async def generate_viral_script(article_data: Dict, platform: str = 'youtube') -> str:
    """Generate a viral social media script from article data.
    
    Args:
        article_data: Dictionary containing article data (url, title, content, key_points, etc.)
        platform: Target platform (youtube, tiktok, instagram, linkedin)
    
    Returns:
        Formatted script optimized for the specified platform
    """
    try:
        # Ensure article_data has required fields
        if not article_data.get('url') or not article_data.get('content'):
            return "❌ Error: Article data missing required fields (url, content)"

        # Add platform to article_data for optimization
        article_data['platform'] = platform

        # Initialize scripting agent
        scripting_agent = ScriptingAgent()

        # Generate script
        script = scripting_agent.generate_script(article_data)

        return f"""
🎬 **VIRAL SCRIPT GENERATED FOR {platform.upper()}**

{script}

**📊 Script Metadata:**
- Content Type: {scripting_agent.classifier.analyze_input(article_data.get('title', ''), article_data)}
- Word Count: {len(script.split())} words
- Estimated Duration: {len(script.split()) * 0.5:.1f} seconds
- Platform: {platform.upper()}
- Source: {article_data.get('url', 'N/A')}

✅ **Script Generation Complete** - Ready for visual timing analysis!
"""
    except Exception as e:
        return f"❌ Error generating script: {str(e)}"

# Create scripting agent tools list
scripting_tools = [generate_viral_script]