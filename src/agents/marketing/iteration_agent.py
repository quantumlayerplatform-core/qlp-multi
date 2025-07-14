"""
Iteration Agent - Analyzes performance and suggests improvements
"""

from typing import Dict, List, Any, Optional
import asyncio
from src.agents.azure_llm_client import llm_client, LLMProvider
from src.common.config import settings
from src.agents.marketing.models import (
    CampaignAnalytics, ContentType, Channel, ToneStyle
)
import structlog

logger = structlog.get_logger()


class IterationAgent:
    """Analyzes campaign performance and suggests iterations"""
    
    def __init__(self):
        self.llm_client = llm_client
        
        # Learning patterns from successful content
        self.success_patterns = {
            "high_engagement": {
                "indicators": ["personal story", "specific numbers", "question ending"],
                "threshold": 0.05  # 5% engagement rate
            },
            "high_conversion": {
                "indicators": ["clear CTA", "urgency", "social proof"],
                "threshold": 0.02  # 2% conversion rate
            },
            "viral_potential": {
                "indicators": ["controversial take", "industry insight", "visual element"],
                "threshold": 0.1   # 10% share rate
            }
        }
    
    async def suggest_improvements(
        self, analytics: CampaignAnalytics
    ) -> List[Dict[str, Any]]:
        """Suggest improvements based on analytics"""
        
        improvements = []
        
        # Analyze underperforming channels
        channel_improvements = await self._analyze_channels(
            analytics.channel_performance
        )
        improvements.extend(channel_improvements)
        
        # Content optimization suggestions
        content_improvements = await self._analyze_content_patterns(analytics)
        improvements.extend(content_improvements)
        
        # Timing optimizations
        timing_improvements = self._analyze_timing_patterns(analytics)
        improvements.extend(timing_improvements)
        
        # Audience targeting improvements
        audience_improvements = await self._analyze_audience_response(analytics)
        improvements.extend(audience_improvements)
        
        return improvements
    
    async def _analyze_channels(
        self, channel_performance: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze channel-specific improvements"""
        
        improvements = []
        
        for channel, metrics in channel_performance.items():
            engagement_rate = metrics.get("avg_engagement_rate", 0)
            
            # Check against benchmarks
            if channel == Channel.TWITTER.value and engagement_rate < 0.02:
                improvements.append({
                    "type": "channel_optimization",
                    "channel": channel,
                    "issue": "Below benchmark engagement",
                    "current": f"{engagement_rate:.2%}",
                    "target": "2%",
                    "suggestions": [
                        "Use more visual content (images, GIFs)",
                        "Post during peak hours (9 AM, 1 PM EST)",
                        "Engage with replies within first hour",
                        "Use 1-2 hashtags maximum",
                        "Keep tweets under 200 characters"
                    ]
                })
            
            elif channel == Channel.LINKEDIN.value and engagement_rate < 0.05:
                improvements.append({
                    "type": "channel_optimization",
                    "channel": channel,
                    "issue": "LinkedIn engagement below target",
                    "current": f"{engagement_rate:.2%}",
                    "target": "5%",
                    "suggestions": [
                        "Start posts with personal anecdotes",
                        "Use native LinkedIn video",
                        "Post on Tuesday-Thursday",
                        "Include industry statistics",
                        "End with open-ended questions"
                    ]
                })
            
            elif channel == Channel.EMAIL.value:
                open_rate = metrics.get("click_rate", 0) / 0.12  # Estimate
                if open_rate < 0.25:
                    improvements.append({
                        "type": "channel_optimization",
                        "channel": channel,
                        "issue": "Low email open rates",
                        "current": f"{open_rate:.1%}",
                        "target": "25%",
                        "suggestions": [
                            "A/B test subject lines",
                            "Personalize sender name",
                            "Send Tuesday 10 AM or Thursday 2 PM",
                            "Keep subject lines under 50 characters",
                            "Use preview text effectively"
                        ]
                    })
        
        return improvements
    
    async def _analyze_content_patterns(
        self, analytics: CampaignAnalytics
    ) -> List[Dict[str, Any]]:
        """Analyze content patterns for improvements"""
        
        prompt = f"""Analyze this campaign performance data and suggest content improvements:

Top Performing Content IDs: {analytics.best_performing_content[:3]}
Worst Performing Content IDs: {analytics.worst_performing_content[:3]}
Average Engagement Rate: {analytics.avg_engagement_rate:.2%}

Provide specific, actionable suggestions for:
1. Content themes that resonate
2. Optimal content length
3. Tone and style adjustments
4. Visual content recommendations
5. Headline optimization tactics"""

        try:
            response = await self.llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a content marketing strategist analyzing campaign data."
                    },
                    {"role": "user", "content": prompt}
                ],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                temperature=0.7
            )
            
            suggestions = self._parse_content_suggestions(
                response.get("content", "")
            )
            
            return [{
                "type": "content_optimization",
                "suggestions": suggestions,
                "priority": "high"
            }]
            
        except Exception as e:
            logger.error("Content analysis failed", error=str(e))
            return self._fallback_content_improvements()
    
    def _analyze_timing_patterns(
        self, analytics: CampaignAnalytics
    ) -> List[Dict[str, Any]]:
        """Analyze timing patterns for improvements"""
        
        improvements = []
        
        # Simplified timing analysis
        # In production, would analyze actual timestamp data
        improvements.append({
            "type": "timing_optimization",
            "suggestions": [
                "Test posting 30 minutes earlier for morning content",
                "Avoid posting during lunch hours (12-1 PM)",
                "Experiment with weekend posts for technical content",
                "Use scheduling tools to maintain consistency"
            ],
            "priority": "medium"
        })
        
        return improvements
    
    async def _analyze_audience_response(
        self, analytics: CampaignAnalytics
    ) -> List[Dict[str, Any]]:
        """Analyze audience response patterns"""
        
        improvements = []
        
        # Check if certain content types resonate better
        if analytics.avg_engagement_rate < 0.03:
            improvements.append({
                "type": "audience_optimization",
                "issue": "Overall low engagement",
                "suggestions": [
                    "Survey your audience for content preferences",
                    "Create more beginner-friendly content",
                    "Address specific pain points in your messaging",
                    "Use more relatable examples and case studies",
                    "Collaborate with industry influencers"
                ],
                "priority": "high"
            })
        
        return improvements
    
    async def generate_a_b_tests(
        self, content_id: str, content_type: ContentType
    ) -> List[Dict[str, Any]]:
        """Generate A/B test variations"""
        
        tests = []
        
        if content_type == ContentType.EMAIL_CAMPAIGN:
            tests.extend([
                {
                    "test_name": "Subject Line Emotion",
                    "variant_a": "Original subject line",
                    "variant_b": "Add urgency: 'Last chance: ' + original",
                    "hypothesis": "Urgency increases open rates by 15%"
                },
                {
                    "test_name": "CTA Button Color",
                    "variant_a": "Blue CTA button",
                    "variant_b": "Orange CTA button",
                    "hypothesis": "Orange increases clicks by 10%"
                }
            ])
        
        elif content_type == ContentType.LINKEDIN_POST:
            tests.extend([
                {
                    "test_name": "Opening Hook",
                    "variant_a": "Start with statistics",
                    "variant_b": "Start with personal story",
                    "hypothesis": "Personal stories increase engagement by 25%"
                },
                {
                    "test_name": "Post Length",
                    "variant_a": "Short post (< 150 words)",
                    "variant_b": "Long post (300-500 words)",
                    "hypothesis": "Longer posts get more comments"
                }
            ])
        
        elif content_type == ContentType.TWEET_THREAD:
            tests.extend([
                {
                    "test_name": "Thread Length",
                    "variant_a": "5-tweet thread",
                    "variant_b": "10-tweet thread",
                    "hypothesis": "Shorter threads get more full reads"
                },
                {
                    "test_name": "Media Usage",
                    "variant_a": "Text only",
                    "variant_b": "Include diagrams/GIFs",
                    "hypothesis": "Visual content increases shares by 40%"
                }
            ])
        
        return tests
    
    async def optimize_content(
        self, original_content: str, 
        performance_data: Dict[str, Any]
    ) -> str:
        """Optimize content based on performance data"""
        
        engagement_rate = performance_data.get("engagement_rate", 0)
        
        if engagement_rate >= 0.05:
            # High performer - minor tweaks only
            return await self._refine_high_performer(original_content)
        else:
            # Low performer - significant optimization
            return await self._transform_low_performer(
                original_content, performance_data
            )
    
    async def _refine_high_performer(self, content: str) -> str:
        """Refine already successful content"""
        
        prompt = f"""This content performed well. Make minor refinements to make it even better:

{content}

Improvements:
1. Strengthen the hook
2. Clarify the main benefit
3. Make CTA more compelling
4. Keep the same tone and structure"""

        try:
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                temperature=0.3  # Low temperature for minor changes
            )
            
            return response.get("content", "")
            
        except:
            return content  # Return original if optimization fails
    
    async def _transform_low_performer(
        self, content: str, performance_data: Dict[str, Any]
    ) -> str:
        """Transform underperforming content"""
        
        issues = []
        if performance_data.get("engagement_rate", 0) < 0.01:
            issues.append("Very low engagement")
        if performance_data.get("click_rate", 0) < 0.005:
            issues.append("Poor click-through rate")
        if performance_data.get("sentiment_score", 1) < 0.7:
            issues.append("Negative sentiment")
        
        prompt = f"""Transform this underperforming content:

Original:
{content}

Issues: {', '.join(issues)}

Create a completely new version that:
1. Has a stronger emotional hook
2. Clearly states the value proposition
3. Uses active voice and power words
4. Includes social proof or urgency
5. Has a clear, compelling CTA"""

        try:
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                temperature=0.8  # Higher temperature for creative transformation
            )
            
            return response.get("content", "")
            
        except:
            return self._fallback_optimization(content)
    
    def _parse_content_suggestions(self, response: str) -> List[str]:
        """Parse content suggestions from LLM response"""
        
        suggestions = []
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering or bullets
                suggestion = line.lstrip('0123456789.-) ').strip()
                if suggestion:
                    suggestions.append(suggestion)
        
        return suggestions[:10]  # Limit to top 10 suggestions
    
    def _fallback_content_improvements(self) -> List[Dict[str, Any]]:
        """Fallback content improvement suggestions"""
        
        return [{
            "type": "content_optimization",
            "suggestions": [
                "Use more specific numbers and data points",
                "Include customer success stories",
                "Create more visual content",
                "Write shorter, punchier headlines",
                "Add clear calls-to-action",
                "Use power words that trigger emotion",
                "Include social proof elements",
                "Address objections proactively"
            ],
            "priority": "high"
        }]
    
    def _fallback_optimization(self, content: str) -> str:
        """Fallback content optimization"""
        
        # Simple optimization rules
        optimized = content
        
        # Add urgency if missing
        if "today" not in content.lower() and "now" not in content.lower():
            optimized += "\n\n⏰ Limited time - Start today!"
        
        # Strengthen CTA if weak
        if not any(cta in content.lower() for cta in ["click", "start", "try", "get"]):
            optimized += "\n\n→ Try it free"
        
        return optimized