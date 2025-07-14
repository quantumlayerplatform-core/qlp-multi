"""
Social Media Publisher - Handles automated posting to various platforms
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import json
from enum import Enum
import structlog
from abc import ABC, abstractmethod

import httpx
import tweepy
from linkedin_api import Linkedin

from src.common.config import settings
from src.agents.marketing.models import ContentPiece, Channel

logger = structlog.get_logger()


class PublishStatus(str, Enum):
    """Publishing status"""
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"
    RETRY = "retry"


class PublishResult:
    """Result of a publishing attempt"""
    def __init__(
        self,
        content_id: str,
        channel: Channel,
        status: PublishStatus,
        platform_id: Optional[str] = None,
        url: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.content_id = content_id
        self.channel = channel
        self.status = status
        self.platform_id = platform_id  # Tweet ID, LinkedIn post ID, etc.
        self.url = url
        self.error = error
        self.metadata = metadata or {}
        self.published_at = datetime.utcnow()


class PlatformPublisher(ABC):
    """Abstract base class for platform publishers"""
    
    @abstractmethod
    async def publish(self, content: ContentPiece) -> PublishResult:
        """Publish content to the platform"""
        pass
    
    @abstractmethod
    async def verify_credentials(self) -> bool:
        """Verify platform credentials are valid"""
        pass
    
    @abstractmethod
    async def get_rate_limits(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        pass


class TwitterPublisher(PlatformPublisher):
    """Twitter/X publishing implementation"""
    
    def __init__(self):
        # Initialize Twitter API v2 client
        self.client = tweepy.Client(
            bearer_token=settings.TWITTER_BEARER_TOKEN,
            consumer_key=settings.TWITTER_API_KEY,
            consumer_secret=settings.TWITTER_API_SECRET,
            access_token=settings.TWITTER_ACCESS_TOKEN,
            access_token_secret=settings.TWITTER_ACCESS_SECRET,
            wait_on_rate_limit=True
        )
    
    async def publish(self, content: ContentPiece) -> PublishResult:
        """Publish content to Twitter"""
        try:
            if content.type == "tweet_thread":
                # Split thread and post sequentially
                tweets = self._split_thread(content.content)
                tweet_ids = []
                reply_to_id = None
                
                for tweet_text in tweets:
                    response = await asyncio.to_thread(
                        self.client.create_tweet,
                        text=tweet_text,
                        reply_to_tweet_id=reply_to_id
                    )
                    tweet_id = response.data['id']
                    tweet_ids.append(tweet_id)
                    reply_to_id = tweet_id  # Next tweet replies to this one
                    
                    # Small delay between tweets
                    await asyncio.sleep(1)
                
                return PublishResult(
                    content_id=content.content_id,
                    channel=Channel.TWITTER,
                    status=PublishStatus.PUBLISHED,
                    platform_id=tweet_ids[0],  # First tweet ID
                    url=f"https://twitter.com/i/web/status/{tweet_ids[0]}",
                    metadata={"thread_ids": tweet_ids}
                )
            else:
                # Single tweet
                response = await asyncio.to_thread(
                    self.client.create_tweet,
                    text=content.content
                )
                
                return PublishResult(
                    content_id=content.content_id,
                    channel=Channel.TWITTER,
                    status=PublishStatus.PUBLISHED,
                    platform_id=response.data['id'],
                    url=f"https://twitter.com/i/web/status/{response.data['id']}"
                )
                
        except Exception as e:
            logger.error(f"Twitter publishing failed: {e}")
            return PublishResult(
                content_id=content.content_id,
                channel=Channel.TWITTER,
                status=PublishStatus.FAILED,
                error=str(e)
            )
    
    def _split_thread(self, content: str) -> List[str]:
        """Split thread content into individual tweets"""
        # Simple split by numbered sections (1/7, 2/7, etc.)
        import re
        
        # Try to split by tweet markers
        tweet_pattern = r'\d+/\d+[:\s]+'
        tweets = re.split(tweet_pattern, content)
        
        # Filter out empty strings and clean up
        tweets = [t.strip() for t in tweets if t.strip()]
        
        # If no clear splits, split by double newlines
        if len(tweets) <= 1:
            tweets = content.split('\n\n')
            tweets = [t.strip() for t in tweets if t.strip()]
        
        # Ensure tweets are within character limit
        final_tweets = []
        for tweet in tweets:
            if len(tweet) <= 280:
                final_tweets.append(tweet)
            else:
                # Split long tweets
                words = tweet.split()
                current = []
                for word in words:
                    if len(' '.join(current + [word])) <= 275:  # Leave room
                        current.append(word)
                    else:
                        final_tweets.append(' '.join(current))
                        current = [word]
                if current:
                    final_tweets.append(' '.join(current))
        
        return final_tweets
    
    async def verify_credentials(self) -> bool:
        """Verify Twitter credentials"""
        try:
            await asyncio.to_thread(self.client.get_me)
            return True
        except:
            return False
    
    async def get_rate_limits(self) -> Dict[str, Any]:
        """Get Twitter rate limits"""
        # Twitter v2 doesn't provide easy rate limit access
        return {"tweets_remaining": "unknown"}


class LinkedInPublisher(PlatformPublisher):
    """LinkedIn publishing implementation"""
    
    def __init__(self):
        # Note: linkedin_api is unofficial and requires username/password
        # For production, use official LinkedIn API with OAuth
        self.client = Linkedin(
            settings.LINKEDIN_EMAIL,
            settings.LINKEDIN_PASSWORD
        )
    
    async def publish(self, content: ContentPiece) -> PublishResult:
        """Publish content to LinkedIn"""
        try:
            # Post to LinkedIn
            # Note: This is using unofficial API - for production use OAuth
            response = await asyncio.to_thread(
                self.client.submit_share,
                content.content,
                main_type="com.linkedin.publishing.PublishedShareText",
                title=content.title
            )
            
            return PublishResult(
                content_id=content.content_id,
                channel=Channel.LINKEDIN,
                status=PublishStatus.PUBLISHED,
                platform_id=response.get('id'),
                url=response.get('url')
            )
            
        except Exception as e:
            logger.error(f"LinkedIn publishing failed: {e}")
            return PublishResult(
                content_id=content.content_id,
                channel=Channel.LINKEDIN,
                status=PublishStatus.FAILED,
                error=str(e)
            )
    
    async def verify_credentials(self) -> bool:
        """Verify LinkedIn credentials"""
        try:
            await asyncio.to_thread(self.client.get_profile)
            return True
        except:
            return False
    
    async def get_rate_limits(self) -> Dict[str, Any]:
        """Get LinkedIn rate limits"""
        return {"posts_remaining": "unknown"}


class SocialMediaPublisher:
    """Main publisher that coordinates all platform publishers"""
    
    def __init__(self):
        self.publishers: Dict[Channel, PlatformPublisher] = {}
        self._initialize_publishers()
    
    def _initialize_publishers(self):
        """Initialize available publishers based on config"""
        if all([
            settings.TWITTER_API_KEY,
            settings.TWITTER_API_SECRET,
            settings.TWITTER_ACCESS_TOKEN,
            settings.TWITTER_ACCESS_SECRET
        ]):
            self.publishers[Channel.TWITTER] = TwitterPublisher()
            logger.info("Twitter publisher initialized")
        
        if all([
            settings.LINKEDIN_EMAIL,
            settings.LINKEDIN_PASSWORD
        ]):
            self.publishers[Channel.LINKEDIN] = LinkedInPublisher()
            logger.info("LinkedIn publisher initialized")
    
    async def publish_content(self, content: ContentPiece) -> PublishResult:
        """Publish content to appropriate platform"""
        if content.channel not in self.publishers:
            return PublishResult(
                content_id=content.content_id,
                channel=content.channel,
                status=PublishStatus.FAILED,
                error=f"No publisher configured for {content.channel.value}"
            )
        
        publisher = self.publishers[content.channel]
        return await publisher.publish(content)
    
    async def publish_batch(
        self,
        content_pieces: List[ContentPiece],
        max_concurrent: int = 3
    ) -> List[PublishResult]:
        """Publish multiple content pieces with rate limiting"""
        results = []
        
        # Group by channel to respect rate limits
        by_channel = {}
        for piece in content_pieces:
            if piece.channel not in by_channel:
                by_channel[piece.channel] = []
            by_channel[piece.channel].append(piece)
        
        # Publish each channel's content
        for channel, pieces in by_channel.items():
            if channel not in self.publishers:
                # Skip unconfigured channels
                for piece in pieces:
                    results.append(PublishResult(
                        content_id=piece.content_id,
                        channel=channel,
                        status=PublishStatus.FAILED,
                        error=f"No publisher for {channel.value}"
                    ))
                continue
            
            # Publish with concurrency limit
            for i in range(0, len(pieces), max_concurrent):
                batch = pieces[i:i + max_concurrent]
                batch_results = await asyncio.gather(
                    *[self.publish_content(piece) for piece in batch],
                    return_exceptions=True
                )
                
                for piece, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        results.append(PublishResult(
                            content_id=piece.content_id,
                            channel=channel,
                            status=PublishStatus.FAILED,
                            error=str(result)
                        ))
                    else:
                        results.append(result)
                
                # Delay between batches
                if i + max_concurrent < len(pieces):
                    await asyncio.sleep(2)
        
        return results
    
    async def verify_all_credentials(self) -> Dict[Channel, bool]:
        """Verify credentials for all configured publishers"""
        results = {}
        for channel, publisher in self.publishers.items():
            results[channel] = await publisher.verify_credentials()
        return results
    
    def get_configured_channels(self) -> List[Channel]:
        """Get list of configured channels"""
        return list(self.publishers.keys())


# Global publisher instance
social_publisher = SocialMediaPublisher()