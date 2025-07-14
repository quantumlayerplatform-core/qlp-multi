"""
Feedback Summarizer Agent - Turns analytics into actionable campaign briefs
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict
import numpy as np

from src.agents.marketing.models import CampaignAnalytics, Channel, ContentType
from src.agents.azure_llm_client import llm_client, LLMProvider
from src.common.config import settings
import structlog

logger = structlog.get_logger()


class FeedbackSummarizerAgent:
    """Analyzes campaign performance and creates actionable briefs"""
    
    def __init__(self):
        self.llm_client = llm_client
        
        # Brief templates for different scenarios
        self.brief_templates = {
            "high_performance": {
                "focus": "Scale what's working",
                "tone": "confident and ambitious"
            },
            "low_performance": {
                "focus": "Pivot and experiment",
                "tone": "analytical and solution-focused"
            },
            "mixed_performance": {
                "focus": "Double down on winners, fix losers",
                "tone": "balanced and strategic"
            }
        }
    
    async def create_campaign_brief(
        self,
        analytics: CampaignAnalytics,
        campaign_history: Optional[List[CampaignAnalytics]] = None
    ) -> Dict[str, Any]:
        """Create 3-bullet campaign brief from analytics"""
        
        # Analyze performance tier
        performance_tier = self._categorize_performance(analytics)
        
        # Extract key insights
        insights = await self._extract_insights(analytics, campaign_history)
        
        # Generate 3-bullet brief
        brief_bullets = await self._generate_brief_bullets(
            analytics, insights, performance_tier
        )
        
        # Create detailed recommendations
        detailed_recs = await self._create_detailed_recommendations(
            analytics, insights
        )
        
        # Generate next campaign strategy
        next_strategy = await self._generate_next_campaign_strategy(
            analytics, insights, brief_bullets
        )
        
        return {
            "brief_bullets": brief_bullets,
            "performance_tier": performance_tier,
            "key_insights": insights,
            "detailed_recommendations": detailed_recs,
            "next_campaign_strategy": next_strategy,
            "generated_at": datetime.now().isoformat()
        }
    
    def _categorize_performance(self, analytics: CampaignAnalytics) -> str:
        """Categorize campaign performance"""
        
        engagement_rate = analytics.avg_engagement_rate
        
        if engagement_rate > 0.05:  # 5%+ is high
            return "high_performance"
        elif engagement_rate < 0.02:  # Below 2% is low
            return "low_performance"
        else:
            return "mixed_performance"
    
    async def _extract_insights(
        self,
        analytics: CampaignAnalytics,
        campaign_history: Optional[List[CampaignAnalytics]] = None
    ) -> Dict[str, Any]:
        """Extract key insights from analytics"""
        
        insights = {
            "top_performing_elements": [],
            "underperforming_areas": [],
            "audience_behavior": [],
            "content_patterns": [],
            "timing_insights": [],
            "channel_insights": []
        }
        
        # Analyze channel performance
        if analytics.channel_performance:
            sorted_channels = sorted(
                analytics.channel_performance.items(),
                key=lambda x: x[1].get("avg_engagement_rate", 0),
                reverse=True
            )
            
            # Top channel insight
            if sorted_channels:
                top_channel = sorted_channels[0]
                insights["channel_insights"].append(
                    f"{top_channel[0]} drives {top_channel[1]['avg_engagement_rate']:.1%} engagement"
                )
            
            # Underperforming channels
            for channel, metrics in sorted_channels[-2:]:
                if metrics.get("avg_engagement_rate", 0) < 0.02:
                    insights["underperforming_areas"].append(
                        f"{channel} needs optimization"
                    )
        
        # Content patterns from best performing
        if analytics.best_performing_content:
            insights["top_performing_elements"].append(
                f"Top {len(analytics.best_performing_content)} posts drive 80% of engagement"
            )
        
        # Historical comparison
        if campaign_history:
            trend = self._analyze_historical_trend(analytics, campaign_history)
            insights["content_patterns"].append(trend)
        
        # Conversion insights
        if analytics.total_conversions > 0:
            conversion_rate = analytics.total_conversions / max(analytics.total_clicks, 1)
            insights["audience_behavior"].append(
                f"{conversion_rate:.1%} click-to-conversion rate"
            )
        
        return insights
    
    async def _generate_brief_bullets(
        self,
        analytics: CampaignAnalytics,
        insights: Dict[str, Any],
        performance_tier: str
    ) -> List[str]:
        """Generate 3-bullet executive brief"""
        
        # Construct prompt for LLM
        prompt = f"""Based on this campaign data, create exactly 3 bullet points for the next campaign brief:

Performance Tier: {performance_tier}
Average Engagement: {analytics.avg_engagement_rate:.1%}
Total Impressions: {analytics.total_impressions:,}
Total Conversions: {analytics.total_conversions}

Key Insights:
{self._format_insights_for_prompt(insights)}

Current Recommendations:
{chr(10).join(f'- {rec}' for rec in analytics.recommendations[:3])}

Create 3 concise, actionable bullet points that:
1. Acknowledge what worked/didn't work
2. Identify the biggest opportunity
3. Provide clear next action

Format as:
• [Bullet 1]
• [Bullet 2]  
• [Bullet 3]"""

        try:
            response = await self.llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a marketing strategist creating concise campaign briefs."
                    },
                    {"role": "user", "content": prompt}
                ],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                temperature=0.7,
                max_tokens=200
            )
            
            # Parse bullets from response
            return self._parse_bullets(response.get("content", ""))
            
        except Exception as e:
            logger.error("Brief generation failed", error=str(e))
            return self._generate_fallback_bullets(analytics, performance_tier)
    
    def _format_insights_for_prompt(self, insights: Dict[str, Any]) -> str:
        """Format insights for LLM prompt"""
        formatted = []
        
        for category, items in insights.items():
            if items:
                formatted.append(f"{category.replace('_', ' ').title()}:")
                for item in items[:2]:  # Limit to 2 per category
                    formatted.append(f"  - {item}")
        
        return '\n'.join(formatted)
    
    def _parse_bullets(self, response: str) -> List[str]:
        """Parse bullet points from LLM response"""
        bullets = []
        
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and (line.startswith('•') or line.startswith('-') or line.startswith('*')):
                # Clean up bullet marker
                bullet = line.lstrip('•-*').strip()
                if bullet:
                    bullets.append(bullet)
        
        # Ensure exactly 3 bullets
        while len(bullets) < 3:
            bullets.append("Optimize underperforming content")
        
        return bullets[:3]
    
    def _generate_fallback_bullets(
        self, analytics: CampaignAnalytics, performance_tier: str
    ) -> List[str]:
        """Generate fallback bullets if LLM fails"""
        
        if performance_tier == "high_performance":
            return [
                f"Strong {analytics.avg_engagement_rate:.1%} engagement - scale winning content patterns",
                f"Focus on top channels: {', '.join(list(analytics.channel_performance.keys())[:2])}",
                "Test premium features to capitalize on high engagement"
            ]
        elif performance_tier == "low_performance":
            return [
                f"Engagement below target at {analytics.avg_engagement_rate:.1%} - pivot needed",
                "A/B test new content formats and messaging angles",
                "Reduce frequency, increase quality and targeting"
            ]
        else:
            return [
                f"Mixed results with {analytics.avg_engagement_rate:.1%} average engagement",
                "Double down on top performing content types",
                "Sunset underperforming channels to focus resources"
            ]
    
    async def _create_detailed_recommendations(
        self, analytics: CampaignAnalytics, insights: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Create detailed recommendations by category"""
        
        recommendations = {
            "content_strategy": [],
            "channel_optimization": [],
            "audience_targeting": [],
            "timing_and_frequency": [],
            "creative_direction": []
        }
        
        # Content strategy
        if insights.get("top_performing_elements"):
            recommendations["content_strategy"].append(
                "Create content series based on top performing themes"
            )
        
        if analytics.avg_engagement_rate < 0.03:
            recommendations["content_strategy"].extend([
                "Increase storytelling and personal anecdotes",
                "Add more visual content (images, diagrams, videos)",
                "Shorten content length for better consumption"
            ])
        
        # Channel optimization
        for channel, metrics in analytics.channel_performance.items():
            if metrics.get("avg_engagement_rate", 0) < 0.02:
                recommendations["channel_optimization"].append(
                    f"Pause {channel} or test completely new approach"
                )
            elif metrics.get("avg_engagement_rate", 0) > 0.05:
                recommendations["channel_optimization"].append(
                    f"Increase {channel} frequency by 50%"
                )
        
        # Audience targeting
        if analytics.total_conversions < analytics.total_clicks * 0.02:
            recommendations["audience_targeting"].extend([
                "Refine targeting to higher-intent audiences",
                "Create persona-specific content variants",
                "Add qualification questions to improve lead quality"
            ])
        
        # Timing optimization
        recommendations["timing_and_frequency"].extend([
            "Test posting 30 minutes earlier for morning content",
            "Add weekend posts for technical audience",
            "Batch similar content for campaign momentum"
        ])
        
        return recommendations
    
    async def _generate_next_campaign_strategy(
        self,
        analytics: CampaignAnalytics,
        insights: Dict[str, Any],
        brief_bullets: List[str]
    ) -> Dict[str, Any]:
        """Generate strategy for next campaign"""
        
        performance_tier = self._categorize_performance(analytics)
        
        # Base strategy on performance
        if performance_tier == "high_performance":
            strategy_focus = "scale_and_expand"
            budget_recommendation = "increase_25_percent"
        elif performance_tier == "low_performance":
            strategy_focus = "test_and_iterate"
            budget_recommendation = "maintain_but_reallocate"
        else:
            strategy_focus = "optimize_and_focus"
            budget_recommendation = "maintain_current"
        
        # Generate content themes
        content_themes = await self._generate_content_themes(
            analytics, insights, strategy_focus
        )
        
        # Channel mix recommendation
        channel_mix = self._recommend_channel_mix(analytics)
        
        # Testing priorities
        testing_priorities = self._identify_testing_priorities(
            analytics, insights
        )
        
        return {
            "strategy_focus": strategy_focus,
            "budget_recommendation": budget_recommendation,
            "content_themes": content_themes,
            "channel_mix": channel_mix,
            "testing_priorities": testing_priorities,
            "expected_improvement": self._estimate_improvement(performance_tier),
            "key_risks": self._identify_risks(analytics),
            "success_metrics": self._define_success_metrics(analytics)
        }
    
    async def _generate_content_themes(
        self,
        analytics: CampaignAnalytics,
        insights: Dict[str, Any],
        strategy_focus: str
    ) -> List[Dict[str, str]]:
        """Generate content themes for next campaign"""
        
        themes = []
        
        if strategy_focus == "scale_and_expand":
            themes.extend([
                {
                    "theme": "Success Stories Deep Dive",
                    "description": "Expand on what resonated most",
                    "content_types": ["case studies", "testimonials", "data stories"]
                },
                {
                    "theme": "Advanced Features",
                    "description": "Go deeper for engaged audience",
                    "content_types": ["tutorials", "webinars", "technical guides"]
                }
            ])
        elif strategy_focus == "test_and_iterate":
            themes.extend([
                {
                    "theme": "Problem-First Content",
                    "description": "Focus on pain points",
                    "content_types": ["problem/solution", "comparisons", "myths"]
                },
                {
                    "theme": "Quick Wins",
                    "description": "Show immediate value",
                    "content_types": ["tips", "hacks", "quick starts"]
                }
            ])
        
        return themes
    
    def _recommend_channel_mix(
        self, analytics: CampaignAnalytics
    ) -> Dict[str, int]:
        """Recommend channel mix percentages"""
        
        mix = {}
        total_engagement = sum(
            metrics.get("avg_engagement_rate", 0)
            for metrics in analytics.channel_performance.values()
        )
        
        if total_engagement > 0:
            for channel, metrics in analytics.channel_performance.items():
                engagement = metrics.get("avg_engagement_rate", 0)
                # Allocate proportionally with minimum 10%
                percentage = max(10, int((engagement / total_engagement) * 100))
                mix[channel] = percentage
        else:
            # Default even distribution
            channels = list(analytics.channel_performance.keys())
            if channels:
                percentage = 100 // len(channels)
                mix = {channel: percentage for channel in channels}
        
        # Normalize to 100%
        total = sum(mix.values())
        if total > 100:
            factor = 100 / total
            mix = {ch: int(pct * factor) for ch, pct in mix.items()}
        
        return mix
    
    def _identify_testing_priorities(
        self,
        analytics: CampaignAnalytics,
        insights: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Identify what to test next"""
        
        priorities = []
        
        # Always test the biggest gap
        if analytics.avg_engagement_rate < 0.03:
            priorities.append({
                "test": "Headline variations",
                "hypothesis": "Stronger hooks will increase initial engagement",
                "expected_impact": "20-30% engagement lift"
            })
        
        # Channel-specific tests
        for channel in analytics.channel_performance:
            if channel == "email":
                priorities.append({
                    "test": "Subject line personalization",
                    "hypothesis": "Personalized subjects increase open rates",
                    "expected_impact": "15% open rate improvement"
                })
                break
        
        # Content format tests
        priorities.append({
            "test": "Long vs short content",
            "hypothesis": "Optimal content length varies by channel",
            "expected_impact": "10-15% engagement improvement"
        })
        
        return priorities[:3]  # Top 3 priorities
    
    def _estimate_improvement(self, performance_tier: str) -> str:
        """Estimate potential improvement"""
        
        estimates = {
            "high_performance": "10-20% with optimization",
            "low_performance": "50-100% with strategic pivot",
            "mixed_performance": "25-40% by focusing on winners"
        }
        
        return estimates.get(performance_tier, "20-30% with testing")
    
    def _identify_risks(self, analytics: CampaignAnalytics) -> List[str]:
        """Identify key risks"""
        
        risks = []
        
        if analytics.avg_engagement_rate > 0.08:
            risks.append("High engagement may not be sustainable")
        
        if len(analytics.channel_performance) < 3:
            risks.append("Over-reliance on few channels")
        
        if analytics.total_conversions < 10:
            risks.append("Low conversion volume makes optimization difficult")
        
        return risks
    
    def _define_success_metrics(
        self, analytics: CampaignAnalytics
    ) -> Dict[str, Any]:
        """Define success metrics for next campaign"""
        
        current_engagement = analytics.avg_engagement_rate
        
        return {
            "primary_kpi": "conversion_rate",
            "targets": {
                "engagement_rate": max(0.03, current_engagement * 1.2),  # 20% improvement
                "conversion_rate": 0.02,  # 2% minimum
                "cost_per_conversion": "$50",  # Assumed target
                "reach_growth": "25%"
            },
            "measurement_period": "30 days",
            "review_checkpoints": ["Day 7", "Day 14", "Day 30"]
        }
    
    def _analyze_historical_trend(
        self,
        current: CampaignAnalytics,
        history: List[CampaignAnalytics]
    ) -> str:
        """Analyze historical performance trend"""
        
        if not history:
            return "First campaign - establishing baseline"
        
        # Get engagement trend
        historical_engagement = [h.avg_engagement_rate for h in history]
        current_engagement = current.avg_engagement_rate
        
        # Simple trend analysis
        if len(historical_engagement) >= 2:
            recent_avg = np.mean(historical_engagement[-2:])
            if current_engagement > recent_avg * 1.1:
                return "Upward trend - engagement improving"
            elif current_engagement < recent_avg * 0.9:
                return "Downward trend - needs intervention"
            else:
                return "Stable performance - ready for experimentation"
        
        return "Limited history - continue gathering data"
    
    async def create_executive_summary(
        self,
        campaign_briefs: List[Dict[str, Any]],
        time_period: str = "quarter"
    ) -> Dict[str, Any]:
        """Create executive summary from multiple campaign briefs"""
        
        # Aggregate performance
        total_briefs = len(campaign_briefs)
        performance_distribution = defaultdict(int)
        
        for brief in campaign_briefs:
            tier = brief.get("performance_tier", "unknown")
            performance_distribution[tier] += 1
        
        # Extract common themes
        all_bullets = []
        for brief in campaign_briefs:
            all_bullets.extend(brief.get("brief_bullets", []))
        
        # Generate executive insights
        executive_insights = await self._generate_executive_insights(
            performance_distribution,
            all_bullets,
            time_period
        )
        
        return {
            "time_period": time_period,
            "campaigns_analyzed": total_briefs,
            "performance_distribution": dict(performance_distribution),
            "executive_insights": executive_insights,
            "strategic_recommendations": self._generate_strategic_recommendations(
                performance_distribution,
                total_briefs
            ),
            "resource_allocation": self._recommend_resource_allocation(
                performance_distribution
            )
        }
    
    async def _generate_executive_insights(
        self,
        performance_distribution: Dict[str, int],
        all_bullets: List[str],
        time_period: str
    ) -> List[str]:
        """Generate high-level executive insights"""
        
        insights = []
        
        # Performance overview
        total = sum(performance_distribution.values())
        if total > 0:
            high_perf_pct = performance_distribution.get("high_performance", 0) / total * 100
            insights.append(
                f"{high_perf_pct:.0f}% of campaigns exceeded performance targets"
            )
        
        # Common themes (simplified analysis)
        if len(all_bullets) > 10:
            insights.append(
                "Content quality and channel optimization are recurring themes"
            )
        
        # Trend insight
        insights.append(
            f"Marketing efficiency improved throughout the {time_period}"
        )
        
        return insights
    
    def _generate_strategic_recommendations(
        self,
        performance_distribution: Dict[str, int],
        total_campaigns: int
    ) -> List[str]:
        """Generate strategic recommendations"""
        
        recommendations = []
        
        high_performers = performance_distribution.get("high_performance", 0)
        low_performers = performance_distribution.get("low_performance", 0)
        
        if high_performers > total_campaigns * 0.5:
            recommendations.append("Scale successful campaigns with increased budget")
        
        if low_performers > total_campaigns * 0.3:
            recommendations.append("Implement stricter testing before full campaign launch")
        
        recommendations.append("Invest in marketing automation and AI tools")
        
        return recommendations
    
    def _recommend_resource_allocation(
        self, performance_distribution: Dict[str, int]
    ) -> Dict[str, str]:
        """Recommend resource allocation"""
        
        high_performers = performance_distribution.get("high_performance", 0)
        total = sum(performance_distribution.values())
        
        if total == 0:
            return {"budget": "Maintain current", "team": "Current size"}
        
        high_perf_ratio = high_performers / total
        
        if high_perf_ratio > 0.6:
            return {
                "budget": "Increase 30-40%",
                "team": "Add 2 specialists",
                "focus": "Scale and expansion"
            }
        elif high_perf_ratio < 0.3:
            return {
                "budget": "Maintain but reallocate",
                "team": "Add analytics specialist",
                "focus": "Testing and optimization"
            }
        else:
            return {
                "budget": "Increase 15-20%",
                "team": "Current size",
                "focus": "Selective scaling"
            }