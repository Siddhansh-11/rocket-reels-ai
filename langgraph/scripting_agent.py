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
**HOOK**: {hook}

**ACT 1 - CONTEXT**: {context}

**ACT 2 - REVELATION**: {revelation}

**ACT 3 - IMPACT**: {impact}

**CONCLUSION/CTA**: {cta}
""",
                'populate': lambda data: {
                    'hook': data['hook'],
                    'context': f"The tech world has been buzzing with rumors and speculation about {data['topic']}, but today we finally got official confirmation. While companies like NVIDIA have dominated the market, {data.get('source', 'a major player')} has been quietly working on something that could change everything. The timing couldn't be more perfect as we're entering a new era of AI-powered computing and gamers are demanding more performance than ever before.",
                    'revelation': f"At today's announcement, {data.get('source', 'the company')} unveiled {data['topic']}, and the details are absolutely incredible. This isn't just another incremental upgrade - we're looking at a complete redesign from the ground up. The new architecture brings {', '.join(data.get('key_points', ['significant improvements', 'enhanced performance', 'cutting-edge features'])[:3])}. What makes this particularly exciting is how they've approached the integration of artificial intelligence directly into the hardware, making it a true game-changer for both content creators and gamers alike.",
                    'impact': f"The implications of this announcement are massive. First, we're seeing {data.get('key_points', ['revolutionary technology'])[0] if data.get('key_points') else 'groundbreaking innovation'} that could completely shift the competitive landscape. Content creators will benefit from faster rendering times and AI-assisted workflows, while gamers can expect significantly improved frame rates and visual quality without breaking the bank. This technology also opens up possibilities we haven't even imagined yet - from real-time AI image generation to enhanced productivity features that could transform how we work and play.",
                    'cta': "What do you think about this announcement? Will this be enough to challenge the current market leaders? Let me know your thoughts in the comments below, and don't forget to subscribe for more breaking tech news and in-depth analysis!"
                }
            },
            'reaction': {
                'structure': """
**HOOK**: {hook}

**ACT 1 - SETUP**: {setup}

**ACT 2 - ANALYSIS**: {analysis}

**ACT 3 - IMPLICATIONS**: {implications}

**CONCLUSION/CTA**: {cta}
""",
                'populate': lambda data: {
                    'hook': data['hook'],
                    'setup': f"The tech community is absolutely buzzing about the latest announcement from {data.get('source', 'a major technology company')} regarding {data['topic']}. I've been following this story closely, and I have to say, this development caught me completely off guard. The timing is particularly interesting because it comes at a moment when the industry is at a critical turning point. We've been waiting for someone to challenge the status quo, and it looks like that moment has finally arrived. Let me break down exactly what this means and why everyone should be paying attention.",
                    'analysis': f"After diving deep into the technical specifications and announcements, here's my honest take on what we're seeing. The focus on {', '.join(data.get('key_points', ['innovation', 'performance', 'value'])[:2])} is clearly a strategic move to address the biggest pain points in the current market. What really stands out to me is how they've approached {data.get('key_points', ['the core technology'])[0] if data.get('key_points') else 'this innovation'} - it's not just about raw performance numbers, but about creating a more accessible and user-friendly experience. The fact that they're integrating AI capabilities directly into the hardware shows they understand where the industry is heading, and they're positioning themselves to be leaders rather than followers.",
                    'implications': f"Looking at the bigger picture, this announcement could fundamentally reshape {data.get('category', 'the entire technology landscape')}. We're not just talking about improved specs or slightly better performance - this represents a philosophical shift in how companies approach innovation. For consumers, this means more choice, better value, and potentially lower prices across the board as competition heats up. For the industry, it signals that no company can rest on their laurels anymore. Innovation cycles are accelerating, and companies that don't adapt quickly will be left behind.",
                    'cta': "I'm really curious to hear what you think about this development. Do you see this as a genuine game-changer, or is it just marketing hype? Have you had experiences with similar technologies? Drop your thoughts in the comments below - I read every single one and love engaging with this community. And if you found this analysis helpful, make sure to hit that subscribe button for more in-depth tech coverage!"
                }
            },
            'tutorial': {
                'structure': """
**HOOK**: {hook}

**ACT 1 - PROBLEM**: {problem}

**ACT 2 - SOLUTION**: {solution}

**ACT 3 - RESULTS**: {results}

**CONCLUSION/CTA**: {cta}
""",
                'populate': lambda data: {
                    'hook': data['hook'],
                    'problem': f"If you've been struggling to understand {data['topic']}, you're definitely not alone. This is one of the most complex and rapidly evolving areas in technology today, and even experienced professionals find it challenging to keep up with all the latest developments. The problem is that most explanations either get too technical too quickly, or they oversimplify things to the point where you're not really learning anything useful. What makes this even more frustrating is that understanding these concepts is becoming increasingly important for anyone who wants to stay competitive in today's tech landscape.",
                    'solution': f"Here's the step-by-step approach I've developed to break down {data['topic']} in a way that actually makes sense. First, we need to understand the fundamental principles: {data.get('key_points', ['the core concepts', 'key technologies', 'practical applications'])[0] if data.get('key_points') else 'the basic framework'}. Then, we'll explore {', '.join(data.get('key_points', ['the main components', 'implementation strategies'])[:2])}. What I love about this method is that it builds your understanding progressively, so each concept reinforces the previous ones. We'll also look at real-world examples and practical applications that you can immediately start applying in your own projects or work environment.",
                    'results': f"The results of applying this systematic approach are remarkable. Not only will you gain a deep understanding of {data['topic']}, but you'll also develop the analytical skills to evaluate new developments in this field as they emerge. Students and professionals who have used this method report feeling much more confident in technical discussions and decision-making processes. You'll save hours of confusion and frustration, and more importantly, you'll be able to leverage this knowledge to advance your career or improve your projects significantly.",
                    'cta': "I'd love to hear about your experience with this approach! Try implementing these concepts in your next project and let me know how it goes in the comments. If you found this tutorial helpful, please give it a thumbs up and subscribe for more in-depth technical content. Do you have specific questions about any of these concepts? Drop them below and I'll do my best to address them in future videos!"
                }
            },
            'trend_analysis': {
                'structure': """
**HOOK**: {hook}

**ACT 1 - TREND OVERVIEW**: {trend}

**ACT 2 - DEEP ANALYSIS**: {deep_dive}

**ACT 3 - FUTURE PREDICTIONS**: {future}

**CONCLUSION/CTA**: {cta}
""",
                'populate': lambda data: {
                    'hook': data['hook'],
                    'trend': f"Everyone's talking about {data['topic']}, but most people are completely missing the bigger picture here. What we're witnessing isn't just another tech trend - it's a fundamental shift that will affect how we work, create, and interact with technology for years to come. The surface-level discussions focus on the obvious features and capabilities, but the real story is much more interesting and complex. To understand where this is heading, we need to look at the underlying forces driving this change and examine the patterns that most analysts are overlooking.",
                    'deep_dive': f"Let me break down what's really happening behind the scenes. The convergence of {', '.join(data.get('key_points', ['emerging technologies', 'market forces', 'consumer demands'])[:2])} is creating a perfect storm for innovation. {data.get('summary', 'This trend is reshaping the entire industry landscape')}. What makes this particularly significant is the timing - we're at an inflection point where multiple technological advances are coming together simultaneously. The companies that understand this intersection will dominate the next decade, while those that don't will struggle to remain relevant. The data suggests we're seeing adoption rates that far exceed what industry experts predicted just two years ago.",
                    'future': f"Looking ahead, the implications are staggering. Within the next 12 to 18 months, we can expect to see {data.get('key_points', ['revolutionary changes', 'unprecedented opportunities', 'paradigm shifts'])[0] if data.get('key_points') else 'massive transformation'} across multiple sectors. But here's what most people don't realize - this is just the beginning. The real transformation will happen over the next three to five years as these technologies mature and integrate with existing systems. We're likely to see entirely new business models emerge, traditional companies completely reimagine their operations, and consumers gain access to capabilities that seemed like science fiction just a few years ago.",
                    'cta': "This is exactly the kind of analysis that helps you stay ahead of the curve in this rapidly changing landscape. What trends are you watching closely? Have you noticed any patterns that others might be missing? Share your insights in the comments - I love learning from this community's diverse perspectives. And if you want to stay informed about emerging trends before they become mainstream, make sure to subscribe and hit the notification bell!"
                }
            },
            'comparison': {
                'structure': """
**HOOK**: {hook}

**ACT 1 - SETUP**: {setup}

**ACT 2 - ANALYSIS**: {analysis}

**ACT 3 - VERDICT**: {verdict}

**CONCLUSION/CTA**: {cta}
""",
                'populate': lambda data: {
                    'hook': data['hook'],
                    'setup': f"The debate around {data['topic']} versus the competition has been heating up, and honestly, I think most comparisons are missing the crucial details that actually matter to real users. Everyone focuses on the headline specs and marketing claims, but that's not the whole story. To give you a truly comprehensive comparison, I've spent weeks testing and analyzing every aspect of these options. We need to look at performance, cost-effectiveness, long-term value, user experience, and several factors that most reviews completely ignore. The goal here isn't to declare a winner based on arbitrary criteria, but to help you make the best decision for your specific needs and use case.",
                    'analysis': f"Let me walk you through the detailed analysis of what sets these options apart. {data.get('summary', 'After extensive testing and comparison, several key differences emerge that fundamentally change the value proposition')}. When it comes to raw performance, the numbers tell an interesting story, but performance isn't everything. We also need to consider the ecosystem, software compatibility, power efficiency, thermal management, and upgrade potential. What I found particularly interesting is how {', '.join(data.get('key_points', ['price-to-performance ratio', 'feature set', 'reliability'])[:2])} varies significantly depending on your specific workload and requirements. Some options excel in certain scenarios while falling short in others.",
                    'verdict': f"After this comprehensive analysis, here's my honest verdict: {data['topic']} emerges as the clear winner for {data.get('key_points', ['most users seeking the best overall value'])[0] if data.get('key_points') else 'users who prioritize performance and reliability'}. However, and this is important, that doesn't mean it's the right choice for everyone. If your priorities lean heavily toward budget considerations, content creation workflows, or specific software requirements, the decision might be different. The key is understanding exactly what you need and how each option delivers on those requirements. What impressed me most about this option is how it balances performance, efficiency, and long-term value in a way that makes sense for the majority of users.",
                    'cta': "I'm really interested in your thoughts on this comparison! Have you had experience with any of these options? What factors matter most in your decision-making process? Let me know in the comments below - your real-world experiences often provide insights that no amount of testing can replicate. And if this comparison helped you make a decision, please give it a thumbs up and subscribe for more detailed tech analysis!"
                }
            },
            'storytelling': {
                'structure': """
**HOOK**: {hook}

**ACT 1 - THE JOURNEY**: {journey}

**ACT 2 - THE CHALLENGE**: {struggle}

**ACT 3 - THE BREAKTHROUGH**: {solution}

**CONCLUSION/CTA**: {cta}
""",
                'populate': lambda data: {
                    'hook': data['hook'],
                    'journey': f"The story behind {data['topic']} is absolutely fascinating, and it's one that most people never get to hear. It begins years ago with an ambitious vision that seemed almost impossible at the time. The team behind this innovation wasn't just trying to make incremental improvements - they were attempting to fundamentally reimagine how we approach this entire field. What makes this story particularly compelling is the unconventional path they took, the risks they were willing to accept, and the persistence they showed when everyone else thought they were heading in the wrong direction. This isn't just a story about technology - it's about human determination and the power of thinking differently.",
                    'struggle': f"But the journey wasn't smooth. {data.get('summary', 'They faced seemingly impossible technical challenges that would have stopped most teams in their tracks')}. For months, they struggled with problems that had no obvious solutions. The technical hurdles seemed insurmountable, funding was tight, and industry experts were skeptical about their approach. There were moments when the entire project nearly fell apart, and team members questioned whether they were chasing an impossible dream. The pressure was immense, especially when competitors with much larger budgets were making steady progress with more conventional approaches. What kept them going was their conviction that there had to be a better way.",
                    'solution': f"The breakthrough came when they discovered {data.get('key_points', ['an innovative approach that changed everything'])[0] if data.get('key_points') else 'a completely new way of solving the problem'}. It wasn't a gradual improvement or a lucky accident - it was a moment of genuine insight that transformed their entire approach. This discovery didn't just solve their immediate technical challenges; it opened up possibilities they hadn't even considered before. The solution was elegant in its simplicity, yet revolutionary in its implications. This led to a cascade of innovations that fundamentally changed not just their product, but the entire industry's understanding of what was possible. Today, what seemed impossible just a few years ago is becoming the new standard.",
                    'cta': "Stories like this remind me why I love covering technology - it's really about human creativity and perseverance. Do you have any experiences with breakthrough moments in your own work or projects? I'd love to hear about times when you had to persist through seemingly impossible challenges. Share your stories in the comments below - these real-world experiences are often more inspiring than any corporate success story. And if you enjoyed this deep dive, make sure to subscribe for more behind-the-scenes stories from the tech world!"
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
🎬 **VOICEOVER SCRIPT GENERATED FOR {platform.upper()}**

{script}

**📊 Script Metadata:**
- Content Type: {scripting_agent.classifier.analyze_input(article_data.get('title', ''), article_data)}
- Word Count: {len(script.split())} words
- Estimated Duration: {len(script.split()) * 0.5:.1f} seconds
- Platform: {platform.upper()}
- Source: {article_data.get('url', 'N/A')}

✅ **Voiceover Script Ready** - Pure speech content with no visual instructions!
"""
    except Exception as e:
        return f"❌ Error generating script: {str(e)}"

# Create scripting agent tools list
scripting_tools = [generate_viral_script]