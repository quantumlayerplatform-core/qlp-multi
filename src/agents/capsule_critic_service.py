#!/usr/bin/env python3
"""
Capsule Critic Service
Service that runs CapsuleCriticAgent on stored capsules and saves critique results
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Float, JSON, DateTime, Boolean, ForeignKey, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
import structlog

from src.common.database import db_manager, Base
from src.common.models import QLCapsule, ExecutionRequest
from src.agents.capsule_critic_agent import CapsuleCriticAgent, CapsuleCritique
from src.orchestrator.capsule_storage import CapsuleStorageService

logger = structlog.get_logger()


class CapsuleCritiqueRecord(Base):
    """Database model for storing capsule critiques"""
    __tablename__ = "capsule_critiques"
    
    id = Column(Integer, primary_key=True)
    capsule_id = Column(String, ForeignKey("capsules.id"), nullable=False)
    request_id = Column(String, nullable=False)
    overall_usefulness = Column(Float, nullable=False)
    is_useful = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=False)
    recommendation = Column(String, nullable=False)
    
    # JSON fields for complex data
    dimension_scores = Column(JSON, nullable=False)
    key_strengths = Column(JSON, nullable=False)
    key_weaknesses = Column(JSON, nullable=False)
    improvement_priorities = Column(JSON, nullable=False)
    
    overall_reasoning = Column(String, nullable=False)
    metadata = Column(JSON, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CapsuleCriticService:
    """Service for running critiques on stored capsules"""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db_session = db_session or db_manager.get_session()
        self.storage_service = CapsuleStorageService(self.db_session)
        self.critic_agent = CapsuleCriticAgent()
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=db_manager.engine)
    
    async def critique_stored_capsule(self, capsule_id: str) -> Optional[CapsuleCritique]:
        """Critique a capsule from the database"""
        
        try:
            # Retrieve capsule and request from database
            capsule_data = self.storage_service.get_capsule(capsule_id)
            if not capsule_data:
                logger.error(f"Capsule {capsule_id} not found in database")
                return None
            
            # Reconstruct QLCapsule object
            capsule = QLCapsule(**capsule_data["capsule"])
            
            # Reconstruct ExecutionRequest
            request = ExecutionRequest(**capsule_data["request"])
            
            logger.info(f"Starting critique for capsule {capsule_id}")
            
            # Run critique
            critique = await self.critic_agent.critique_capsule(capsule, request)
            
            # Store critique in database
            await self._store_critique(critique, request.id)
            
            logger.info(
                f"Critique completed for capsule {capsule_id}",
                usefulness=critique.overall_usefulness,
                recommendation=critique.recommendation
            )
            
            return critique
            
        except Exception as e:
            logger.error(f"Error critiquing capsule {capsule_id}: {e}")
            return None
    
    async def critique_recent_capsules(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Critique all capsules created in the last N hours"""
        
        try:
            # Get recent capsules
            recent_capsules = self.storage_service.list_capsules(
                limit=100,  # Process up to 100 recent capsules
                offset=0
            )
            
            results = []
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            for capsule_summary in recent_capsules:
                # Check if created recently
                created_at = datetime.fromisoformat(capsule_summary["created_at"].replace("Z", "+00:00"))
                if created_at < cutoff_time:
                    continue
                
                # Check if already critiqued
                if await self._has_recent_critique(capsule_summary["id"]):
                    logger.info(f"Skipping {capsule_summary['id']} - already critiqued")
                    continue
                
                # Run critique
                critique = await self.critique_stored_capsule(capsule_summary["id"])
                if critique:
                    results.append({
                        "capsule_id": capsule_summary["id"],
                        "usefulness": critique.overall_usefulness,
                        "recommendation": critique.recommendation
                    })
            
            logger.info(f"Critiqued {len(results)} capsules from the last {hours} hours")
            return results
            
        except Exception as e:
            logger.error(f"Error critiquing recent capsules: {e}")
            return []
    
    async def get_critique(self, capsule_id: str) -> Optional[Dict[str, Any]]:
        """Get existing critique for a capsule"""
        
        try:
            critique_record = self.db_session.query(CapsuleCritiqueRecord).filter_by(
                capsule_id=capsule_id
            ).order_by(CapsuleCritiqueRecord.created_at.desc()).first()
            
            if not critique_record:
                return None
            
            return {
                "capsule_id": critique_record.capsule_id,
                "overall_usefulness": critique_record.overall_usefulness,
                "is_useful": critique_record.is_useful,
                "confidence": critique_record.confidence,
                "recommendation": critique_record.recommendation,
                "dimension_scores": critique_record.dimension_scores,
                "key_strengths": critique_record.key_strengths,
                "key_weaknesses": critique_record.key_weaknesses,
                "improvement_priorities": critique_record.improvement_priorities,
                "overall_reasoning": critique_record.overall_reasoning,
                "created_at": critique_record.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error retrieving critique: {e}")
            return None
    
    async def get_critique_statistics(self) -> Dict[str, Any]:
        """Get overall critique statistics"""
        
        try:
            total_critiques = self.db_session.query(CapsuleCritiqueRecord).count()
            
            useful_count = self.db_session.query(CapsuleCritiqueRecord).filter_by(
                is_useful=True
            ).count()
            
            # Get recommendation breakdown
            recommendations = {}
            for rec in ["use_as_is", "use_with_modifications", "human_review", "regenerate"]:
                count = self.db_session.query(CapsuleCritiqueRecord).filter_by(
                    recommendation=rec
                ).count()
                recommendations[rec] = count
            
            # Calculate average usefulness
            avg_usefulness = self.db_session.query(
                CapsuleCritiqueRecord.overall_usefulness
            ).scalar() or 0
            
            return {
                "total_critiques": total_critiques,
                "useful_capsules": useful_count,
                "usefulness_rate": (useful_count / total_critiques * 100) if total_critiques > 0 else 0,
                "average_usefulness": avg_usefulness,
                "recommendations": recommendations,
                "last_critique": self._get_last_critique_time()
            }
            
        except Exception as e:
            logger.error(f"Error getting critique statistics: {e}")
            return {}
    
    async def _store_critique(self, critique: CapsuleCritique, request_id: str):
        """Store critique in database"""
        
        try:
            # Convert dimension scores to JSON-serializable format
            dimension_scores_json = [
                {
                    "dimension": score.dimension.value,
                    "score": score.score,
                    "reasoning": score.reasoning,
                    "issues": score.issues,
                    "suggestions": score.suggestions
                }
                for score in critique.dimension_scores
            ]
            
            critique_record = CapsuleCritiqueRecord(
                capsule_id=critique.capsule_id,
                request_id=request_id,
                overall_usefulness=critique.overall_usefulness,
                is_useful=critique.is_useful,
                confidence=critique.confidence,
                recommendation=critique.recommendation,
                dimension_scores=dimension_scores_json,
                key_strengths=critique.key_strengths,
                key_weaknesses=critique.key_weaknesses,
                improvement_priorities=critique.improvement_priorities,
                overall_reasoning=critique.overall_reasoning,
                metadata=critique.metadata
            )
            
            self.db_session.add(critique_record)
            self.db_session.commit()
            
            logger.info(f"Stored critique for capsule {critique.capsule_id}")
            
        except Exception as e:
            logger.error(f"Error storing critique: {e}")
            self.db_session.rollback()
            raise
    
    async def _has_recent_critique(self, capsule_id: str, hours: int = 24) -> bool:
        """Check if capsule has been critiqued recently"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_critique = self.db_session.query(CapsuleCritiqueRecord).filter(
            CapsuleCritiqueRecord.capsule_id == capsule_id,
            CapsuleCritiqueRecord.created_at >= cutoff_time
        ).first()
        
        return recent_critique is not None
    
    def _get_last_critique_time(self) -> Optional[str]:
        """Get timestamp of last critique"""
        
        last_critique = self.db_session.query(CapsuleCritiqueRecord).order_by(
            CapsuleCritiqueRecord.created_at.desc()
        ).first()
        
        if last_critique:
            return last_critique.created_at.isoformat()
        return None


# CLI for running critiques
async def main():
    """Run capsule critiques from command line"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Capsule Critic Service")
    parser.add_argument("--capsule-id", help="Critique specific capsule")
    parser.add_argument("--recent", type=int, help="Critique capsules from last N hours")
    parser.add_argument("--stats", action="store_true", help="Show critique statistics")
    
    args = parser.parse_args()
    
    service = CapsuleCriticService()
    
    if args.capsule_id:
        # Critique specific capsule
        print(f"🔍 Critiquing capsule {args.capsule_id}...")
        critique = await service.critique_stored_capsule(args.capsule_id)
        
        if critique:
            print(f"\n📊 CRITIQUE RESULTS")
            print(f"{'='*50}")
            print(f"Overall Usefulness: {critique.overall_usefulness:.1f}/100")
            print(f"Is Useful: {'✅ Yes' if critique.is_useful else '❌ No'}")
            print(f"Recommendation: {critique.recommendation.upper()}")
            print(f"\n💪 Strengths: {', '.join(critique.key_strengths[:2])}")
            print(f"⚠️  Weaknesses: {', '.join(critique.key_weaknesses[:2])}")
            print(f"\n📝 {critique.overall_reasoning}")
        else:
            print("❌ Failed to critique capsule")
    
    elif args.recent:
        # Critique recent capsules
        print(f"🔍 Critiquing capsules from last {args.recent} hours...")
        results = await service.critique_recent_capsules(args.recent)
        
        print(f"\n📊 CRITIQUE SUMMARY")
        print(f"{'='*50}")
        print(f"Critiqued {len(results)} capsules")
        
        if results:
            avg_usefulness = sum(r["usefulness"] for r in results) / len(results)
            print(f"Average Usefulness: {avg_usefulness:.1f}/100")
            
            print("\nRecommendations:")
            for rec in ["use_as_is", "use_with_modifications", "human_review", "regenerate"]:
                count = sum(1 for r in results if r["recommendation"] == rec)
                print(f"  - {rec}: {count}")
    
    elif args.stats:
        # Show statistics
        stats = await service.get_critique_statistics()
        
        print(f"\n📊 CRITIQUE STATISTICS")
        print(f"{'='*50}")
        print(f"Total Critiques: {stats.get('total_critiques', 0)}")
        print(f"Useful Capsules: {stats.get('useful_capsules', 0)} ({stats.get('usefulness_rate', 0):.1f}%)")
        print(f"Average Usefulness: {stats.get('average_usefulness', 0):.1f}/100")
        
        print("\nRecommendation Breakdown:")
        for rec, count in stats.get('recommendations', {}).items():
            print(f"  - {rec}: {count}")
        
        if stats.get('last_critique'):
            print(f"\nLast Critique: {stats['last_critique']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())