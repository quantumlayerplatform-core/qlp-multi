"""
Narrative Agent - Converts product features into compelling stories
"""

from typing import Dict, List, Any, Optional
import asyncio

from src.common.config import settings
from src.agents.marketing.models import ContentType, Channel, ToneStyle
from src.agents.azure_llm_client import llm_client, LLMProvider
import structlog

logger = structlog.get_logger()


class NarrativeAgent:
    """Transforms product features into engaging narratives"""
    
    def __init__(self):
        self.llm_client = llm_client
        
    async def generate_strategy(self, prompt: str) -> str:
        """Generate high-level marketing strategy"""
        try:
            messages = [{
                "role": "system",
                "content": "You are a world-class marketing strategist for tech startups."
            }, {
                "role": "user",
                "content": f"{prompt}\n\nCreate a comprehensive, actionable marketing strategy that will drive growth and engagement."
            }]
            
            response = await self.llm_client.chat_completion(
                messages=messages,
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.get("content", self._fallback_strategy())
        except Exception as e:
            logger.error("Strategy generation failed", error=str(e))
            return self._fallback_strategy()
    
    async def generate_content(
        self,
        content_type: ContentType,
        channel: Channel,
        product_info: str,
        value_prop: str,
        target_audience: str,
        tone_preferences: List[ToneStyle]
    ) -> Dict[str, Any]:
        """Generate narrative-driven content"""
        
        content_generators = {
            ContentType.LINKEDIN_POST: self._generate_linkedin_post,
            ContentType.EMAIL_CAMPAIGN: self._generate_email_campaign,
            ContentType.LANDING_PAGE: self._generate_landing_page,
            ContentType.VIDEO_SCRIPT: self._generate_video_script,
            ContentType.PRODUCT_LAUNCH: self._generate_product_launch
        }
        
        generator = content_generators.get(
            content_type, self._generate_generic_content
        )
        
        return await generator(
            product_info=product_info,
            value_prop=value_prop,
            target_audience=target_audience,
            tone_preferences=tone_preferences
        )
    
    async def _generate_linkedin_post(self, **kwargs) -> Dict[str, Any]:
        """Generate LinkedIn post with storytelling"""
        prompt = f"""Create a compelling LinkedIn post about:

Product: {kwargs['product_info']}
Value Proposition: {kwargs['value_prop']}
Target Audience: {kwargs['target_audience']}

Requirements:
1. Start with a personal story or industry insight
2. Connect to the product naturally
3. Include 3-5 key benefits
4. End with a thought-provoking question
5. Use professional but conversational tone
6. 150-300 words
7. Include 3-5 relevant hashtags

Format as:
TITLE: [Post title/hook]
CONTENT: [Main post content]
HASHTAGS: [Relevant hashtags]
CTA: [Call to action]"""

        try:
            response = await self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a LinkedIn thought leader in tech."},
                    {"role": "user", "content": prompt}
                ],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                temperature=0.8
            )
            
            content = response.get("content", "")
            return self._parse_structured_content(content)
            
        except Exception as e:
            logger.error("LinkedIn post generation failed", error=str(e))
            return self._fallback_linkedin_post(**kwargs)
    
    async def _generate_email_campaign(self, **kwargs) -> Dict[str, Any]:
        """Generate email campaign series"""
        prompt = f"""Create a 3-email drip campaign for:

Product: {kwargs['product_info']}
Value Proposition: {kwargs['value_prop']}
Target Audience: {kwargs['target_audience']}

Email 1: Welcome & Problem Introduction
Email 2: Solution Deep Dive  
Email 3: Success Stories & CTA

For each email provide:
SUBJECT: [Subject line]
PREVIEW: [Preview text]
CONTENT: [Email body]
CTA: [Call to action button text]

Make it engaging, benefit-focused, and personalized."""

        try:
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                max_tokens=2500
            )
            
            return self._parse_email_series(response.get("content", ""))
            
        except Exception as e:
            logger.error("Email campaign generation failed", error=str(e))
            return self._fallback_email_campaign(**kwargs)
    
    async def _generate_landing_page(self, **kwargs) -> Dict[str, Any]:
        """Generate landing page copy"""
        prompt = f"""Create landing page copy for:

Product: {kwargs['product_info']}
Value Proposition: {kwargs['value_prop']}
Target Audience: {kwargs['target_audience']}

Sections needed:
1. HERO: Headline, subheadline, and primary CTA
2. PROBLEM: Pain points we solve (3 points)
3. SOLUTION: How we solve it (3 features)
4. BENEFITS: What users gain (3 benefits)
5. SOCIAL PROOF: Testimonial or stats
6. CTA: Final call to action

Make it scannable, benefit-driven, and conversion-focused."""

        try:
            response = await self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a conversion copywriter."},
                    {"role": "user", "content": prompt}
                ],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                temperature=0.7
            )
            
            return self._parse_landing_page(response.get("content", ""))
            
        except Exception as e:
            logger.error("Landing page generation failed", error=str(e))
            return self._fallback_landing_page(**kwargs)
    
    async def _generate_video_script(self, **kwargs) -> Dict[str, Any]:
        """Generate video script for demos or ads"""
        prompt = f"""Create a 60-second video script for:

Product: {kwargs['product_info']}
Value Proposition: {kwargs['value_prop']}
Target Audience: {kwargs['target_audience']}

Structure:
- Hook (0-5 seconds)
- Problem (5-15 seconds)  
- Solution Demo (15-40 seconds)
- Benefits (40-50 seconds)
- CTA (50-60 seconds)

Include:
- Scene descriptions
- Voiceover text
- On-screen text
- Music/mood notes"""

        response = await self._call_llm(prompt, "video_script")
        return self._parse_video_script(response)
    
    async def _generate_product_launch(self, **kwargs) -> Dict[str, Any]:
        """Generate Product Hunt launch copy"""
        prompt = f"""Create Product Hunt launch copy for:

Product: {kwargs['product_info']}
Value Proposition: {kwargs['value_prop']}

Provide:
1. TAGLINE: One-liner (60 chars max)
2. DESCRIPTION: 2-3 sentences explaining what it does
3. FIRST COMMENT: Founder's story and vision (200 words)
4. GALLERY CAPTIONS: 3 captions for screenshots
5. TOPICS: 3-5 relevant topics/tags"""

        response = await self._call_llm(prompt, "product_launch")
        return self._parse_product_launch(response)
    
    async def _generate_generic_content(self, **kwargs) -> Dict[str, Any]:
        """Fallback generic content generator"""
        return {
            "content": f"Introducing {kwargs['value_prop']} - built for {kwargs['target_audience']}",
            "title": "Transform Your Workflow",
            "keywords": ["innovation", "efficiency", "automation"],
            "hashtags": ["#TechInnovation", "#FutureOfWork"],
            "cta": "Learn More"
        }
    
    async def _call_llm(self, prompt: str, content_type: str) -> str:
        """Generic LLM caller with fallback"""
        try:
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                max_tokens=1500,
                temperature=0.8
            )
            return response.get("content", "")
        except:
            return f"Generated {content_type} content placeholder"
    
    def _parse_structured_content(self, raw_content: str) -> Dict[str, Any]:
        """Parse LLM response into structured format"""
        lines = raw_content.strip().split('\n')
        result = {
            "content": "",
            "title": "",
            "hashtags": [],
            "cta": ""
        }
        
        current_section = None
        for line in lines:
            if line.startswith("TITLE:"):
                result["title"] = line.replace("TITLE:", "").strip()
            elif line.startswith("CONTENT:"):
                current_section = "content"
                result["content"] = line.replace("CONTENT:", "").strip()
            elif line.startswith("HASHTAGS:"):
                hashtags = line.replace("HASHTAGS:", "").strip()
                result["hashtags"] = [h.strip() for h in hashtags.split() if h.startswith("#")]
            elif line.startswith("CTA:"):
                result["cta"] = line.replace("CTA:", "").strip()
            elif current_section == "content" and line.strip():
                result["content"] += f"\n{line}"
        
        return result
    
    def _parse_email_series(self, raw_content: str) -> Dict[str, Any]:
        """Parse email series from LLM response"""
        # Implementation would parse the 3-email series
        # For now, return structured placeholder
        return {
            "content": raw_content,
            "title": "Email Campaign Series",
            "emails": [
                {
                    "subject": "Welcome! Here's how we can help",
                    "preview": "Discover a better way to work",
                    "content": "Email 1 content...",
                    "cta": "Get Started"
                }
            ]
        }
    
    def _parse_landing_page(self, raw_content: str) -> Dict[str, Any]:
        """Parse landing page sections"""
        return {
            "content": raw_content,
            "title": "Landing Page Copy",
            "sections": {
                "hero": "Build Software 100x Faster",
                "subhero": "AI agents that code like senior developers",
                "cta": "Start Free Trial"
            }
        }
    
    def _parse_video_script(self, raw_content: str) -> Dict[str, Any]:
        """Parse video script format"""
        return {
            "content": raw_content,
            "title": "60-Second Demo Video",
            "duration": 60,
            "scenes": []
        }
    
    def _parse_product_launch(self, raw_content: str) -> Dict[str, Any]:
        """Parse Product Hunt launch content"""
        return {
            "content": raw_content,
            "title": "Product Hunt Launch",
            "tagline": "AI agents that build production-ready software",
            "topics": ["developer-tools", "artificial-intelligence", "automation"]
        }
    
    def _fallback_strategy(self) -> str:
        """Fallback marketing strategy"""
        return """
## Marketing Strategy for QuantumLayer

### Core Messaging Pillars
1. **Speed**: Build in hours, not months
2. **Quality**: Production-ready code, not prototypes  
3. **Intelligence**: Self-improving AI agents

### Weekly Themes
- Week 1: Launch & Awareness
- Week 2: Technical Deep Dives
- Week 3: Success Stories
- Week 4: Community Building

### Channel Strategy
- LinkedIn: Thought leadership & B2B outreach
- Twitter: Real-time updates & developer engagement
- Medium: Technical blogs & case studies
- Email: Nurture sequence for leads

### Success Metrics
- 10K website visitors in first month
- 1K email signups
- 100 demo requests
- 50 pilot customers
"""
    
    def _fallback_linkedin_post(self, **kwargs) -> Dict[str, Any]:
        """Fallback LinkedIn post"""
        return {
            "title": "The Future of Software Development is Here",
            "content": f"""
Last week, I watched our AI agents build a complete SaaS platform in 3 hours.

What used to take a team of developers 3 months was done before lunch.

{kwargs['value_prop']}

This isn't just about speed. It's about democratizing software creation.

What would you build if you could go from idea to production in hours?
""",
            "hashtags": ["#AI", "#SoftwareDevelopment", "#Innovation", "#FutureOfWork"],
            "cta": "See it in action →"
        }
    
    def _fallback_email_campaign(self, **kwargs) -> Dict[str, Any]:
        """Fallback email campaign"""
        return {
            "content": "3-email drip campaign",
            "title": "Welcome Series",
            "emails": [
                {
                    "subject": f"Welcome! Here's how {kwargs['value_prop']}",
                    "content": "Welcome email content..."
                }
            ]
        }
    
    def _fallback_landing_page(self, **kwargs) -> Dict[str, Any]:
        """Fallback landing page"""
        return {
            "content": f"""
# {kwargs['value_prop']}

## Build Production Software in Hours, Not Months

Start your free trial today.
""",
            "title": "Landing Page",
            "cta": "Start Free Trial"
        }