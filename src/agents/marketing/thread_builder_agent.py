"""
Thread Builder Agent - Designs compelling multi-tweet narratives
"""

from typing import List, Dict, Any, Optional
import asyncio
from src.agents.azure_llm_client import llm_client, LLMProvider
from src.common.config import settings
import structlog

logger = structlog.get_logger()


class ThreadBuilderAgent:
    """Constructs engaging Twitter/X thread narratives"""
    
    def __init__(self):
        self.llm_client = llm_client
        
        # Thread structure patterns
        self.thread_patterns = {
            "story_arc": {
                "structure": ["hook", "problem", "journey", "solution", "impact", "lesson", "cta"],
                "description": "Personal story with clear narrative arc"
            },
            "educational": {
                "structure": ["claim", "why_matters", "concept_1", "concept_2", "concept_3", "examples", "implementation", "results", "resources", "cta"],
                "description": "Teaching complex concepts step by step"
            },
            "contrarian": {
                "structure": ["controversial_take", "common_belief", "why_wrong", "evidence", "alternative", "benefits", "objections", "proof", "mindset_shift", "action"],
                "description": "Challenge conventional wisdom"
            },
            "case_study": {
                "structure": ["result_hook", "context", "challenge", "approach", "process", "obstacles", "breakthrough", "outcome", "lessons", "your_turn"],
                "description": "Deep dive into specific success"
            },
            "comparison": {
                "structure": ["bold_claim", "option_a", "option_b", "criteria_1", "criteria_2", "criteria_3", "winner", "when_to_use", "action"],
                "description": "Compare approaches or tools"
            }
        }
    
    async def build_thread(
        self,
        topic: str,
        key_points: List[str],
        pattern: str = "educational",
        target_audience: str = "developers",
        tone: str = "conversational",
        include_media: bool = True
    ) -> Dict[str, Any]:
        """Build a complete thread with optimal structure"""
        
        # Select thread pattern
        thread_structure = self.thread_patterns.get(
            pattern, 
            self.thread_patterns["educational"]
        )
        
        # Generate thread content
        tweets = await self._generate_thread_content(
            topic=topic,
            key_points=key_points,
            structure=thread_structure["structure"],
            audience=target_audience,
            tone=tone
        )
        
        # Optimize for engagement
        optimized_tweets = await self._optimize_thread(tweets, include_media)
        
        # Add thread metadata
        thread_data = {
            "tweets": optimized_tweets,
            "pattern": pattern,
            "structure": thread_structure["structure"],
            "estimated_read_time": len(optimized_tweets) * 15,  # seconds
            "media_suggestions": self._suggest_media(optimized_tweets) if include_media else [],
            "optimal_posting_time": self._calculate_optimal_time(target_audience),
            "hashtag_suggestions": self._suggest_hashtags(topic, optimized_tweets),
            "engagement_hooks": self._identify_hooks(optimized_tweets)
        }
        
        return thread_data
    
    async def _generate_thread_content(
        self,
        topic: str,
        key_points: List[str],
        structure: List[str],
        audience: str,
        tone: str
    ) -> List[str]:
        """Generate thread content based on structure"""
        
        prompt = f"""Create a {len(structure)}-tweet thread about: {topic}

Key points to cover:
{chr(10).join(f'- {point}' for point in key_points)}

Thread structure:
{chr(10).join(f'{i+1}. {element.replace("_", " ").title()}' for i, element in enumerate(structure))}

Target audience: {audience}
Tone: {tone}

Requirements:
1. First tweet must hook attention immediately
2. Each tweet should be 200-250 characters (save room for numbering)
3. Use line breaks for readability
4. Include specific examples or data
5. End each tweet with intrigue for the next
6. Final tweet has clear CTA

Format each tweet as:
Tweet 1: [content]
Tweet 2: [content]
etc."""

        try:
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                max_tokens=2000,
                temperature=0.7
            )
            
            return self._parse_tweets(response.get("content", ""))
            
        except Exception as e:
            logger.error("Thread generation failed", error=str(e))
            return self._generate_fallback_thread(topic, structure)
    
    async def _optimize_thread(
        self, tweets: List[str], include_media: bool
    ) -> List[str]:
        """Optimize thread for maximum engagement"""
        
        optimized = []
        
        for i, tweet in enumerate(tweets):
            # Add thread numbering
            if i == 0:
                # First tweet doesn't need number but needs thread indicator
                optimized_tweet = f"{tweet}\n\n🧵👇"
            else:
                # Subsequent tweets get numbering
                optimized_tweet = f"{i+1}/\n\n{tweet}"
            
            # Ensure optimal length
            if len(optimized_tweet) > 270:
                optimized_tweet = self._shorten_tweet(optimized_tweet)
            
            # Add engagement elements
            if i == len(tweets) - 1:
                # Last tweet - ensure CTA
                if "?" not in optimized_tweet and "→" not in optimized_tweet:
                    optimized_tweet += "\n\nWhat's your experience? 🤔"
            elif i == 0:
                # First tweet - ensure hook
                if not any(char in optimized_tweet[:50] for char in ["!", "?", "🚀", "💡", "⚡"]):
                    optimized_tweet = "🚀 " + optimized_tweet
            
            optimized.append(optimized_tweet)
        
        return optimized
    
    def _parse_tweets(self, raw_content: str) -> List[str]:
        """Parse LLM response into individual tweets"""
        tweets = []
        lines = raw_content.strip().split('\n')
        
        current_tweet = ""
        for line in lines:
            if line.startswith("Tweet ") and current_tweet:
                tweets.append(current_tweet.strip())
                # Extract content after "Tweet X: "
                parts = line.split(":", 1)
                current_tweet = parts[1].strip() if len(parts) > 1 else ""
            elif line.strip() and not line.startswith("Tweet "):
                if current_tweet:
                    current_tweet += " " + line.strip()
                else:
                    current_tweet = line.strip()
        
        if current_tweet:
            tweets.append(current_tweet.strip())
        
        # Ensure we have at least 5 tweets
        while len(tweets) < 5:
            tweets.append(f"Additional insight #{len(tweets)+1} about this topic...")
        
        return tweets[:10]  # Max 10 tweets
    
    def _shorten_tweet(self, tweet: str) -> str:
        """Shorten tweet while preserving meaning"""
        # Remove extra spaces
        tweet = " ".join(tweet.split())
        
        # Common shortenings
        replacements = {
            "because": "b/c",
            "without": "w/o",
            "with": "w/",
            "and": "&",
            "at": "@",
            "your": "ur",
            "you": "u",
            "to": "2",
            "for": "4"
        }
        
        for long, short in replacements.items():
            if len(tweet) > 270:
                tweet = tweet.replace(f" {long} ", f" {short} ")
        
        return tweet[:270]
    
    def _suggest_media(self, tweets: List[str]) -> List[Dict[str, Any]]:
        """Suggest media for each tweet"""
        suggestions = []
        
        for i, tweet in enumerate(tweets):
            if i == 0:
                # Hero image for first tweet
                suggestions.append({
                    "tweet_index": 0,
                    "media_type": "image",
                    "description": "Eye-catching hero graphic with thread title",
                    "specs": "1200x675px, bold text overlay"
                })
            elif "example" in tweet.lower() or "case study" in tweet.lower():
                suggestions.append({
                    "tweet_index": i,
                    "media_type": "screenshot",
                    "description": "Screenshot showing the example",
                    "specs": "1200x675px, annotated"
                })
            elif any(word in tweet.lower() for word in ["data", "stats", "numbers", "%"]):
                suggestions.append({
                    "tweet_index": i,
                    "media_type": "chart",
                    "description": "Data visualization",
                    "specs": "1200x675px, clear and simple"
                })
            elif i == len(tweets) - 1:
                # CTA image for last tweet
                suggestions.append({
                    "tweet_index": i,
                    "media_type": "cta_image",
                    "description": "Call-to-action graphic",
                    "specs": "1200x675px, include link/button"
                })
        
        return suggestions
    
    def _calculate_optimal_time(self, audience: str) -> Dict[str, Any]:
        """Calculate optimal posting time based on audience"""
        
        audience_times = {
            "developers": {"hour": 9, "timezone": "America/New_York", "day": "Tuesday"},
            "founders": {"hour": 8, "timezone": "America/New_York", "day": "Wednesday"},
            "investors": {"hour": 7, "timezone": "America/New_York", "day": "Thursday"},
            "general_tech": {"hour": 13, "timezone": "America/New_York", "day": "Tuesday"}
        }
        
        optimal = audience_times.get(
            audience.lower(), 
            audience_times["general_tech"]
        )
        
        return {
            "best_time": f"{optimal['hour']}:00 {optimal['timezone']}",
            "best_day": optimal["day"],
            "alternative_times": [
                f"{optimal['hour']+4}:00 {optimal['timezone']}",
                f"{optimal['hour']+8}:00 {optimal['timezone']}"
            ]
        }
    
    def _suggest_hashtags(self, topic: str, tweets: List[str]) -> List[str]:
        """Suggest relevant hashtags"""
        
        # Base hashtags
        hashtags = ["#BuildInPublic"]
        
        # Topic-based hashtags
        topic_lower = topic.lower()
        content_lower = " ".join(tweets).lower()
        
        if "ai" in topic_lower or "artificial intelligence" in topic_lower:
            hashtags.extend(["#AI", "#AIAgents"])
        if "developer" in topic_lower or "coding" in topic_lower:
            hashtags.extend(["#DevTools", "#Programming"])
        if "startup" in topic_lower:
            hashtags.extend(["#StartupLife", "#Founders"])
        if "launch" in content_lower:
            hashtags.append("#ProductLaunch")
        
        # Limit to 3-4 hashtags
        return list(set(hashtags))[:4]
    
    def _identify_hooks(self, tweets: List[str]) -> List[Dict[str, Any]]:
        """Identify engagement hooks in thread"""
        hooks = []
        
        for i, tweet in enumerate(tweets):
            # Questions
            if "?" in tweet:
                hooks.append({
                    "tweet_index": i,
                    "hook_type": "question",
                    "description": "Engages through curiosity"
                })
            
            # Controversy
            if any(word in tweet.lower() for word in ["unpopular", "wrong", "myth", "actually"]):
                hooks.append({
                    "tweet_index": i,
                    "hook_type": "contrarian",
                    "description": "Challenges assumptions"
                })
            
            # Data/Stats
            if any(char in tweet for char in ["$", "%", "x", "10", "100"]):
                hooks.append({
                    "tweet_index": i,
                    "hook_type": "data",
                    "description": "Concrete evidence"
                })
            
            # Personal story
            if any(word in tweet.lower() for word in ["i", "my", "we", "our"]):
                hooks.append({
                    "tweet_index": i,
                    "hook_type": "personal",
                    "description": "Relatable experience"
                })
        
        return hooks
    
    def _generate_fallback_thread(self, topic: str, structure: List[str]) -> List[str]:
        """Generate fallback thread if API fails"""
        
        fallback_templates = [
            f"Here's what most people get wrong about {topic}:",
            f"After spending 1000+ hours on {topic}, here's what I learned:",
            f"The hidden truth about {topic} that nobody talks about:",
            f"I analyzed 50+ examples of {topic}. The pattern is clear:",
            f"Why {topic} is about to change everything:",
            f"The biggest mistake people make with {topic}:",
            f"Here's the framework I use for {topic}:",
            f"The future of {topic} is already here. Most just can't see it:",
            f"What I wish I knew about {topic} when I started:",
            f"Let's talk about {topic}. Time for some real talk:"
        ]
        
        thread = [fallback_templates[0]]
        for i in range(1, min(len(structure), 9)):
            thread.append(f"Key point #{i} about {topic}...")
        
        thread.append(f"Ready to master {topic}? Here's how to start →")
        
        return thread
    
    async def analyze_successful_threads(
        self, thread_urls: List[str]
    ) -> Dict[str, Any]:
        """Analyze successful threads to extract patterns"""
        
        # In production, this would fetch and analyze real threads
        # For now, return pattern analysis
        
        return {
            "common_patterns": [
                "Strong hook in first 7 words",
                "Personal story in tweets 2-3",
                "Data/proof in middle section",
                "Clear CTA in final tweet"
            ],
            "optimal_length": 7,
            "best_hooks": [
                "Contrarian takes",
                "Specific numbers",
                "Personal failures",
                "Future predictions"
            ],
            "engagement_tactics": [
                "Ask question in tweet 4-5",
                "Include surprising fact",
                "Reference well-known example",
                "End with open loop"
            ]
        }
    
    async def remix_thread(
        self, original_thread: List[str], 
        new_angle: str
    ) -> List[str]:
        """Remix existing thread with new angle"""
        
        prompt = f"""Remix this thread with a new angle: {new_angle}

Original thread:
{chr(10).join(f'{i+1}. {tweet}' for i, tweet in enumerate(original_thread))}

Keep the same structure but change:
1. The perspective/angle
2. Examples used
3. The hook
4. The CTA

Make it feel fresh while maintaining what worked."""

        try:
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                temperature=0.8
            )
            
            return self._parse_tweets(response.get("content", ""))
            
        except:
            # Simple remix
            return [tweet.replace("is", f"with {new_angle} is") for tweet in original_thread]