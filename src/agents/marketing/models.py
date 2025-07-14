"""
Marketing Campaign Models
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class Channel(str, Enum):
    """Marketing channels"""
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    MEDIUM = "medium"
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    EMAIL = "email"
    DEVTO = "devto"
    PRODUCTHUNT = "producthunt"
    YOUTUBE = "youtube"


class ContentType(str, Enum):
    """Types of marketing content"""
    TWEET_THREAD = "tweet_thread"
    LINKEDIN_POST = "linkedin_post"
    BLOG_POST = "blog_post"
    EMAIL_CAMPAIGN = "email_campaign"
    REDDIT_POST = "reddit_post"
    VIDEO_SCRIPT = "video_script"
    LANDING_PAGE = "landing_page"
    PRODUCT_LAUNCH = "product_launch"


class ToneStyle(str, Enum):
    """Content tone styles"""
    TECHNICAL = "technical"
    VISIONARY = "visionary"
    EDUCATIONAL = "educational"
    CONVERSATIONAL = "conversational"
    AUTHORITATIVE = "authoritative"
    INSPIRATIONAL = "inspirational"
    ANALYTICAL = "analytical"


class CampaignObjective(str, Enum):
    """Campaign objectives"""
    LAUNCH_AWARENESS = "launch_awareness"
    TECHNICAL_EVANGELISM = "technical_evangelism"
    FOUNDER_AUTHORITY = "founder_authority"
    LEAD_GENERATION = "lead_generation"
    COMMUNITY_BUILDING = "community_building"
    INVESTOR_OUTREACH = "investor_outreach"
    TALENT_ACQUISITION = "talent_acquisition"


class MarketingContent(BaseModel):
    """Individual piece of marketing content"""
    content_id: str = Field(default_factory=lambda: f"content_{datetime.now().timestamp()}")
    type: ContentType
    channel: Channel
    title: Optional[str] = None
    content: str
    tone: ToneStyle
    target_audience: str
    keywords: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    cta: Optional[str] = None
    media_urls: List[str] = Field(default_factory=list)
    scheduled_time: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CampaignRequest(BaseModel):
    """Request to generate a marketing campaign"""
    objective: CampaignObjective
    product_description: str
    key_features: List[str]
    target_audience: str
    unique_value_prop: str
    duration_days: int = 30
    channels: List[Channel]
    tone_preferences: List[ToneStyle]
    competitor_insights: Optional[str] = None
    constraints: Optional[str] = None
    launch_date: Optional[datetime] = None


class MarketingCampaign(BaseModel):
    """Complete marketing campaign"""
    campaign_id: str = Field(default_factory=lambda: f"campaign_{datetime.now().timestamp()}")
    objective: CampaignObjective
    target_audience: str
    duration_days: int
    content_pieces: List[MarketingContent]
    content_calendar: Dict[str, List[str]]  # date -> content_ids
    strategy_summary: str
    kpis: Dict[str, Any]
    total_pieces: int = 0
    channels_used: List[Channel] = Field(default_factory=list)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.total_pieces = len(self.content_pieces)
        self.channels_used = list(set(c.channel for c in self.content_pieces))


class ContentPerformance(BaseModel):
    """Performance metrics for content"""
    content_id: str
    channel: Channel
    impressions: int = 0
    clicks: int = 0
    engagement_rate: float = 0.0
    conversions: int = 0
    shares: int = 0
    comments: int = 0
    sentiment_score: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


class CampaignAnalytics(BaseModel):
    """Analytics for entire campaign"""
    campaign_id: str
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    avg_engagement_rate: float = 0.0
    best_performing_content: List[str] = Field(default_factory=list)
    worst_performing_content: List[str] = Field(default_factory=list)
    channel_performance: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)