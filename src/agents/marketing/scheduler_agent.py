"""
Scheduler Agent - Optimizes content scheduling across channels
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, time
import asyncio
import random

from src.agents.marketing.models import Channel, ContentType, CampaignObjective
import structlog

logger = structlog.get_logger()


class SchedulerAgent:
    """Optimizes content scheduling for maximum engagement"""
    
    def __init__(self):
        # Optimal posting times by channel (UTC)
        self.optimal_times = {
            Channel.TWITTER: [
                time(13, 0),  # 9 AM EST
                time(17, 0),  # 1 PM EST
                time(20, 0),  # 4 PM EST
            ],
            Channel.LINKEDIN: [
                time(12, 0),  # 8 AM EST
                time(17, 0),  # 1 PM EST
                time(22, 0),  # 6 PM EST
            ],
            Channel.REDDIT: [
                time(13, 0),  # 9 AM EST
                time(18, 0),  # 2 PM EST
                time(1, 0),   # 9 PM EST
            ],
            Channel.EMAIL: [
                time(14, 0),  # 10 AM EST
            ],
            Channel.MEDIUM: [
                time(12, 0),  # 8 AM EST
                time(16, 0),  # 12 PM EST
            ]
        }
        
        # Content type distribution by objective
        self.content_distribution = {
            CampaignObjective.LAUNCH_AWARENESS: {
                ContentType.TWEET_THREAD: 0.3,
                ContentType.LINKEDIN_POST: 0.2,
                ContentType.PRODUCT_LAUNCH: 0.2,
                ContentType.EMAIL_CAMPAIGN: 0.15,
                ContentType.BLOG_POST: 0.15
            },
            CampaignObjective.TECHNICAL_EVANGELISM: {
                ContentType.BLOG_POST: 0.35,
                ContentType.TWEET_THREAD: 0.25,
                ContentType.REDDIT_POST: 0.2,
                ContentType.VIDEO_SCRIPT: 0.2
            },
            CampaignObjective.LEAD_GENERATION: {
                ContentType.LANDING_PAGE: 0.3,
                ContentType.EMAIL_CAMPAIGN: 0.3,
                ContentType.LINKEDIN_POST: 0.2,
                ContentType.BLOG_POST: 0.2
            }
        }
    
    async def create_calendar(
        self,
        channels: List[Channel],
        duration_days: int,
        objective: CampaignObjective,
        launch_date: datetime
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Create optimized content calendar"""
        
        calendar = {}
        current_date = launch_date
        
        # Get content distribution for objective
        distribution = self.content_distribution.get(
            objective, 
            self._get_default_distribution()
        )
        
        # Plan content for each day
        for day in range(duration_days):
            date_key = current_date.strftime("%Y-%m-%d")
            daily_content = []
            
            # Determine content for this day
            if day == 0:  # Launch day
                daily_content.extend(self._plan_launch_day(channels, current_date))
            elif day % 7 == 0:  # Weekly highlights
                daily_content.extend(self._plan_weekly_content(channels, current_date))
            else:  # Regular days
                daily_content.extend(
                    self._plan_regular_day(channels, current_date, distribution)
                )
            
            if daily_content:
                calendar[date_key] = daily_content
            
            current_date += timedelta(days=1)
        
        return calendar
    
    def _plan_launch_day(
        self, channels: List[Channel], date: datetime
    ) -> List[Dict[str, Any]]:
        """Plan content for launch day"""
        content = []
        
        # Morning: Product Hunt launch
        if Channel.PRODUCTHUNT in channels:
            content.append({
                "type": ContentType.PRODUCT_LAUNCH.value,
                "channel": Channel.PRODUCTHUNT.value,
                "scheduled_time": datetime.combine(date, time(8, 0)),
                "priority": "high"
            })
        
        # Mid-morning: Twitter announcement
        if Channel.TWITTER in channels:
            content.append({
                "type": ContentType.TWEET_THREAD.value,
                "channel": Channel.TWITTER.value,
                "scheduled_time": datetime.combine(date, time(13, 0)),
                "priority": "high"
            })
        
        # Afternoon: LinkedIn post
        if Channel.LINKEDIN in channels:
            content.append({
                "type": ContentType.LINKEDIN_POST.value,
                "channel": Channel.LINKEDIN.value,
                "scheduled_time": datetime.combine(date, time(17, 0)),
                "priority": "high"
            })
        
        # Evening: Email announcement
        if Channel.EMAIL in channels:
            content.append({
                "type": ContentType.EMAIL_CAMPAIGN.value,
                "channel": Channel.EMAIL.value,
                "scheduled_time": datetime.combine(date, time(19, 0)),
                "priority": "high"
            })
        
        return content
    
    def _plan_weekly_content(
        self, channels: List[Channel], date: datetime
    ) -> List[Dict[str, Any]]:
        """Plan weekly highlight content"""
        content = []
        
        # Weekly blog post
        if Channel.MEDIUM in channels:
            content.append({
                "type": ContentType.BLOG_POST.value,
                "channel": Channel.MEDIUM.value,
                "scheduled_time": datetime.combine(date, time(12, 0)),
                "priority": "medium"
            })
        
        # Weekly thread recap
        if Channel.TWITTER in channels:
            content.append({
                "type": ContentType.TWEET_THREAD.value,
                "channel": Channel.TWITTER.value,
                "scheduled_time": datetime.combine(date, time(17, 0)),
                "priority": "medium"
            })
        
        return content
    
    def _plan_regular_day(
        self, channels: List[Channel], 
        date: datetime,
        distribution: Dict[ContentType, float]
    ) -> List[Dict[str, Any]]:
        """Plan content for regular days"""
        content = []
        
        # Select 1-3 pieces of content based on channels
        num_pieces = min(len(channels), random.randint(1, 3))
        
        # Randomly select content types based on distribution
        selected_types = self._weighted_random_selection(
            list(distribution.keys()),
            list(distribution.values()),
            num_pieces
        )
        
        # Assign to channels and times
        available_channels = channels.copy()
        for content_type in selected_types:
            # Find suitable channel
            channel = self._get_suitable_channel(content_type, available_channels)
            if not channel:
                continue
                
            # Get optimal time
            posting_time = self._get_optimal_time(channel, date)
            
            content.append({
                "type": content_type.value,
                "channel": channel.value,
                "scheduled_time": posting_time,
                "priority": "normal"
            })
            
            # Remove used channel to avoid duplicates
            if channel in available_channels:
                available_channels.remove(channel)
        
        return content
    
    def _get_suitable_channel(
        self, content_type: ContentType, available_channels: List[Channel]
    ) -> Optional[Channel]:
        """Match content type to suitable channel"""
        
        channel_map = {
            ContentType.TWEET_THREAD: Channel.TWITTER,
            ContentType.LINKEDIN_POST: Channel.LINKEDIN,
            ContentType.BLOG_POST: Channel.MEDIUM,
            ContentType.REDDIT_POST: Channel.REDDIT,
            ContentType.EMAIL_CAMPAIGN: Channel.EMAIL,
            ContentType.PRODUCT_LAUNCH: Channel.PRODUCTHUNT,
            ContentType.VIDEO_SCRIPT: Channel.YOUTUBE,
            ContentType.LANDING_PAGE: Channel.EMAIL  # Email drives to landing
        }
        
        preferred = channel_map.get(content_type)
        if preferred and preferred in available_channels:
            return preferred
        
        # Fallback to any available channel
        return available_channels[0] if available_channels else None
    
    def _get_optimal_time(self, channel: Channel, date: datetime) -> datetime:
        """Get optimal posting time for channel"""
        times = self.optimal_times.get(channel, [time(12, 0)])
        
        # Add some randomness to avoid being too predictable
        selected_time = random.choice(times)
        
        # Add random minutes
        minutes_offset = random.randint(-30, 30)
        posting_datetime = datetime.combine(date, selected_time)
        posting_datetime += timedelta(minutes=minutes_offset)
        
        return posting_datetime
    
    def _weighted_random_selection(
        self, items: List[Any], weights: List[float], k: int
    ) -> List[Any]:
        """Select k items based on weights"""
        if len(items) <= k:
            return items
            
        selected = []
        items_copy = items.copy()
        weights_copy = weights.copy()
        
        for _ in range(k):
            if not items_copy:
                break
                
            # Normalize weights
            total = sum(weights_copy)
            if total == 0:
                break
                
            probs = [w/total for w in weights_copy]
            
            # Select item
            import numpy as np
            idx = np.random.choice(len(items_copy), p=probs)
            
            selected.append(items_copy[idx])
            
            # Remove selected item
            items_copy.pop(idx)
            weights_copy.pop(idx)
        
        return selected
    
    def _get_default_distribution(self) -> Dict[ContentType, float]:
        """Get default content distribution"""
        return {
            ContentType.TWEET_THREAD: 0.25,
            ContentType.LINKEDIN_POST: 0.2,
            ContentType.BLOG_POST: 0.2,
            ContentType.EMAIL_CAMPAIGN: 0.15,
            ContentType.REDDIT_POST: 0.1,
            ContentType.VIDEO_SCRIPT: 0.1
        }
    
    async def optimize_schedule(
        self, calendar: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Optimize existing schedule for better engagement"""
        
        optimized = {}
        
        for date_key, content_list in calendar.items():
            # Check for conflicts
            content_list = self._resolve_time_conflicts(content_list)
            
            # Ensure minimum spacing
            content_list = self._ensure_spacing(content_list)
            
            # Balance across day parts
            content_list = self._balance_day_parts(content_list)
            
            optimized[date_key] = content_list
        
        return optimized
    
    def _resolve_time_conflicts(
        self, content_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Resolve scheduling conflicts"""
        
        # Sort by time
        sorted_content = sorted(
            content_list, 
            key=lambda x: x.get("scheduled_time", datetime.now())
        )
        
        # Ensure at least 1 hour between posts
        for i in range(1, len(sorted_content)):
            prev_time = sorted_content[i-1]["scheduled_time"]
            curr_time = sorted_content[i]["scheduled_time"]
            
            if (curr_time - prev_time).total_seconds() < 3600:
                # Delay current post
                sorted_content[i]["scheduled_time"] = prev_time + timedelta(hours=1)
        
        return sorted_content
    
    def _ensure_spacing(
        self, content_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Ensure proper spacing between posts"""
        
        # Group by channel
        by_channel = {}
        for content in content_list:
            channel = content["channel"]
            if channel not in by_channel:
                by_channel[channel] = []
            by_channel[channel].append(content)
        
        # Ensure channel-specific spacing
        spacing_rules = {
            Channel.TWITTER.value: timedelta(hours=4),
            Channel.LINKEDIN.value: timedelta(hours=8),
            Channel.EMAIL.value: timedelta(days=1)
        }
        
        for channel, posts in by_channel.items():
            min_spacing = spacing_rules.get(channel, timedelta(hours=6))
            
            posts.sort(key=lambda x: x["scheduled_time"])
            for i in range(1, len(posts)):
                if posts[i]["scheduled_time"] - posts[i-1]["scheduled_time"] < min_spacing:
                    posts[i]["scheduled_time"] = posts[i-1]["scheduled_time"] + min_spacing
        
        # Flatten back
        return [post for posts in by_channel.values() for post in posts]
    
    def _balance_day_parts(
        self, content_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Balance content across day parts"""
        
        # Define day parts
        morning = (time(6, 0), time(12, 0))
        afternoon = (time(12, 0), time(18, 0))
        evening = (time(18, 0), time(23, 59))
        
        # Count posts per day part
        counts = {"morning": 0, "afternoon": 0, "evening": 0}
        
        for content in content_list:
            post_time = content["scheduled_time"].time()
            if morning[0] <= post_time < morning[1]:
                counts["morning"] += 1
            elif afternoon[0] <= post_time < afternoon[1]:
                counts["afternoon"] += 1
            else:
                counts["evening"] += 1
        
        # Rebalance if needed
        # This is simplified - production would be more sophisticated
        
        return content_list