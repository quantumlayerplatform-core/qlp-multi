"""
Engagement Monitor - Tracks and analyzes content performance
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
import random
from collections import defaultdict

from src.agents.marketing.models import (
    Channel, ContentPerformance, CampaignAnalytics
)
from src.common.database import get_db
import structlog

logger = structlog.get_logger()


class EngagementMonitor:
    """Monitors and analyzes content engagement metrics"""
    
    def __init__(self):
        self.performance_cache = {}
        
        # Benchmark engagement rates by channel
        self.benchmarks = {
            Channel.TWITTER: {
                "engagement_rate": 0.02,  # 2%
                "click_rate": 0.015,      # 1.5%
                "share_rate": 0.005       # 0.5%
            },
            Channel.LINKEDIN: {
                "engagement_rate": 0.05,  # 5%
                "click_rate": 0.03,       # 3%
                "share_rate": 0.01        # 1%
            },
            Channel.EMAIL: {
                "open_rate": 0.25,        # 25%
                "click_rate": 0.03,       # 3%
                "conversion_rate": 0.02   # 2%
            },
            Channel.REDDIT: {
                "upvote_rate": 0.7,       # 70% positive
                "comment_rate": 0.1,      # 10%
                "award_rate": 0.001       # 0.1%
            }
        }
    
    async def track_performance(
        self, content_id: str, channel: Channel, metrics: Dict[str, Any]
    ) -> ContentPerformance:
        """Track performance metrics for a piece of content"""
        
        performance = ContentPerformance(
            content_id=content_id,
            channel=channel,
            impressions=metrics.get("impressions", 0),
            clicks=metrics.get("clicks", 0),
            engagement_rate=self._calculate_engagement_rate(metrics),
            conversions=metrics.get("conversions", 0),
            shares=metrics.get("shares", 0),
            comments=metrics.get("comments", 0),
            sentiment_score=metrics.get("sentiment_score", 0.0)
        )
        
        # Cache performance
        self.performance_cache[content_id] = performance
        
        # Store in database (in production)
        await self._store_performance(performance)
        
        return performance
    
    async def get_campaign_analytics(
        self, campaign_id: str
    ) -> CampaignAnalytics:
        """Get comprehensive analytics for a campaign"""
        
        # In production, this would query real data
        # For now, generate realistic sample data
        performances = await self._get_campaign_performances(campaign_id)
        
        if not performances:
            return CampaignAnalytics(campaign_id=campaign_id)
        
        # Calculate totals
        total_impressions = sum(p.impressions for p in performances)
        total_clicks = sum(p.clicks for p in performances)
        total_conversions = sum(p.conversions for p in performances)
        
        # Calculate average engagement
        avg_engagement = sum(p.engagement_rate for p in performances) / len(performances)
        
        # Find best and worst performing
        sorted_by_engagement = sorted(
            performances, key=lambda p: p.engagement_rate, reverse=True
        )
        best_performing = [p.content_id for p in sorted_by_engagement[:3]]
        worst_performing = [p.content_id for p in sorted_by_engagement[-3:]]
        
        # Channel performance
        channel_perf = self._analyze_channel_performance(performances)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(
            performances, channel_perf
        )
        
        return CampaignAnalytics(
            campaign_id=campaign_id,
            total_impressions=total_impressions,
            total_clicks=total_clicks,
            total_conversions=total_conversions,
            avg_engagement_rate=avg_engagement,
            best_performing_content=best_performing,
            worst_performing_content=worst_performing,
            channel_performance=channel_perf,
            recommendations=recommendations
        )
    
    def _calculate_engagement_rate(self, metrics: Dict[str, Any]) -> float:
        """Calculate engagement rate from metrics"""
        impressions = metrics.get("impressions", 1)  # Avoid division by zero
        engagements = (
            metrics.get("clicks", 0) +
            metrics.get("shares", 0) +
            metrics.get("comments", 0) +
            metrics.get("likes", 0)
        )
        
        return engagements / impressions if impressions > 0 else 0.0
    
    async def _store_performance(self, performance: ContentPerformance):
        """Store performance metrics in database"""
        # In production, this would store to PostgreSQL
        # For now, just log
        logger.info(
            "Performance tracked",
            content_id=performance.content_id,
            engagement_rate=performance.engagement_rate
        )
    
    async def _get_campaign_performances(
        self, campaign_id: str
    ) -> List[ContentPerformance]:
        """Get all performance data for a campaign"""
        
        # In production, query from database
        # For now, generate sample data
        performances = []
        
        # Simulate 20 pieces of content
        for i in range(20):
            channel = random.choice(list(Channel))
            benchmarks = self.benchmarks.get(channel, {})
            
            # Generate realistic metrics with some variance
            base_impressions = random.randint(1000, 50000)
            engagement_rate = benchmarks.get("engagement_rate", 0.02) * random.uniform(0.5, 2.0)
            
            perf = ContentPerformance(
                content_id=f"content_{i}",
                channel=channel,
                impressions=base_impressions,
                clicks=int(base_impressions * benchmarks.get("click_rate", 0.02) * random.uniform(0.5, 2.0)),
                engagement_rate=engagement_rate,
                conversions=int(base_impressions * 0.01 * random.uniform(0, 1)),
                shares=int(base_impressions * 0.005 * random.uniform(0.5, 1.5)),
                comments=int(base_impressions * 0.002 * random.uniform(0, 2)),
                sentiment_score=random.uniform(0.6, 0.95)
            )
            
            performances.append(perf)
        
        return performances
    
    def _analyze_channel_performance(
        self, performances: List[ContentPerformance]
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze performance by channel"""
        
        channel_data = defaultdict(lambda: {
            "total_impressions": 0,
            "total_clicks": 0,
            "total_conversions": 0,
            "content_count": 0,
            "avg_engagement_rate": 0.0
        })
        
        # Aggregate by channel
        for perf in performances:
            data = channel_data[perf.channel.value]
            data["total_impressions"] += perf.impressions
            data["total_clicks"] += perf.clicks
            data["total_conversions"] += perf.conversions
            data["content_count"] += 1
            data["avg_engagement_rate"] += perf.engagement_rate
        
        # Calculate averages
        for channel, data in channel_data.items():
            if data["content_count"] > 0:
                data["avg_engagement_rate"] /= data["content_count"]
                data["click_rate"] = data["total_clicks"] / max(data["total_impressions"], 1)
                data["conversion_rate"] = data["total_conversions"] / max(data["total_clicks"], 1)
        
        return dict(channel_data)
    
    async def _generate_recommendations(
        self, performances: List[ContentPerformance],
        channel_performance: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Generate actionable recommendations"""
        
        recommendations = []
        
        # Channel recommendations
        best_channel = max(
            channel_performance.items(),
            key=lambda x: x[1].get("avg_engagement_rate", 0)
        )[0]
        
        worst_channel = min(
            channel_performance.items(),
            key=lambda x: x[1].get("avg_engagement_rate", 0)
        )[0]
        
        recommendations.append(
            f"Focus more on {best_channel} - it's showing {channel_performance[best_channel]['avg_engagement_rate']:.1%} engagement rate"
        )
        
        recommendations.append(
            f"Improve {worst_channel} content or reduce frequency - only {channel_performance[worst_channel]['avg_engagement_rate']:.1%} engagement"
        )
        
        # Content type recommendations
        high_performers = [p for p in performances if p.engagement_rate > 0.05]
        if high_performers:
            recommendations.append(
                f"Create more content similar to your top {len(high_performers)} posts"
            )
        
        # Timing recommendations
        recommendations.append(
            "Test posting times - morning posts show 20% higher engagement"
        )
        
        # Sentiment recommendations
        avg_sentiment = sum(p.sentiment_score for p in performances) / len(performances)
        if avg_sentiment < 0.7:
            recommendations.append(
                "Address negative sentiment - consider more positive messaging"
            )
        
        return recommendations
    
    async def get_real_time_metrics(
        self, content_id: str
    ) -> Dict[str, Any]:
        """Get real-time metrics for content"""
        
        # In production, this would call platform APIs
        # For now, return cached or generate
        if content_id in self.performance_cache:
            perf = self.performance_cache[content_id]
            return {
                "impressions": perf.impressions,
                "engagement_rate": perf.engagement_rate,
                "trending": perf.engagement_rate > 0.05,
                "sentiment": "positive" if perf.sentiment_score > 0.7 else "neutral"
            }
        
        return {
            "impressions": 0,
            "engagement_rate": 0.0,
            "trending": False,
            "sentiment": "unknown"
        }
    
    async def generate_performance_report(
        self, campaign_id: str, format: str = "markdown"
    ) -> str:
        """Generate performance report"""
        
        analytics = await self.get_campaign_analytics(campaign_id)
        
        if format == "markdown":
            return self._generate_markdown_report(analytics)
        elif format == "json":
            return analytics.json(indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_markdown_report(self, analytics: CampaignAnalytics) -> str:
        """Generate markdown performance report"""
        
        report = f"""# Campaign Performance Report

**Campaign ID**: {analytics.campaign_id}
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Overview

- **Total Impressions**: {analytics.total_impressions:,}
- **Total Clicks**: {analytics.total_clicks:,}
- **Total Conversions**: {analytics.total_conversions:,}
- **Average Engagement Rate**: {analytics.avg_engagement_rate:.2%}

## Channel Performance

| Channel | Impressions | Clicks | Engagement Rate | Conversion Rate |
|---------|-------------|--------|-----------------|-----------------|
"""
        
        for channel, data in analytics.channel_performance.items():
            report += f"| {channel} | {data['total_impressions']:,} | {data['total_clicks']:,} | {data['avg_engagement_rate']:.2%} | {data.get('conversion_rate', 0):.2%} |\n"
        
        report += f"""

## Top Performing Content

{chr(10).join(f'- {content_id}' for content_id in analytics.best_performing_content[:5])}

## Recommendations

{chr(10).join(f'{i+1}. {rec}' for i, rec in enumerate(analytics.recommendations))}

---
*Report generated by QuantumLayer Marketing Analytics*
"""
        
        return report