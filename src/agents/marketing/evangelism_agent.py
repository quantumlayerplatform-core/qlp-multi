"""
Evangelism Agent - Creates technical content for developer audiences
"""

from typing import Dict, List, Any
import asyncio
from src.agents.azure_llm_client import llm_client, LLMProvider
from src.common.config import settings
from src.agents.marketing.models import ContentType, Channel
import structlog

logger = structlog.get_logger()


class EvangelismAgent:
    """Creates technical evangelism content for developers and CTOs"""
    
    def __init__(self):
        self.llm_client = llm_client
        
    async def generate_content(
        self,
        content_type: ContentType,
        channel: Channel,
        product_info: str,
        features: List[str],
        target_audience: str,
        strategy: str
    ) -> Dict[str, Any]:
        """Generate technical evangelism content"""
        
        if content_type == ContentType.TWEET_THREAD:
            return await self._generate_tweet_thread(
                product_info, features, target_audience
            )
        elif content_type == ContentType.BLOG_POST:
            return await self._generate_technical_blog(
                product_info, features, target_audience, strategy
            )
        elif content_type == ContentType.REDDIT_POST:
            return await self._generate_reddit_post(
                product_info, features, channel
            )
        else:
            return await self._generate_generic_technical_content(
                content_type, product_info, features
            )
    
    async def _generate_tweet_thread(
        self, product_info: str, features: List[str], target_audience: str
    ) -> Dict[str, Any]:
        """Generate technical tweet thread"""
        prompt = f"""Create a technical tweet thread about:

Product: {product_info}
Key Features:
{chr(10).join(f'- {feature}' for feature in features)}
Audience: {target_audience}

Requirements:
1. Start with a bold technical claim or surprising fact
2. 5-8 tweets total
3. Include code snippets or architecture diagrams descriptions
4. Back up claims with technical details
5. End with a call to action
6. Use relevant hashtags

Format each tweet as:
Tweet 1: [content]
Tweet 2: [content]
etc.

Make it technically compelling but accessible."""

        try:
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                max_tokens=1500,
                temperature=0.7
            )
            
            return self._parse_tweet_thread(response.get("content", ""))
            
        except Exception as e:
            logger.error("Tweet thread generation failed", error=str(e))
            return self._fallback_tweet_thread(product_info, features)
    
    async def _generate_technical_blog(
        self, product_info: str, features: List[str], 
        target_audience: str, strategy: str
    ) -> Dict[str, Any]:
        """Generate in-depth technical blog post"""
        prompt = f"""Write a technical blog post about:

Product: {product_info}
Features: {', '.join(features)}
Audience: {target_audience}
Strategy Context: {strategy}

Structure:
1. Hook: Technical problem statement
2. Current Solutions: Why they fall short
3. Our Approach: Technical architecture and innovations
4. Deep Dive: Pick one feature for detailed explanation
5. Performance Metrics: Real numbers and benchmarks
6. Implementation Example: Code snippets
7. Future Roadmap: What's next
8. Conclusion: Call to action

Make it 1000-1500 words, technically accurate, with code examples.
Include SEO keywords naturally."""

        try:
            response = await self.llm_client.chat_completion(
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a technical evangelist and architect who writes for developers."
                    },
                    {"role": "user", "content": prompt}
                ],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                temperature=0.7,
                max_tokens=2500
            )
            
            return self._parse_blog_post(response.get("content", ""))
            
        except Exception as e:
            logger.error("Blog post generation failed", error=str(e))
            return self._fallback_blog_post(product_info, features)
    
    async def _generate_reddit_post(
        self, product_info: str, features: List[str], channel: Channel
    ) -> Dict[str, Any]:
        """Generate Reddit post for technical communities"""
        subreddit_map = {
            "r/MachineLearning": "ML/AI focus",
            "r/programming": "General programming",
            "r/devops": "DevOps and automation",
            "r/startups": "Startup journey"
        }
        
        prompt = f"""Create a Reddit post for r/programming about:

Product: {product_info}
Features: {', '.join(features[:3])}

Requirements:
1. Authentic, not salesy
2. Start with technical insight or problem
3. Share architectural decisions
4. Include lessons learned
5. Ask for feedback
6. No direct promotion until comments

Title: [Compelling technical title]
Post: [Main content]

Make it feel like a genuine developer sharing their work."""

        response = await self._call_llm(prompt)
        return self._parse_reddit_post(response)
    
    async def _generate_generic_technical_content(
        self, content_type: ContentType, product_info: str, features: List[str]
    ) -> Dict[str, Any]:
        """Generate generic technical content"""
        prompt = f"""Create technical content about:

Type: {content_type.value}
Product: {product_info}
Features: {', '.join(features[:3])}

Make it technical, specific, and valuable to developers."""

        response = await self._call_llm(prompt)
        return {
            "content": response,
            "title": f"Technical Deep Dive: {features[0]}",
            "keywords": ["AI", "automation", "development"],
            "hashtags": ["#TechInnovation", "#DeveloperTools"]
        }
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with fallback"""
        try:
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                max_tokens=1500
            )
            return response.get("content", "")
        except:
            return "Technical content generation failed"
    
    def _parse_tweet_thread(self, raw_content: str) -> Dict[str, Any]:
        """Parse tweet thread from LLM response"""
        tweets = []
        lines = raw_content.strip().split('\n')
        
        current_tweet = ""
        for line in lines:
            if line.startswith("Tweet ") and current_tweet:
                tweets.append(current_tweet.strip())
                current_tweet = line.split(":", 1)[1].strip() if ":" in line else ""
            elif line.strip():
                current_tweet += f" {line.strip()}"
        
        if current_tweet:
            tweets.append(current_tweet.strip())
        
        # Ensure we have at least 5 tweets
        while len(tweets) < 5:
            tweets.append(f"🧵 {len(tweets)+1}/n More insights on our technical approach...")
        
        # Add thread markers
        formatted_tweets = []
        for i, tweet in enumerate(tweets):
            if i == 0:
                formatted_tweets.append(f"{tweet}\n\n🧵👇")
            else:
                formatted_tweets.append(f"{i+1}/\n\n{tweet}")
        
        return {
            "content": "\n\n---\n\n".join(formatted_tweets),
            "title": "Technical Deep Dive Thread",
            "tweets": formatted_tweets,
            "hashtags": ["#AIAgents", "#DevTools", "#BuildInPublic"],
            "keywords": ["AI", "automation", "developer productivity"]
        }
    
    def _parse_blog_post(self, raw_content: str) -> Dict[str, Any]:
        """Parse blog post from LLM response"""
        # Extract title if present
        lines = raw_content.strip().split('\n')
        title = "How We Built AI Agents That Code Like Senior Developers"
        
        if lines and lines[0].startswith("#"):
            title = lines[0].replace("#", "").strip()
            content = '\n'.join(lines[1:])
        else:
            content = raw_content
        
        # Extract keywords from content
        keywords = []
        keyword_indicators = ["AI", "agent", "automation", "code", "developer", "production"]
        for keyword in keyword_indicators:
            if keyword.lower() in content.lower():
                keywords.append(keyword)
        
        return {
            "content": content,
            "title": title,
            "keywords": keywords,
            "hashtags": ["#TechBlog", "#AI", "#SoftwareEngineering"],
            "cta": "Try it yourself at quantumlayer.dev"
        }
    
    def _parse_reddit_post(self, raw_content: str) -> Dict[str, Any]:
        """Parse Reddit post format"""
        lines = raw_content.strip().split('\n')
        title = ""
        post_content = ""
        
        for line in lines:
            if line.startswith("Title:"):
                title = line.replace("Title:", "").strip()
            elif line.startswith("Post:"):
                post_content = line.replace("Post:", "").strip()
            elif post_content and line.strip():
                post_content += f"\n\n{line.strip()}"
        
        return {
            "content": post_content or raw_content,
            "title": title or "Built an AI system that generates production code - thoughts?",
            "keywords": ["opensource", "AI", "automation"],
            "subreddit": "r/programming"
        }
    
    def _fallback_tweet_thread(self, product_info: str, features: List[str]) -> Dict[str, Any]:
        """Fallback tweet thread"""
        tweets = [
            f"🚀 We just cracked the code on AI-powered software development.\n\nOur agents don't just generate snippets - they build entire production systems.\n\n🧵👇",
            f"2/\n\nThe problem: Current AI tools generate toy code that needs massive rewrites.\n\nOur solution: Multi-tier agents that think like senior developers.",
            f"3/\n\nKey innovation: Pattern Selection Engine\n\n• 60-70% compute reduction\n• Picks optimal reasoning strategy\n• Learns from every execution",
            f"4/\n\nReal example: Asked for a 'SaaS billing system'\n\nGot:\n✅ Stripe integration\n✅ Usage tracking\n✅ Invoice generation\n✅ Admin dashboard\n✅ Tests + Docker\n\nIn 3 hours.",
            f"5/\n\nThe magic: Temporal workflows + Qdrant vector memory\n\nEvery successful pattern is learned and reused. The system literally gets smarter with each request.",
            f"6/\n\nWe're not replacing developers.\n\nWe're giving them superpowers.\n\nImagine shipping in hours what used to take months.\n\n🔗 See it in action: quantumlayer.dev"
        ]
        
        return {
            "content": "\n\n---\n\n".join(tweets),
            "title": "AI Agents That Actually Ship Production Code",
            "tweets": tweets,
            "hashtags": ["#AI", "#DevTools", "#BuildInPublic", "#StartupLife"],
            "keywords": ["AI agents", "code generation", "developer tools"]
        }
    
    def _fallback_blog_post(self, product_info: str, features: List[str]) -> Dict[str, Any]:
        """Fallback blog post"""
        return {
            "title": "Building AI Agents That Think Like Senior Developers",
            "content": f"""
# Building AI Agents That Think Like Senior Developers

## The Problem with Current AI Code Generation

Every developer has tried ChatGPT or Copilot. They're great for snippets, but what about building entire systems?

Current limitations:
- Generated code lacks production considerations
- No understanding of architectural patterns
- Missing tests, deployment, monitoring
- Each request starts from scratch

## Our Approach: Multi-Tier Agent Architecture

We built QuantumLayer with a radical idea: What if AI agents could think like senior developers?

### The Architecture

```
Request → Orchestrator → Agent Selection → Execution → Validation → Delivery
              ↓
          Pattern Memory (Qdrant)
```

### Key Innovations

1. **Pattern Selection Engine**: Reduces compute by 60-70%
2. **Multi-Tier Agents**: T0 for simple tasks, T3 for complex systems
3. **Vector Memory**: Learn from every execution
4. **5-Stage Validation**: Ensure production quality

## Real-World Example

Input: "Build a subscription billing system"

Output:
- Complete Stripe integration
- User management with auth
- Admin dashboard
- Webhook handlers
- Test suite with 80% coverage
- Docker deployment
- API documentation

Time: 3 hours (vs 3 months traditional)

## What's Next

We're just getting started. Imagine:
- AI agents that refactor legacy codebases
- Automatic scaling based on usage patterns
- Self-healing systems that fix their own bugs

The future of software development isn't about replacing developers. It's about amplifying their capabilities.

**Ready to build faster?** [Start your free trial](https://quantumlayer.dev)
""",
            "keywords": ["AI", "software development", "automation", "developer tools"],
            "hashtags": ["#AI", "#TechBlog", "#Innovation"],
            "cta": "Start building with AI agents"
        }