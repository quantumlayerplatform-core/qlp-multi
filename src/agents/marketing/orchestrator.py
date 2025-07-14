"""
Marketing Campaign Orchestrator

Central coordinator for AI-powered marketing campaign generation and execution.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import structlog

from src.common.models import AgentTier
from src.agents.marketing.models import (
    CampaignRequest, MarketingCampaign, MarketingContent,
    Channel, ContentType, ToneStyle, CampaignObjective
)
from src.agents.marketing.narrative_agent import NarrativeAgent
from src.agents.marketing.evangelism_agent import EvangelismAgent
from src.agents.marketing.tone_agent import ToneAgent
from src.agents.marketing.scheduler_agent import SchedulerAgent
from src.agents.marketing.engagement_monitor import EngagementMonitor
from src.agents.marketing.iteration_agent import IterationAgent

logger = structlog.get_logger()


class MarketingOrchestrator:
    """Orchestrates AI-powered marketing campaign generation"""
    
    def __init__(self):
        self.narrative_agent = NarrativeAgent()
        self.evangelism_agent = EvangelismAgent()
        self.tone_agent = ToneAgent()
        self.scheduler_agent = SchedulerAgent()
        self.engagement_monitor = EngagementMonitor()
        self.iteration_agent = IterationAgent()
        
    async def generate_campaign(self, request: CampaignRequest) -> MarketingCampaign:
        """Generate a complete marketing campaign"""
        logger.info("Starting campaign generation", 
                   objective=request.objective,
                   channels=request.channels)
        
        # Step 1: Generate campaign strategy
        strategy = await self._generate_strategy(request)
        
        # Step 2: Create content calendar
        calendar = await self._create_content_calendar(request)
        
        # Step 3: Generate content for each scheduled slot
        content_pieces = []
        for date, content_specs in calendar.items():
            for spec in content_specs:
                content = await self._generate_content_piece(
                    request, spec, strategy
                )
                content_pieces.append(content)
        
        # Step 4: Optimize tone and messaging
        optimized_content = await self._optimize_content(
            content_pieces, request.target_audience
        )
        
        # Step 5: Create final campaign
        campaign = MarketingCampaign(
            objective=request.objective,
            target_audience=request.target_audience,
            duration_days=request.duration_days,
            content_pieces=optimized_content,
            content_calendar=self._build_calendar_map(optimized_content),
            strategy_summary=strategy,
            kpis=self._define_kpis(request)
        )
        
        logger.info("Campaign generation complete",
                   campaign_id=campaign.campaign_id,
                   total_pieces=campaign.total_pieces)
        
        return campaign
    
    async def _generate_strategy(self, request: CampaignRequest) -> str:
        """Generate overall campaign strategy"""
        strategy_prompt = f"""
        Create a comprehensive marketing strategy for:
        
        Product: {request.product_description}
        Objective: {request.objective.value}
        Target Audience: {request.target_audience}
        Unique Value Prop: {request.unique_value_prop}
        Duration: {request.duration_days} days
        Channels: {', '.join(c.value for c in request.channels)}
        
        Key Features to Highlight:
        {chr(10).join(f'- {feature}' for feature in request.key_features)}
        
        Provide a strategic overview including:
        1. Core messaging pillars
        2. Content themes by week
        3. Channel-specific strategies
        4. Engagement tactics
        5. Success metrics
        """
        
        # In production, this would call the LLM
        # For now, return a structured strategy
        return await self.narrative_agent.generate_strategy(strategy_prompt)
    
    async def _create_content_calendar(
        self, request: CampaignRequest
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Create content calendar with optimal scheduling"""
        return await self.scheduler_agent.create_calendar(
            channels=request.channels,
            duration_days=request.duration_days,
            objective=request.objective,
            launch_date=request.launch_date or datetime.now()
        )
    
    async def _generate_content_piece(
        self, request: CampaignRequest, 
        spec: Dict[str, Any], 
        strategy: str
    ) -> MarketingContent:
        """Generate individual content piece"""
        # Determine which agent to use based on content type
        content_type = ContentType(spec["type"])
        channel = Channel(spec["channel"])
        
        if content_type in [ContentType.BLOG_POST, ContentType.TWEET_THREAD]:
            content = await self.evangelism_agent.generate_content(
                content_type=content_type,
                channel=channel,
                product_info=request.product_description,
                features=request.key_features,
                target_audience=request.target_audience,
                strategy=strategy
            )
        else:
            content = await self.narrative_agent.generate_content(
                content_type=content_type,
                channel=channel,
                product_info=request.product_description,
                value_prop=request.unique_value_prop,
                target_audience=request.target_audience,
                tone_preferences=request.tone_preferences
            )
        
        return MarketingContent(
            type=content_type,
            channel=channel,
            content=content["content"],
            title=content.get("title"),
            tone=ToneStyle(spec.get("tone", ToneStyle.CONVERSATIONAL)),
            target_audience=request.target_audience,
            keywords=content.get("keywords", []),
            hashtags=content.get("hashtags", []),
            cta=content.get("cta"),
            scheduled_time=spec.get("scheduled_time")
        )
    
    async def _optimize_content(
        self, content_pieces: List[MarketingContent], 
        target_audience: str
    ) -> List[MarketingContent]:
        """Optimize content tone and messaging"""
        optimized = []
        for content in content_pieces:
            # Adjust tone for specific audience
            adjusted_content = await self.tone_agent.adjust_tone(
                content=content.content,
                current_tone=content.tone,
                target_audience=target_audience,
                channel=content.channel
            )
            
            content.content = adjusted_content
            optimized.append(content)
        
        return optimized
    
    def _build_calendar_map(
        self, content_pieces: List[MarketingContent]
    ) -> Dict[str, List[str]]:
        """Build calendar mapping of date to content IDs"""
        calendar = {}
        for content in content_pieces:
            if content.scheduled_time:
                date_key = content.scheduled_time.strftime("%Y-%m-%d")
                if date_key not in calendar:
                    calendar[date_key] = []
                calendar[date_key].append(content.content_id)
        return calendar
    
    def _define_kpis(self, request: CampaignRequest) -> Dict[str, Any]:
        """Define KPIs based on campaign objective"""
        kpi_map = {
            CampaignObjective.LAUNCH_AWARENESS: {
                "target_impressions": 100000,
                "target_engagement_rate": 0.05,
                "target_shares": 500
            },
            CampaignObjective.LEAD_GENERATION: {
                "target_leads": 1000,
                "target_conversion_rate": 0.02,
                "target_email_signups": 500
            },
            CampaignObjective.TECHNICAL_EVANGELISM: {
                "target_github_stars": 100,
                "target_blog_views": 10000,
                "target_demo_requests": 50
            },
            CampaignObjective.FOUNDER_AUTHORITY: {
                "target_followers_growth": 1000,
                "target_engagement_rate": 0.08,
                "target_speaking_invites": 5
            }
        }
        
        return kpi_map.get(request.objective, {
            "target_impressions": 50000,
            "target_engagement_rate": 0.03
        })
    
    async def monitor_and_iterate(
        self, campaign_id: str
    ) -> Dict[str, Any]:
        """Monitor campaign performance and suggest iterations"""
        # Get performance data
        analytics = await self.engagement_monitor.get_campaign_analytics(campaign_id)
        
        # Generate improvement suggestions
        improvements = await self.iteration_agent.suggest_improvements(analytics)
        
        return {
            "analytics": analytics,
            "improvements": improvements
        }
    
    async def export_campaign(
        self, campaign: MarketingCampaign, 
        format: str = "json"
    ) -> str:
        """Export campaign in various formats"""
        if format == "json":
            return campaign.json(indent=2)
        elif format == "markdown":
            return self._export_as_markdown(campaign)
        elif format == "csv":
            return self._export_as_csv(campaign)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_as_markdown(self, campaign: MarketingCampaign) -> str:
        """Export campaign as markdown documentation"""
        md = f"""# Marketing Campaign: {campaign.objective.value}

## Overview
- **Target Audience**: {campaign.target_audience}
- **Duration**: {campaign.duration_days} days
- **Total Content Pieces**: {campaign.total_pieces}
- **Channels**: {', '.join(c.value for c in campaign.channels_used)}

## Strategy
{campaign.strategy_summary}

## Content Calendar

"""
        for date, content_ids in sorted(campaign.content_calendar.items()):
            md += f"\n### {date}\n"
            for content_id in content_ids:
                content = next(c for c in campaign.content_pieces if c.content_id == content_id)
                md += f"- **{content.channel.value}**: {content.title or content.type.value}\n"
        
        md += "\n## Content Details\n"
        for content in campaign.content_pieces:
            md += f"\n### {content.title or content.content_id}\n"
            md += f"- **Type**: {content.type.value}\n"
            md += f"- **Channel**: {content.channel.value}\n"
            md += f"- **Tone**: {content.tone.value}\n"
            if content.keywords:
                md += f"- **Keywords**: {', '.join(content.keywords)}\n"
            if content.hashtags:
                md += f"- **Hashtags**: {', '.join(content.hashtags)}\n"
            md += f"\n{content.content}\n"
            if content.cta:
                md += f"\n**CTA**: {content.cta}\n"
        
        return md
    
    def _export_as_csv(self, campaign: MarketingCampaign) -> str:
        """Export campaign as CSV for scheduling tools"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Date", "Time", "Channel", "Type", "Title", 
            "Content", "Hashtags", "CTA", "Media URLs"
        ])
        
        # Content rows
        for content in campaign.content_pieces:
            scheduled = content.scheduled_time or datetime.now()
            writer.writerow([
                scheduled.strftime("%Y-%m-%d"),
                scheduled.strftime("%H:%M"),
                content.channel.value,
                content.type.value,
                content.title or "",
                content.content,
                " ".join(content.hashtags),
                content.cta or "",
                " ".join(content.media_urls)
            ])
        
        return output.getvalue()