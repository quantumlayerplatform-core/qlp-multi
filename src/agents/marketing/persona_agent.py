"""
Persona Agent - Crafts messaging variants by persona
"""

from typing import List, Dict, Any, Optional
import asyncio
from src.agents.azure_llm_client import llm_client, LLMProvider
from src.common.config import settings
from src.agents.marketing.models import ToneStyle
import structlog

logger = structlog.get_logger()


class PersonaAgent:
    """Creates persona-specific messaging variants"""
    
    def __init__(self):
        self.llm_client = llm_client
        
        # Define detailed personas
        self.personas = {
            "engineering_lead": {
                "title": "Engineering Lead/Tech Lead",
                "pain_points": [
                    "Team velocity and productivity",
                    "Technical debt management",
                    "Scaling development processes",
                    "Code quality and maintainability"
                ],
                "values": ["efficiency", "reliability", "innovation", "team growth"],
                "language_style": "technical but pragmatic",
                "decision_factors": ["ROI", "integration ease", "team adoption", "long-term maintainability"],
                "content_preferences": ["case studies", "technical specs", "benchmarks", "architecture diagrams"]
            },
            "product_manager": {
                "title": "Product Manager",
                "pain_points": [
                    "Feature delivery speed",
                    "Stakeholder alignment",
                    "Market competition",
                    "User satisfaction"
                ],
                "values": ["user experience", "market fit", "iteration speed", "data-driven decisions"],
                "language_style": "strategic and outcome-focused",
                "decision_factors": ["user impact", "time to market", "competitive advantage", "metrics"],
                "content_preferences": ["roadmaps", "user stories", "impact metrics", "competitor analysis"]
            },
            "cto": {
                "title": "CTO/VP Engineering",
                "pain_points": [
                    "Scaling engineering organization",
                    "Technology strategy alignment",
                    "Budget optimization",
                    "Innovation vs stability"
                ],
                "values": ["strategic advantage", "operational excellence", "talent retention", "innovation"],
                "language_style": "visionary yet practical",
                "decision_factors": ["strategic fit", "total cost", "risk mitigation", "competitive edge"],
                "content_preferences": ["industry trends", "strategic frameworks", "ROI analysis", "thought leadership"]
            },
            "startup_founder": {
                "title": "Startup Founder/CEO",
                "pain_points": [
                    "Limited resources",
                    "Speed to market",
                    "Finding product-market fit",
                    "Competing with incumbents"
                ],
                "values": ["growth", "disruption", "efficiency", "customer focus"],
                "language_style": "bold and inspirational",
                "decision_factors": ["growth potential", "cost efficiency", "speed", "differentiation"],
                "content_preferences": ["success stories", "growth hacks", "lean methodologies", "vision pieces"]
            },
            "enterprise_architect": {
                "title": "Enterprise Architect",
                "pain_points": [
                    "System integration complexity",
                    "Security and compliance",
                    "Legacy system migration",
                    "Standardization"
                ],
                "values": ["stability", "security", "scalability", "standards compliance"],
                "language_style": "formal and comprehensive",
                "decision_factors": ["security", "compliance", "integration capabilities", "vendor stability"],
                "content_preferences": ["white papers", "security audits", "compliance docs", "integration guides"]
            },
            "developer": {
                "title": "Senior Developer/Engineer",
                "pain_points": [
                    "Repetitive tasks",
                    "Context switching",
                    "Learning curve for new tools",
                    "Documentation quality"
                ],
                "values": ["code quality", "developer experience", "automation", "learning"],
                "language_style": "direct and technical",
                "decision_factors": ["ease of use", "documentation", "community support", "flexibility"],
                "content_preferences": ["code examples", "API docs", "tutorials", "community discussions"]
            },
            "investor": {
                "title": "VC/Angel Investor",
                "pain_points": [
                    "Identifying breakthrough technologies",
                    "Market sizing",
                    "Team evaluation",
                    "Exit potential"
                ],
                "values": ["market opportunity", "scalability", "defensibility", "team quality"],
                "language_style": "analytical and forward-looking",
                "decision_factors": ["market size", "growth rate", "moat", "team track record"],
                "content_preferences": ["market analysis", "growth metrics", "competitive positioning", "team background"]
            }
        }
    
    async def create_persona_variant(
        self,
        original_content: str,
        target_persona: str,
        content_type: str = "general"
    ) -> Dict[str, Any]:
        """Create content variant for specific persona"""
        
        persona = self.personas.get(target_persona)
        if not persona:
            logger.warning(f"Unknown persona: {target_persona}")
            return {"content": original_content, "persona": target_persona}
        
        # Generate persona-specific version
        variant = await self._generate_persona_content(
            original_content, persona, content_type
        )
        
        # Add persona-specific elements
        enhanced_variant = await self._enhance_for_persona(
            variant, persona, content_type
        )
        
        return {
            "persona": target_persona,
            "content": enhanced_variant,
            "key_adjustments": self._identify_adjustments(original_content, enhanced_variant),
            "messaging_focus": self._get_messaging_focus(persona),
            "recommended_channels": self._get_recommended_channels(persona),
            "follow_up_topics": self._suggest_follow_ups(persona, content_type)
        }
    
    async def _generate_persona_content(
        self,
        original: str,
        persona: Dict[str, Any],
        content_type: str
    ) -> str:
        """Generate persona-specific content"""
        
        prompt = f"""Rewrite this content for a {persona['title']}:

Original content:
{original}

Persona details:
- Pain points: {', '.join(persona['pain_points'])}
- Values: {', '.join(persona['values'])}
- Language style: {persona['language_style']}
- Decision factors: {', '.join(persona['decision_factors'])}

Requirements:
1. Address their specific pain points
2. Use language that resonates with their role
3. Focus on outcomes they care about
4. Include relevant metrics/proof points
5. Maintain core message but adjust framing

Content type: {content_type}"""

        try:
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                provider=LLMProvider.AZURE_OPENAI,
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.get("content", "")
            
        except Exception as e:
            logger.error("Persona content generation failed", error=str(e))
            return self._fallback_persona_content(original, persona)
    
    async def _enhance_for_persona(
        self,
        content: str,
        persona: Dict[str, Any],
        content_type: str
    ) -> str:
        """Add persona-specific enhancements"""
        
        enhancements = []
        
        # Add role-specific proof points
        if persona['title'] == "CTO/VP Engineering":
            enhancements.append(self._add_strategic_metrics())
        elif persona['title'] == "Engineering Lead/Tech Lead":
            enhancements.append(self._add_technical_validation())
        elif persona['title'] == "Product Manager":
            enhancements.append(self._add_user_impact_data())
        
        # Add relevant social proof
        social_proof = self._get_persona_social_proof(persona)
        if social_proof:
            enhancements.append(social_proof)
        
        # Combine content with enhancements
        if enhancements:
            enhancement_text = "\n\n".join(filter(None, enhancements))
            return f"{content}\n\n{enhancement_text}"
        
        return content
    
    def _add_strategic_metrics(self) -> str:
        """Add metrics for strategic decision makers"""
        return "📊 Enterprise clients report 70% reduction in development time and 50% cost savings within 6 months."
    
    def _add_technical_validation(self) -> str:
        """Add technical validation points"""
        return "🔧 Built on proven tech: Temporal workflows, Qdrant vectors, 5-stage validation pipeline. SOC2 compliant."
    
    def _add_user_impact_data(self) -> str:
        """Add user impact metrics"""
        return "📈 Teams ship 10x more features. NPS score: 72. Developer happiness: 94%."
    
    def _get_persona_social_proof(self, persona: Dict[str, Any]) -> Optional[str]:
        """Get relevant social proof for persona"""
        
        social_proof_map = {
            "CTO/VP Engineering": "Trusted by CTOs at 50+ high-growth startups",
            "Engineering Lead/Tech Lead": "Used by engineering teams at Stripe, Airbnb, and Uber",
            "Product Manager": "Helping PMs ship faster at leading product companies",
            "Startup Founder/CEO": "Backed by founders who've built $1B+ companies",
            "Enterprise Architect": "Meets enterprise security and compliance standards",
            "Senior Developer/Engineer": "20K+ developers building with us daily",
            "VC/Angel Investor": "Portfolio companies see 5x productivity gains"
        }
        
        return social_proof_map.get(persona['title'])
    
    def _identify_adjustments(self, original: str, variant: str) -> List[str]:
        """Identify key adjustments made for persona"""
        
        adjustments = []
        
        # Check for added metrics
        if any(char in variant for char in ["%", "$", "x"]) and not any(char in original for char in ["%", "$", "x"]):
            adjustments.append("Added quantitative proof points")
        
        # Check for role-specific language
        if "strategic" in variant.lower() and "strategic" not in original.lower():
            adjustments.append("Elevated to strategic level")
        
        # Check for outcome focus
        if "roi" in variant.lower() or "savings" in variant.lower():
            adjustments.append("Emphasized business outcomes")
        
        return adjustments
    
    def _get_messaging_focus(self, persona: Dict[str, Any]) -> Dict[str, str]:
        """Get key messaging focus for persona"""
        
        focus_map = {
            "Engineering Lead/Tech Lead": {
                "primary": "Developer productivity and code quality",
                "secondary": "Team scalability and best practices"
            },
            "Product Manager": {
                "primary": "Feature velocity and user satisfaction",
                "secondary": "Market competitiveness and metrics"
            },
            "CTO/VP Engineering": {
                "primary": "Strategic technology advantage",
                "secondary": "Organizational efficiency and innovation"
            },
            "Startup Founder/CEO": {
                "primary": "Rapid growth and market disruption",
                "secondary": "Resource efficiency and competitive edge"
            },
            "Enterprise Architect": {
                "primary": "Security, compliance, and integration",
                "secondary": "Scalability and standardization"
            },
            "Senior Developer/Engineer": {
                "primary": "Developer experience and automation",
                "secondary": "Learning curve and community"
            },
            "VC/Angel Investor": {
                "primary": "Market opportunity and scalability",
                "secondary": "Technology moat and team strength"
            }
        }
        
        return focus_map.get(
            persona['title'], 
            {"primary": "Value delivery", "secondary": "Efficiency gains"}
        )
    
    def _get_recommended_channels(self, persona: Dict[str, Any]) -> List[str]:
        """Get recommended channels for reaching persona"""
        
        channel_map = {
            "Engineering Lead/Tech Lead": ["Twitter", "Dev.to", "GitHub", "Slack communities"],
            "Product Manager": ["LinkedIn", "Medium", "ProductHunt", "Substack"],
            "CTO/VP Engineering": ["LinkedIn", "Executive forums", "Podcasts", "Industry events"],
            "Startup Founder/CEO": ["Twitter", "LinkedIn", "YC forums", "Founder communities"],
            "Enterprise Architect": ["LinkedIn", "White papers", "Webinars", "Industry publications"],
            "Senior Developer/Engineer": ["Twitter", "Reddit", "HackerNews", "Dev.to"],
            "VC/Angel Investor": ["Twitter", "LinkedIn", "Newsletter", "Demo days"]
        }
        
        return channel_map.get(persona['title'], ["LinkedIn", "Twitter"])
    
    def _suggest_follow_ups(
        self, persona: Dict[str, Any], content_type: str
    ) -> List[str]:
        """Suggest follow-up content for persona"""
        
        follow_ups = []
        
        if persona['title'] == "Engineering Lead/Tech Lead":
            follow_ups.extend([
                "Technical deep dive: Architecture walkthrough",
                "Team onboarding guide and best practices",
                "Performance benchmarks vs alternatives"
            ])
        elif persona['title'] == "Product Manager":
            follow_ups.extend([
                "Feature roadmap alignment workshop",
                "User story transformation examples",
                "Metrics dashboard walkthrough"
            ])
        elif persona['title'] == "CTO/VP Engineering":
            follow_ups.extend([
                "Executive briefing: Strategic advantages",
                "TCO analysis and ROI projection",
                "Digital transformation roadmap"
            ])
        
        return follow_ups[:3]
    
    def _fallback_persona_content(
        self, original: str, persona: Dict[str, Any]
    ) -> str:
        """Fallback content generation for persona"""
        
        # Simple persona adaptation
        intro_map = {
            "Engineering Lead/Tech Lead": "As an engineering leader, you know the challenge of scaling development velocity.",
            "Product Manager": "Every PM faces the same challenge: shipping features faster without sacrificing quality.",
            "CTO/VP Engineering": "Strategic technology decisions can make or break your competitive advantage.",
            "Startup Founder/CEO": "When you're moving fast and breaking things, every hour counts.",
        }
        
        intro = intro_map.get(persona['title'], "Here's how to transform your development process:")
        
        return f"{intro}\n\n{original}\n\nLet's discuss how this applies to your specific challenges."
    
    async def generate_persona_matrix(
        self, core_message: str
    ) -> Dict[str, Dict[str, Any]]:
        """Generate variants for all personas"""
        
        matrix = {}
        
        for persona_key in self.personas.keys():
            variant = await self.create_persona_variant(
                core_message, persona_key
            )
            matrix[persona_key] = variant
        
        # Add cross-persona insights
        matrix["insights"] = self._analyze_persona_differences(matrix)
        
        return matrix
    
    def _analyze_persona_differences(
        self, matrix: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze differences across persona variants"""
        
        insights = {
            "common_themes": [],
            "unique_angles": {},
            "channel_overlap": [],
            "messaging_convergence": []
        }
        
        # Find common themes
        all_content = [v.get("content", "") for v in matrix.values() if isinstance(v, dict)]
        common_words = ["productivity", "efficiency", "scale", "quality"]
        
        for word in common_words:
            if all(word in content.lower() for content in all_content):
                insights["common_themes"].append(word)
        
        # Identify unique angles
        for persona, data in matrix.items():
            if isinstance(data, dict) and "key_adjustments" in data:
                unique = set(data["key_adjustments"])
                if unique:
                    insights["unique_angles"][persona] = list(unique)
        
        return insights
    
    async def optimize_for_engagement(
        self, content: str, persona: str
    ) -> Dict[str, Any]:
        """Optimize content for maximum persona engagement"""
        
        persona_data = self.personas.get(persona)
        if not persona_data:
            return {"optimized_content": content}
        
        # Get engagement triggers for persona
        triggers = self._get_engagement_triggers(persona_data)
        
        # Apply optimization
        optimized = await self._apply_engagement_optimization(
            content, triggers, persona_data
        )
        
        return {
            "optimized_content": optimized,
            "engagement_triggers_used": triggers,
            "predicted_engagement_lift": self._predict_engagement_lift(triggers)
        }
    
    def _get_engagement_triggers(self, persona: Dict[str, Any]) -> List[str]:
        """Get engagement triggers for persona"""
        
        base_triggers = ["question", "challenge", "opportunity", "transformation"]
        
        # Add persona-specific triggers
        if "efficiency" in persona["values"]:
            base_triggers.append("10x improvement")
        if "innovation" in persona["values"]:
            base_triggers.append("breakthrough technology")
        if "growth" in persona["values"]:
            base_triggers.append("scale rapidly")
        
        return base_triggers
    
    async def _apply_engagement_optimization(
        self, content: str, triggers: List[str], persona: Dict[str, Any]
    ) -> str:
        """Apply engagement optimization techniques"""
        
        # For now, add a compelling question if none exists
        if "?" not in content:
            question_map = {
                "Engineering Lead/Tech Lead": "Ready to give your team superpowers?",
                "Product Manager": "What if you could ship 10x more features?",
                "CTO/VP Engineering": "Is your tech stack holding you back?",
                "Startup Founder/CEO": "What would you build with unlimited engineering capacity?"
            }
            
            question = question_map.get(persona['title'], "Ready to transform your development?")
            content += f"\n\n{question}"
        
        return content
    
    def _predict_engagement_lift(self, triggers: List[str]) -> float:
        """Predict engagement lift from optimization"""
        
        # Simple prediction based on trigger count
        base_lift = 0.1
        trigger_lift = len(triggers) * 0.05
        
        return min(base_lift + trigger_lift, 0.5)  # Max 50% lift