# visual_agent.py
import re
from typing import Dict, List, Any, Tuple
from langchain_core.tools import tool
import json
from datetime import timedelta

class VisualTimingAnalyzer:
    """Analyzes script content and generates precise visual timing cues."""
    
    def __init__(self):
        self.words_per_second = 2.5  # Average speaking pace
        self.platform_styles = {
            'youtube': {'transition_frequency': 8, 'b_roll_percentage': 60},
            'tiktok': {'transition_frequency': 3, 'b_roll_percentage': 80},
            'instagram': {'transition_frequency': 5, 'b_roll_percentage': 70},
            'linkedin': {'transition_frequency': 10, 'b_roll_percentage': 40}
        }
    
    def parse_script_sections(self, script: str) -> List[Dict]:
        """Parse script into timed sections with content analysis."""
        sections = []
        current_time = 0
        
        # Split script by sections (marked with **)
        script_parts = re.split(r'\*\*([^*]+)\*\*:', script)
        
        for i in range(1, len(script_parts), 2):
            if i + 1 < len(script_parts):
                section_type = script_parts[i].strip()
                content = script_parts[i + 1].strip()
                
                word_count = len(content.split())
                duration = word_count / self.words_per_second
                
                sections.append({
                    'type': section_type,
                    'content': content,
                    'start_time': current_time,
                    'end_time': current_time + duration,
                    'duration': duration,
                    'word_count': word_count
                })
                
                current_time += duration
        
        return sections
    
    def generate_timing_cues(self, sections: List[Dict], platform: str) -> List[Dict]:
        """Generate detailed visual timing cues for each section."""
        style = self.platform_styles.get(platform, self.platform_styles['youtube'])
        visual_cues = []
        
        for section in sections:
            section_cues = self._analyze_section_visuals(section, style, platform)
            visual_cues.extend(section_cues)
        
        return visual_cues
    
    def _analyze_section_visuals(self, section: Dict, style: Dict, platform: str) -> List[Dict]:
        """Analyze individual section for visual requirements."""
        cues = []
        section_type = section['type'].lower()
        content = section['content']
        start_time = section['start_time']
        duration = section['duration']
        
        # Base visual for section opening
        opening_visual = self._get_section_opening_visual(section_type, content, platform)
        cues.append({
            'timestamp': f"{self._format_time(start_time)}",
            'duration': min(3.0, duration * 0.3),
            'visual_type': 'section_opener',
            'description': opening_visual,
            'priority': 'high'
        })
        
        # Content-specific visuals throughout section
        content_visuals = self._generate_content_visuals(content, start_time, duration, style, platform)
        cues.extend(content_visuals)
        
        # Transition visual if section is long enough
        if duration > 8:
            mid_point = start_time + (duration * 0.6)
            transition_visual = self._get_transition_visual(section_type, platform)
            cues.append({
                'timestamp': f"{self._format_time(mid_point)}",
                'duration': 2.0,
                'visual_type': 'transition',
                'description': transition_visual,
                'priority': 'medium'
            })
        
        return cues
    
    def _get_section_opening_visual(self, section_type: str, content: str, platform: str) -> str:
        """Generate opening visual based on section type."""
        visual_map = {
            'hook': f"Close-up of speaker with dynamic background - High energy opener for {platform}",
            'opening': "Engaging speaker introduction with branded graphics",
            'context': "B-roll footage related to the topic with overlay text",
            'revelation': "Dramatic reveal visual - screen recording or product shot",
            'impact': "Split-screen comparison or before/after visual",
            'analysis': "Data visualization, charts, or analytical graphics",
            'setup': "Scene-setting B-roll with contextual information",
            'implications': "Future-focused graphics or prediction visuals",
            'problem': "Problem illustration - frustrated user or current state",
            'solution': "Solution demonstration - clear step-by-step visual",
            'tutorial': "Screen recording or hands-on demonstration",
            'step-by-step': "Numbered steps with clear visual progression",
            'results': "Before/after comparison or success metrics",
            'trend overview': "Trending graphics with statistics or market data",
            'deep analysis': "Detailed breakdown with supporting visuals",
            'future predictions': "Futuristic graphics or timeline visualization",
            'the journey': "Timeline or story progression visual",
            'the challenge': "Obstacle illustration or problem visualization",
            'the breakthrough': "Eureka moment - dramatic reveal or celebration",
            'call to action': "Speaker direct to camera with engagement graphics"
        }
        
        return visual_map.get(section_type, f"Relevant B-roll for {section_type} section")
    
    def _generate_content_visuals(self, content: str, start_time: float, duration: float, style: Dict, platform: str) -> List[Dict]:
        """Generate visuals based on content analysis."""
        cues = []
        
        # Identify key phrases that need visual support
        visual_triggers = {
            r'(\d+%|\d+\s*percent)': 'percentage_graphic',
            r'(compared to|versus|vs)': 'comparison_visual',
            r'(step \d+|first|second|third|next)': 'step_indicator',
            r'(increase|decrease|growth|decline)': 'trend_graphic',
            r'(before|after|now|then)': 'timeline_visual',
            r'(AI|artificial intelligence|machine learning)': 'tech_visualization',
            r'(startup|company|business)': 'corporate_visual',
            r'(future|prediction|forecast)': 'future_graphic'
        }
        
        words = content.split()
        current_pos = 0
        
        for pattern, visual_type in visual_triggers.items():
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            for match in matches:
                # Calculate approximate timing of this phrase
                words_before = len(content[:match.start()].split())
                phrase_time = start_time + (words_before / self.words_per_second)
                
                if phrase_time < start_time + duration:  # Within section bounds
                    cues.append({
                        'timestamp': f"{self._format_time(phrase_time)}",
                        'duration': 3.0,
                        'visual_type': visual_type,
                        'description': self._get_visual_description(visual_type, match.group(), platform),
                        'priority': 'medium',
                        'trigger_phrase': match.group()
                    })
        
        # Add regular B-roll intervals
        b_roll_interval = style['transition_frequency']
        for i in range(int(duration // b_roll_interval)):
            b_roll_time = start_time + (i + 1) * b_roll_interval
            if b_roll_time < start_time + duration:
                cues.append({
                    'timestamp': f"{self._format_time(b_roll_time)}",
                    'duration': 4.0,
                    'visual_type': 'b_roll',
                    'description': f"Relevant B-roll footage - {platform} optimized",
                    'priority': 'low'
                })
        
        return cues
    
    def _get_visual_description(self, visual_type: str, trigger_phrase: str, platform: str) -> str:
        """Generate specific visual description based on type and trigger."""
        descriptions = {
            'percentage_graphic': f"Animated percentage counter showing {trigger_phrase} - {platform} style",
            'comparison_visual': f"Split-screen comparison highlighting {trigger_phrase}",
            'step_indicator': f"Step indicator graphic for {trigger_phrase}",
            'trend_graphic': f"Trending chart or graph showing {trigger_phrase}",
            'timeline_visual': f"Timeline graphic emphasizing {trigger_phrase}",
            'tech_visualization': f"High-tech graphics and animations for {trigger_phrase}",
            'corporate_visual': f"Professional corporate imagery for {trigger_phrase}",
            'future_graphic': f"Futuristic design elements for {trigger_phrase}"
        }
        
        return descriptions.get(visual_type, f"Supporting visual for {trigger_phrase}")
    
    def _get_transition_visual(self, section_type: str, platform: str) -> str:
        """Generate transition visual between sections."""
        transitions = {
            'youtube': "Smooth zoom transition with branded overlay",
            'tiktok': "Quick cut with trending transition effect",
            'instagram': "Aesthetic transition with Instagram-style graphics",
            'linkedin': "Professional fade transition with clean graphics"
        }
        
        return transitions.get(platform, "Standard transition effect")
    
    def _format_time(self, seconds: float) -> str:
        """Format time in MM:SS format."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

class VisualSuggestionEngine:
    """Generates specific visual suggestions based on content and platform."""
    
    def __init__(self):
        self.platform_specs = {
            'youtube': {
                'aspect_ratio': '16:9',
                'thumbnail_style': 'high_contrast_clickbait',
                'graphics_style': 'professional_branded',
                'transition_style': 'smooth_cinematic'
            },
            'tiktok': {
                'aspect_ratio': '9:16',
                'thumbnail_style': 'vertical_mobile_optimized',
                'graphics_style': 'trendy_colorful',
                'transition_style': 'quick_snappy'
            },
            'instagram': {
                'aspect_ratio': '9:16',
                'thumbnail_style': 'aesthetic_feed_optimized',
                'graphics_style': 'clean_minimal',
                'transition_style': 'smooth_aesthetic'
            },
            'linkedin': {
                'aspect_ratio': '16:9',
                'thumbnail_style': 'professional_corporate',
                'graphics_style': 'business_clean',
                'transition_style': 'professional_fade'
            }
        }
    
    def generate_visual_suggestions(self, article_data: Dict, platform: str, script_content: str) -> Dict:
        """Generate comprehensive visual suggestions."""
        specs = self.platform_specs.get(platform, self.platform_specs['youtube'])
        
        return {
            'thumbnail_suggestions': self._generate_thumbnail_ideas(article_data, platform, specs),
            'b_roll_suggestions': self._generate_b_roll_ideas(article_data, script_content, platform),
            'graphics_pack': self._generate_graphics_suggestions(article_data, platform, specs),
            'text_overlays': self._generate_text_overlay_suggestions(script_content, platform),
            'color_scheme': self._suggest_color_scheme(article_data, platform),
            'music_suggestions': self._suggest_music_style(article_data, platform)
        }
    
    def _generate_thumbnail_ideas(self, article_data: Dict, platform: str, specs: Dict) -> List[Dict]:
        """Generate thumbnail design ideas."""
        title = article_data.get('title', '')
        domain = article_data.get('domain', '')
        
        return [
            {
                'concept': 'Question Mark Intrigue',
                'description': f"Large question mark with key topic from title, {specs['aspect_ratio']} format",
                'text_overlay': self._extract_key_phrase(title),
                'visual_elements': ['question mark', 'contrasting colors', 'clean typography'],
                'style': specs['thumbnail_style']
            },
            {
                'concept': 'Before/After Split',
                'description': f"Split screen showing transformation or comparison, {platform} optimized",
                'text_overlay': 'Before vs After',
                'visual_elements': ['split screen', 'arrows', 'contrast'],
                'style': specs['thumbnail_style']
            },
            {
                'concept': 'Shocked Expression',
                'description': f"Person with surprised expression + key statistic, {specs['aspect_ratio']}",
                'text_overlay': self._extract_number_or_stat(title),
                'visual_elements': ['facial expression', 'bold text', 'bright colors'],
                'style': specs['thumbnail_style']
            }
        ]
    
    def _generate_b_roll_ideas(self, article_data: Dict, script_content: str, platform: str) -> List[str]:
        """Generate B-roll footage suggestions."""
        suggestions = []
        
        # Extract key topics from content
        topics = self._extract_key_topics(article_data, script_content)
        
        for topic in topics:
            suggestions.extend([
                f"Stock footage of {topic} in action",
                f"Close-up shots of {topic} interface/product",
                f"People using {topic} technology",
                f"Behind-the-scenes {topic} development",
                f"Industry experts discussing {topic}"
            ])
        
        # Platform-specific additions
        if platform == 'tiktok':
            suggestions.extend([
                "Quick transition shots",
                "Trending visual effects",
                "Popular TikTok-style cuts"
            ])
        elif platform == 'youtube':
            suggestions.extend([
                "Detailed product demonstrations",
                "Interview-style footage",
                "Professional setup shots"
            ])
        
        return suggestions[:10]  # Limit to top 10
    
    def _generate_graphics_suggestions(self, article_data: Dict, platform: str, specs: Dict) -> Dict:
        """Generate graphics package suggestions."""
        return {
            'lower_thirds': [
                f"Speaker name + title - {specs['graphics_style']} style",
                f"Source citation - {article_data.get('domain', 'source')}",
                "Key statistics callout"
            ],
            'transitions': [
                f"{specs['transition_style']} between sections",
                "Logo reveal transition",
                "Topic change indicator"
            ],
            'callout_graphics': [
                "Important quote highlight",
                "Key statistic emphasis",
                "Website/social media handles"
            ],
            'background_elements': [
                f"Subtle brand elements - {platform} optimized",
                "Topic-relevant background patterns",
                "Platform-specific design elements"
            ]
        }
    
    def _generate_text_overlay_suggestions(self, script_content: str, platform: str) -> List[Dict]:
        """Generate text overlay timing and content."""
        overlays = []
        
        # Extract key phrases for text overlays
        key_phrases = re.findall(r'\*\*([^*]+)\*\*', script_content)
        
        for i, phrase in enumerate(key_phrases[:5]):  # Limit to 5 key overlays
            overlays.append({
                'text': phrase,
                'style': f'{platform}_optimized_text',
                'timing': f'Overlay {i+1}',
                'position': 'center' if platform == 'tiktok' else 'lower_third',
                'animation': 'fade_in' if platform == 'linkedin' else 'pop_in'
            })
        
        return overlays
    
    def _suggest_color_scheme(self, article_data: Dict, platform: str) -> Dict:
        """Suggest color scheme based on content and platform."""
        color_schemes = {
            'tech': {'primary': '#0066CC', 'secondary': '#00FF88', 'accent': '#FF6B00'},
            'ai': {'primary': '#8A2BE2', 'secondary': '#00CED1', 'accent': '#FFD700'},
            'startup': {'primary': '#FF4500', 'secondary': '#32CD32', 'accent': '#1E90FF'},
            'business': {'primary': '#2F4F4F', 'secondary': '#4682B4', 'accent': '#DAA520'}
        }
        
        # Determine category from article data
        content = (article_data.get('title', '') + article_data.get('content', '')).lower()
        
        for category, colors in color_schemes.items():
            if category in content:
                return {
                    'scheme': category,
                    'colors': colors,
                    'platform_adaptation': f'Optimized for {platform} viewing'
                }
        
        return {
            'scheme': 'default_tech',
            'colors': color_schemes['tech'],
            'platform_adaptation': f'Optimized for {platform} viewing'
        }
    
    def _suggest_music_style(self, article_data: Dict, platform: str) -> Dict:
        """Suggest music style and energy level."""
        content = (article_data.get('title', '') + article_data.get('content', '')).lower()
        
        music_styles = {
            'high_energy': ['breakthrough', 'launch', 'revolutionary', 'amazing'],
            'corporate': ['business', 'enterprise', 'professional', 'industry'],
            'tech': ['ai', 'algorithm', 'code', 'software', 'app'],
            'inspirational': ['success', 'growth', 'achievement', 'innovation']
        }
        
        for style, keywords in music_styles.items():
            if any(keyword in content for keyword in keywords):
                return {
                    'style': style,
                    'tempo': 'fast' if platform in ['tiktok', 'instagram'] else 'moderate',
                    'volume': 'background_level',
                    'platform_note': f'Optimized for {platform} audio standards'
                }
        
        return {
            'style': 'neutral_tech',
            'tempo': 'moderate',
            'volume': 'background_level',
            'platform_note': f'Safe choice for {platform}'
        }
    
    def _extract_key_phrase(self, text: str) -> str:
        """Extract key phrase for thumbnail."""
        words = text.split()
        if len(words) <= 3:
            return text
        return ' '.join(words[:3]) + '...'
    
    def _extract_number_or_stat(self, text: str) -> str:
        """Extract number or statistic from text."""
        numbers = re.findall(r'\d+(?:\.\d+)?%?', text)
        return numbers[0] if numbers else 'NEW!'
    
    def _extract_key_topics(self, article_data: Dict, script_content: str) -> List[str]:
        """Extract key topics from article and script."""
        content = article_data.get('content', '') + script_content
        
        # Simple keyword extraction (in real implementation, use NLP)
        tech_keywords = ['AI', 'artificial intelligence', 'startup', 'app', 'software', 'technology', 'innovation', 'algorithm']
        found_topics = []
        
        for keyword in tech_keywords:
            if keyword.lower() in content.lower():
                found_topics.append(keyword)
        
        return found_topics[:5]  # Return top 5

@tool
async def generate_visual_timing(script_content: str, article_data: Dict, platform: str = 'youtube') -> str:
    """Generate detailed visual timing and suggestions based on script content.
    
    Args:
        script_content: The generated script content
        article_data: Original article data for context
        platform: Target platform (youtube, tiktok, instagram, linkedin)
    
    Returns:
        Comprehensive visual timing guide with specific suggestions
    """
    try:
        if not script_content or not isinstance(script_content, str):
            return "❌ Error: Valid script content required for visual timing"
        
        # Initialize visual components
        timing_analyzer = VisualTimingAnalyzer()
        suggestion_engine = VisualSuggestionEngine()
        
        # Parse script into timed sections
        script_sections = timing_analyzer.parse_script_sections(script_content)
        
        if not script_sections:
            return "❌ Error: Could not parse script sections for timing analysis"
        
        # Generate timing cues
        visual_cues = timing_analyzer.generate_timing_cues(script_sections, platform)
        
        # Generate visual suggestions
        visual_suggestions = suggestion_engine.generate_visual_suggestions(article_data, platform, script_content)
        
        # Calculate total duration
        total_duration = max([section['end_time'] for section in script_sections]) if script_sections else 0
        
        # Format response
        response = f"""
🎨 **VISUAL TIMING & SUGGESTIONS FOR {platform.upper()}**

**⏱️ TIMING BREAKDOWN:**
Total Duration: {timing_analyzer._format_time(total_duration)} ({total_duration:.1f} seconds)
Platform: {platform.upper()}
Visual Cues: {len(visual_cues)} total

**🎬 DETAILED TIMING CUES:**
"""
        
        # Add timing cues grouped by priority
        high_priority_cues = [cue for cue in visual_cues if cue.get('priority') == 'high']
        medium_priority_cues = [cue for cue in visual_cues if cue.get('priority') == 'medium']
        low_priority_cues = [cue for cue in visual_cues if cue.get('priority') == 'low']
        
        if high_priority_cues:
            response += "\n**🔴 HIGH PRIORITY VISUALS:**\n"
            for cue in high_priority_cues:
                response += f"• {cue['timestamp']} - {cue['description']} ({cue['duration']}s)\n"
        
        if medium_priority_cues:
            response += "\n**🟡 MEDIUM PRIORITY VISUALS:**\n"
            for cue in medium_priority_cues[:5]:  # Limit to 5 for readability
                response += f"• {cue['timestamp']} - {cue['description']} ({cue['duration']}s)\n"
        
        if low_priority_cues:
            response += f"\n**🟢 B-ROLL & FILLER VISUALS:** {len(low_priority_cues)} additional cues\n"
        
        # Add visual suggestions
        response += f"""

**🖼️ THUMBNAIL CONCEPTS:**
{chr(10).join([f"• {thumb['concept']}: {thumb['description']}" for thumb in visual_suggestions['thumbnail_suggestions']])}

**🎥 B-ROLL FOOTAGE NEEDED:**
{chr(10).join([f"• {b_roll}" for b_roll in visual_suggestions['b_roll_suggestions'][:5]])}

**📊 GRAPHICS PACKAGE:**
Lower Thirds: {len(visual_suggestions['graphics_pack']['lower_thirds'])} styles
Transitions: {len(visual_suggestions['graphics_pack']['transitions'])} types
Callouts: {len(visual_suggestions['graphics_pack']['callout_graphics'])} elements

**🎨 DESIGN SPECIFICATIONS:**
Color Scheme: {visual_suggestions['color_scheme']['scheme'].title()} 
Primary: {visual_suggestions['color_scheme']['colors']['primary']}
Music Style: {visual_suggestions['music_suggestions']['style'].replace('_', ' ').title()}
Tempo: {visual_suggestions['music_suggestions']['tempo'].title()}

**📝 TEXT OVERLAYS:**
{chr(10).join([f"• {overlay['text']} ({overlay['timing']})" for overlay in visual_suggestions['text_overlays']])}

✅ **Visual Guide Complete** - Ready for video production!
"""
        
        return response
        
    except Exception as e:
        return f"❌ Error generating visual timing: {str(e)}"

@tool
async def generate_production_timeline(script_content: str, article_data: Dict, platform: str = 'youtube') -> str:
    """Generate a complete production timeline with visual cues, timing, and resource requirements.
    
    Args:
        script_content: The generated script content
        article_data: Original article data for context
        platform: Target platform (youtube, tiktok, instagram, linkedin)
    
    Returns:
        Complete production timeline with resources and timing
    """
    try:
        # Get visual timing first
        visual_timing = await generate_visual_timing(script_content, article_data, platform)
        
        if "❌" in visual_timing:
            return visual_timing  # Return error if visual timing failed
        
        # Initialize analyzer for additional production details
        timing_analyzer = VisualTimingAnalyzer()
        script_sections = timing_analyzer.parse_script_sections(script_content)
        
        total_duration = max([section['end_time'] for section in script_sections]) if script_sections else 0
        
        # Calculate production requirements
        production_time = {
            'pre_production': f"{total_duration * 0.5:.1f} hours",
            'filming': f"{total_duration * 0.1:.1f} hours", 
            'editing': f"{total_duration * 2:.1f} hours",
            'review_approval': f"{total_duration * 0.3:.1f} hours"
        }
        
        return f"""
📋 **COMPLETE PRODUCTION TIMELINE FOR {platform.upper()}**

{visual_timing}

**⏰ PRODUCTION SCHEDULE:**
Pre-Production: {production_time['pre_production']} (research, script review, visual prep)
Filming/Recording: {production_time['filming']} (actual content capture)
Post-Production: {production_time['editing']} (editing, graphics, audio)
Review & Approval: {production_time['review_approval']} (final review, adjustments)

**📦 RESOURCE CHECKLIST:**
✅ Script approved and timing verified
□ B-roll footage collected/sourced  
□ Graphics package created
□ Music/audio selected
□ Thumbnail designs prepared
□ Platform-specific formatting completed

**🎯 PLATFORM OPTIMIZATION:**
Aspect Ratio: {timing_analyzer.platform_styles.get(platform, {}).get('aspect_ratio', '16:9')}
Target Duration: {timing_analyzer._format_time(total_duration)}
Engagement Elements: {len([cue for cue in visual_timing.split('•') if 'transition' in cue.lower()])} transitions

🚀 **Ready for Production Pipeline!**
"""
        
    except Exception as e:
        return f"❌ Error generating production timeline: {str(e)}"

# Create visual agent tools list
visual_tools = [generate_visual_timing, generate_production_timeline]