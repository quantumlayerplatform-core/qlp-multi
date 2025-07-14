"""
HAP (Hate, Abuse, Profanity) Detection Service

Provides content moderation capabilities for the QuantumLayer Platform.
"""

import re
import hashlib
import asyncio
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
import unicodedata
from collections import defaultdict

import httpx
from pydantic import BaseModel, Field
import numpy as np
from transformers import pipeline
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text
import logging

from src.common.config import settings

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Content severity levels"""
    CLEAN = "clean"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Category(str, Enum):
    """HAP categories"""
    HATE_SPEECH = "hate_speech"
    ABUSE = "abuse"
    PROFANITY = "profanity"
    SEXUAL = "sexual"
    VIOLENCE = "violence"
    SELF_HARM = "self_harm"
    SPAM = "spam"


class CheckContext(str, Enum):
    """Context for content checking"""
    USER_REQUEST = "user_request"
    AGENT_OUTPUT = "agent_output"
    CAPSULE_CONTENT = "capsule_content"
    VALIDATION_INPUT = "validation_input"


class HAPCheckRequest(BaseModel):
    """Request model for HAP check"""
    content: str
    context: CheckContext = CheckContext.USER_REQUEST
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HAPCheckResult(BaseModel):
    """Result of HAP check"""
    result: str  # clean, flagged, blocked
    severity: Severity
    categories: List[Category] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: Optional[str] = None
    suggestions: Optional[str] = None
    processing_time_ms: float = 0.0


class HAPService:
    """Main HAP detection service"""
    
    def __init__(self):
        self.redis_client = None
        self.db_engine = None
        self.ml_pipeline = None
        self.rule_patterns = self._load_rule_patterns()
        self.profanity_list = self._load_profanity_list()
        self.initialized = False
        
    async def initialize(self):
        """Initialize service connections"""
        if self.initialized:
            return
            
        # Redis for caching
        self.redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Database for logging
        # Convert DATABASE_URL to async version
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        
        self.db_engine = create_async_engine(
            db_url,
            pool_size=5,
            max_overflow=10
        )
        
        # Initialize ML models (lazy loading)
        # self.ml_pipeline = await self._initialize_ml_models()
        
        self.initialized = True
        logger.info("HAP service initialized")
    
    def _load_rule_patterns(self) -> Dict[Category, List[re.Pattern]]:
        """Load regex patterns for rule-based detection"""
        patterns = {
            Category.HATE_SPEECH: [
                # Racial slurs (simplified for example)
                re.compile(r'\b(racist|discrimination|slur)\b', re.IGNORECASE),
            ],
            Category.ABUSE: [
                # Threats and harassment
                re.compile(r'\b(kill|hurt|harm|threat|die)\b', re.IGNORECASE),
                re.compile(r'\b(doxx|dox|address|personal\s+info)\b', re.IGNORECASE),
            ],
            Category.PROFANITY: [
                # Common profanity patterns (including censored versions)
                re.compile(r'\b(f[*@#u]ck|sh[*@#i]t|b[*@#i]tch)\b', re.IGNORECASE),
                re.compile(r'\b(stupid|idiot|dumb)\b', re.IGNORECASE),  # Mild insults
            ],
            Category.VIOLENCE: [
                re.compile(r'\b(violence|assault|attack|weapon)\b', re.IGNORECASE),
            ],
            Category.SELF_HARM: [
                re.compile(r'\b(suicide|self[\s-]?harm|cut\s+myself)\b', re.IGNORECASE),
            ]
        }
        return patterns
    
    def _load_profanity_list(self) -> Set[str]:
        """Load list of known profanity"""
        # In production, load from file or database
        return {
            "damn", "hell", "crap", "bastard",  # Mild
            "stupid", "idiot", "dumb", "moron",  # Insults
            # Add more as needed
        }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent checking"""
        # Remove unicode variations
        text = unicodedata.normalize('NFKD', text)
        
        # Convert leetspeak
        leet_map = {
            '@': 'a', '4': 'a', '3': 'e', '1': 'i', '0': 'o',
            '5': 's', '7': 't', '+': 't', '$': 's'
        }
        for leet, normal in leet_map.items():
            text = text.replace(leet, normal)
        
        # Remove repeated characters
        text = re.sub(r'(.)\1{2,}', r'\1\1', text)
        
        return text.lower().strip()
    
    async def check_content(
        self,
        request: HAPCheckRequest
    ) -> HAPCheckResult:
        """Main content checking method"""
        start_time = asyncio.get_event_loop().time()
        
        # Check cache first
        cache_key = self._get_cache_key(request.content)
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Normalize content
        normalized = self._normalize_text(request.content)
        
        # Rule-based check (fast)
        rule_result = await self._rule_based_check(normalized, request.content)
        
        # If critical severity, return immediately
        if rule_result.severity == Severity.CRITICAL:
            await self._log_violation(request, rule_result)
            await self._cache_result(cache_key, rule_result)
            return rule_result
        
        # ML-based check for ambiguous cases
        if rule_result.severity in [Severity.MEDIUM, Severity.HIGH]:
            ml_result = await self._ml_based_check(request.content)
            # Combine results
            rule_result = self._combine_results(rule_result, ml_result)
        
        # LLM-based check for complex cases (if enabled)
        if (request.context == CheckContext.USER_REQUEST and 
            rule_result.severity >= Severity.MEDIUM):
            llm_result = await self._llm_based_check(request.content)
            rule_result = self._combine_results(rule_result, llm_result)
        
        # Calculate processing time
        rule_result.processing_time_ms = (
            asyncio.get_event_loop().time() - start_time
        ) * 1000
        
        # Log if violation
        if rule_result.severity != Severity.CLEAN:
            await self._log_violation(request, rule_result)
        
        # Cache result
        await self._cache_result(cache_key, rule_result)
        
        return rule_result
    
    async def _rule_based_check(
        self,
        normalized: str,
        original: str
    ) -> HAPCheckResult:
        """Fast rule-based checking"""
        categories = []
        max_severity = Severity.CLEAN
        explanations = []
        
        # Check against patterns
        for category, patterns in self.rule_patterns.items():
            for pattern in patterns:
                if pattern.search(normalized) or pattern.search(original):
                    categories.append(category)
                    explanations.append(f"Detected {category.value}")
                    
                    # Set severity based on category
                    if category in [Category.HATE_SPEECH, Category.VIOLENCE]:
                        max_severity = max(max_severity, Severity.HIGH)
                    elif category in [Category.ABUSE, Category.SELF_HARM]:
                        max_severity = max(max_severity, Severity.HIGH)
                    else:
                        max_severity = max(max_severity, Severity.MEDIUM)
                    break
        
        # Check profanity list
        words = normalized.split()
        profane_words = [w for w in words if w in self.profanity_list]
        if profane_words:
            categories.append(Category.PROFANITY)
            max_severity = max(max_severity, Severity.LOW)
            explanations.append(f"Contains profanity: {', '.join(profane_words[:3])}")
        
        # Determine result
        if max_severity == Severity.CLEAN:
            result = "clean"
        elif max_severity in [Severity.LOW, Severity.MEDIUM]:
            result = "flagged"
        else:
            result = "blocked"
        
        return HAPCheckResult(
            result=result,
            severity=max_severity,
            categories=categories,
            confidence=0.9 if categories else 1.0,
            explanation="; ".join(explanations) if explanations else None,
            suggestions=self._get_suggestions(categories)
        )
    
    async def _ml_based_check(self, content: str) -> HAPCheckResult:
        """ML model-based checking (placeholder)"""
        # In production, use actual ML models
        # For now, return a simple result
        return HAPCheckResult(
            result="clean",
            severity=Severity.CLEAN,
            confidence=0.85
        )
    
    async def _llm_based_check(self, content: str) -> HAPCheckResult:
        """LLM-based checking for nuanced analysis"""
        # Use a safety-focused prompt
        prompt = f"""
        Analyze the following text for harmful content.
        Categories: hate speech, abuse, profanity, violence, self-harm
        
        Text: "{content}"
        
        Respond with:
        1. Severity: clean/low/medium/high/critical
        2. Categories found (if any)
        3. Brief explanation
        4. Suggestion for improvement
        """
        
        # In production, call actual LLM
        # For now, return placeholder
        return HAPCheckResult(
            result="clean",
            severity=Severity.CLEAN,
            confidence=0.95
        )
    
    def _combine_results(
        self,
        result1: HAPCheckResult,
        result2: HAPCheckResult
    ) -> HAPCheckResult:
        """Combine multiple check results"""
        # Take the higher severity
        if result1.severity.value > result2.severity.value:
            combined = result1
        else:
            combined = result2
        
        # Merge categories
        all_categories = list(set(result1.categories + result2.categories))
        
        # Average confidence
        avg_confidence = (result1.confidence + result2.confidence) / 2
        
        return HAPCheckResult(
            result=combined.result,
            severity=combined.severity,
            categories=all_categories,
            confidence=avg_confidence,
            explanation=combined.explanation,
            suggestions=combined.suggestions
        )
    
    def _get_suggestions(self, categories: List[Category]) -> Optional[str]:
        """Get improvement suggestions based on categories"""
        suggestions = []
        
        if Category.PROFANITY in categories:
            suggestions.append("Consider using more professional language")
        if Category.HATE_SPEECH in categories:
            suggestions.append("Ensure content is respectful to all groups")
        if Category.ABUSE in categories:
            suggestions.append("Remove threatening or harassing language")
        if Category.VIOLENCE in categories:
            suggestions.append("Avoid descriptions of violence")
        
        return "; ".join(suggestions) if suggestions else None
    
    def _get_cache_key(self, content: str) -> str:
        """Generate cache key for content"""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return f"hap:check:{content_hash}"
    
    async def _get_cached_result(self, cache_key: str) -> Optional[HAPCheckResult]:
        """Get cached check result"""
        if not self.redis_client:
            return None
            
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                import json
                data = json.loads(cached)
                return HAPCheckResult(**data)
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        
        return None
    
    async def _cache_result(self, cache_key: str, result: HAPCheckResult):
        """Cache check result"""
        if not self.redis_client:
            return
            
        try:
            import json
            ttl = 3600 * 24  # 24 hours for clean, 1 hour for violations
            if result.severity != Severity.CLEAN:
                ttl = 3600
                
            await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result.dict())
            )
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
    
    async def _log_violation(self, request: HAPCheckRequest, result: HAPCheckResult):
        """Log content violations to database"""
        if not self.db_engine:
            return
            
        try:
            async with AsyncSession(self.db_engine) as session:
                await session.execute(
                    text("""
                        INSERT INTO hap_violations (
                            id, tenant_id, user_id, context,
                            severity, categories, confidence,
                            content_hash, explanation,
                            created_at
                        ) VALUES (
                            gen_random_uuid(), :tenant_id, :user_id, :context,
                            :severity, :categories, :confidence,
                            :content_hash, :explanation,
                            NOW()
                        )
                    """),
                    {
                        "tenant_id": request.tenant_id or "default",
                        "user_id": request.user_id,
                        "context": request.context.value,
                        "severity": result.severity.value,
                        "categories": [c.value for c in result.categories],
                        "confidence": result.confidence,
                        "content_hash": hashlib.sha256(request.content.encode()).hexdigest(),
                        "explanation": result.explanation
                    }
                )
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to log violation: {e}")
    
    async def get_user_violations(
        self,
        user_id: str,
        tenant_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get user violation history"""
        if not self.db_engine:
            return {"error": "Database not available"}
            
        try:
            async with AsyncSession(self.db_engine) as session:
                result = await session.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total_violations,
                            COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical,
                            COUNT(CASE WHEN severity = 'high' THEN 1 END) as high,
                            COUNT(CASE WHEN severity = 'medium' THEN 1 END) as medium,
                            array_agg(DISTINCT categories) as all_categories
                        FROM hap_violations
                        WHERE user_id = :user_id
                          AND tenant_id = :tenant_id
                          AND created_at > NOW() - INTERVAL ':days days'
                    """),
                    {
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "days": days
                    }
                )
                
                row = result.fetchone()
                if row:
                    return {
                        "total_violations": row.total_violations,
                        "critical": row.critical,
                        "high": row.high,
                        "medium": row.medium,
                        "categories": row.all_categories or []
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get user violations: {e}")
            
        return {"total_violations": 0}


# Global service instance
hap_service = HAPService()


async def check_content(
    content: str,
    context: str = "user_request",
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None
) -> HAPCheckResult:
    """Convenience function for content checking"""
    if not hap_service.initialized:
        await hap_service.initialize()
        
    request = HAPCheckRequest(
        content=content,
        context=CheckContext(context),
        user_id=user_id,
        tenant_id=tenant_id
    )
    
    return await hap_service.check_content(request)