"""
Tone Agent - Adjusts content tone for different audiences and channels
"""

from typing import Dict, List, Optional
import asyncio
from src.agents.azure_llm_client import llm_client, LLMProvider
from src.common.config import settings
from src.agents.marketing.models import ToneStyle, Channel
import structlog

logger = structlog.get_logger()


class ToneAgent:
    """Adjusts content tone for specific audiences and channels"""
    
    def __init__(self):
        self.llm_client = llm_client
        
        # Tone profiles for different combinations
        self.tone_profiles = {
            (ToneStyle.TECHNICAL, Channel.TWITTER): {
                "style": "Concise, factual, with technical depth",
                "elements": ["metrics", "architecture mentions", "technical terms"],
                "avoid": ["fluff", "corporate speak", "long explanations"]
            },
            (ToneStyle.VISIONARY, Channel.LINKEDIN): {
                "style": "Inspirational, forward-thinking, professional",
                "elements": ["industry trends", "future vision", "thought leadership"],
                "avoid": ["technical jargon", "casual language", "controversy"]
            },
            (ToneStyle.CONVERSATIONAL, Channel.REDDIT): {
                "style": "Authentic, humble, community-focused",
                "elements": ["personal experience", "questions", "vulnerability"],
                "avoid": ["sales pitch", "corporate tone", "self-promotion"]
            },
            (ToneStyle.EDUCATIONAL, Channel.MEDIUM): {
                "style": "Clear, structured, informative",
                "elements": ["step-by-step", "examples", "takeaways"],
                "avoid": ["assumptions", "complexity without explanation", "bias"]
            }
        }
    
    async def adjust_tone(
        self,
        content: str,
        current_tone: ToneStyle,
        target_audience: str,
        channel: Channel
    ) -> str:
        """Adjust content tone for specific audience and channel"""
        
        # Get optimal tone for channel
        optimal_tone = self._get_optimal_tone(channel, target_audience)
        
        if current_tone == optimal_tone:
            return content
        
        # Get tone profile
        profile = self.tone_profiles.get(
            (optimal_tone, channel),
            self._get_default_profile(optimal_tone)
        )
        
        prompt = f"""Adjust this content's tone:

Current Tone: {current_tone.value}
Target Tone: {optimal_tone.value}
Channel: {channel.value}
Audience: {target_audience}

Tone Profile:
- Style: {profile['style']}
- Include: {', '.join(profile['elements'])}
- Avoid: {', '.join(profile['avoid'])}

Original Content:
{content}

Rewrite the content to match the target tone while preserving the core message and information."""

        try:
            response = await self.llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at adapting content tone for different audiences."
                    },
                    {"role": "user", "content": prompt}
                ],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                temperature=0.7
            )
            
            return response.get("content", "")
            
        except Exception as e:
            logger.error("Tone adjustment failed", error=str(e))
            return content  # Return original if adjustment fails
    
    def _get_optimal_tone(self, channel: Channel, audience: str) -> ToneStyle:
        """Determine optimal tone for channel and audience"""
        
        # Channel-specific defaults
        channel_tones = {
            Channel.TWITTER: ToneStyle.CONVERSATIONAL,
            Channel.LINKEDIN: ToneStyle.AUTHORITATIVE,
            Channel.MEDIUM: ToneStyle.EDUCATIONAL,
            Channel.REDDIT: ToneStyle.CONVERSATIONAL,
            Channel.HACKERNEWS: ToneStyle.TECHNICAL,
            Channel.EMAIL: ToneStyle.CONVERSATIONAL,
            Channel.DEVTO: ToneStyle.TECHNICAL,
            Channel.PRODUCTHUNT: ToneStyle.VISIONARY
        }
        
        # Audience overrides
        if "CTO" in audience or "technical" in audience.lower():
            return ToneStyle.TECHNICAL
        elif "founder" in audience.lower() or "CEO" in audience:
            return ToneStyle.VISIONARY
        elif "developer" in audience.lower():
            return ToneStyle.EDUCATIONAL
        
        return channel_tones.get(channel, ToneStyle.CONVERSATIONAL)
    
    def _get_default_profile(self, tone: ToneStyle) -> Dict[str, any]:
        """Get default profile for a tone"""
        defaults = {
            ToneStyle.TECHNICAL: {
                "style": "Precise, detailed, evidence-based",
                "elements": ["data", "specifications", "technical accuracy"],
                "avoid": ["ambiguity", "generalizations", "hype"]
            },
            ToneStyle.VISIONARY: {
                "style": "Bold, future-focused, inspiring",
                "elements": ["big picture", "transformation", "possibility"],
                "avoid": ["limitations", "technical details", "pessimism"]
            },
            ToneStyle.EDUCATIONAL: {
                "style": "Clear, patient, structured",
                "elements": ["examples", "analogies", "summaries"],
                "avoid": ["jargon", "assumptions", "condescension"]
            },
            ToneStyle.CONVERSATIONAL: {
                "style": "Friendly, relatable, engaging",
                "elements": ["questions", "personal touches", "humor"],
                "avoid": ["formality", "distance", "preaching"]
            },
            ToneStyle.AUTHORITATIVE: {
                "style": "Confident, knowledgeable, trustworthy",
                "elements": ["expertise", "insights", "leadership"],
                "avoid": ["uncertainty", "weakness", "informality"]
            }
        }
        
        return defaults.get(tone, defaults[ToneStyle.CONVERSATIONAL])
    
    async def analyze_tone(self, content: str) -> Dict[str, any]:
        """Analyze the current tone of content"""
        prompt = f"""Analyze the tone of this content:

{content}

Provide:
1. Primary tone style
2. Formality level (1-10)
3. Technical depth (1-10)
4. Emotional appeal (1-10)
5. Target audience (best guess)
6. Suggested improvements"""

        try:
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                temperature=0.3
            )
            
            return self._parse_tone_analysis(response.get("content", ""))
            
        except Exception as e:
            logger.error("Tone analysis failed", error=str(e))
            return {
                "primary_tone": "unknown",
                "formality": 5,
                "technical_depth": 5,
                "emotional_appeal": 5
            }
    
    def _parse_tone_analysis(self, analysis: str) -> Dict[str, any]:
        """Parse tone analysis results"""
        # Simple parsing - in production would be more sophisticated
        return {
            "primary_tone": ToneStyle.CONVERSATIONAL,
            "formality": 5,
            "technical_depth": 7,
            "emotional_appeal": 6,
            "target_audience": "developers",
            "improvements": ["Add more specific examples", "Reduce jargon"]
        }
    
    async def create_tone_variants(
        self, content: str, channel: Channel
    ) -> Dict[ToneStyle, str]:
        """Create multiple tone variants of the same content"""
        variants = {}
        
        # Generate variants for different tones
        tone_styles = [
            ToneStyle.TECHNICAL,
            ToneStyle.Visionary,
            ToneStyle.CONVERSATIONAL
        ]
        
        for tone in tone_styles:
            variant = await self.adjust_tone(
                content=content,
                current_tone=ToneStyle.CONVERSATIONAL,
                target_audience="general",
                channel=channel
            )
            variants[tone] = variant
        
        return variants