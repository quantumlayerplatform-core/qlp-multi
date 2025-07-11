#!/usr/bin/env python3
"""
Capsule Critique API Endpoints
Provides HTTP endpoints for capsule quality assessment
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from src.common.database import get_db
from src.agents.capsule_critic_service import CapsuleCriticService
from src.common.auth import get_current_user

logger = structlog.get_logger()

router = APIRouter(prefix="/critique", tags=["critique"])


@router.post("/{capsule_id}")
async def critique_capsule(
    capsule_id: str,
    force: bool = Query(False, description="Force re-critique even if recent critique exists"),
    db_session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Run critique on a specific capsule
    
    Returns detailed quality assessment including:
    - Overall usefulness score (0-100)
    - Dimension scores (task alignment, correctness, etc.)
    - Key strengths and weaknesses
    - Improvement recommendations
    - Use/Don't use recommendation
    """
    
    try:
        service = CapsuleCriticService(db_session)
        
        # Check for existing critique if not forcing
        if not force:
            existing_critique = await service.get_critique(capsule_id)
            if existing_critique:
                logger.info(f"Returning existing critique for capsule {capsule_id}")
                return {
                    "status": "success",
                    "source": "cached",
                    "critique": existing_critique
                }
        
        # Run new critique
        logger.info(f"Running new critique for capsule {capsule_id}")
        critique = await service.critique_stored_capsule(capsule_id)
        
        if not critique:
            raise HTTPException(status_code=404, detail="Capsule not found")
        
        return {
            "status": "success",
            "source": "fresh",
            "critique": {
                "capsule_id": critique.capsule_id,
                "overall_usefulness": critique.overall_usefulness,
                "is_useful": critique.is_useful,
                "confidence": critique.confidence,
                "recommendation": critique.recommendation,
                "dimension_scores": [
                    {
                        "dimension": score.dimension.value,
                        "score": score.score,
                        "reasoning": score.reasoning,
                        "issues": score.issues,
                        "suggestions": score.suggestions
                    }
                    for score in critique.dimension_scores
                ],
                "key_strengths": critique.key_strengths,
                "key_weaknesses": critique.key_weaknesses,
                "improvement_priorities": critique.improvement_priorities,
                "overall_reasoning": critique.overall_reasoning,
                "metadata": critique.metadata
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error critiquing capsule {capsule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{capsule_id}")
async def get_capsule_critique(
    capsule_id: str,
    db_session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get existing critique for a capsule"""
    
    try:
        service = CapsuleCriticService(db_session)
        critique = await service.get_critique(capsule_id)
        
        if not critique:
            raise HTTPException(status_code=404, detail="No critique found for this capsule")
        
        return {
            "status": "success",
            "critique": critique
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving critique: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/recent")
async def critique_recent_capsules(
    hours: int = Query(24, description="Critique capsules from last N hours", ge=1, le=168),
    db_session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Run critiques on recent capsules
    
    Useful for batch quality assessment and continuous improvement
    """
    
    try:
        service = CapsuleCriticService(db_session)
        results = await service.critique_recent_capsules(hours)
        
        # Calculate summary statistics
        if results:
            avg_usefulness = sum(r["usefulness"] for r in results) / len(results)
            recommendation_breakdown = {}
            for rec in ["use_as_is", "use_with_modifications", "human_review", "regenerate"]:
                recommendation_breakdown[rec] = sum(1 for r in results if r["recommendation"] == rec)
        else:
            avg_usefulness = 0
            recommendation_breakdown = {}
        
        return {
            "status": "success",
            "summary": {
                "capsules_critiqued": len(results),
                "time_range_hours": hours,
                "average_usefulness": avg_usefulness,
                "recommendation_breakdown": recommendation_breakdown
            },
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error running batch critiques: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/overview")
async def get_critique_statistics(
    db_session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get overall critique statistics and trends"""
    
    try:
        service = CapsuleCriticService(db_session)
        stats = await service.get_critique_statistics()
        
        return {
            "status": "success",
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting critique statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/{capsule_id}")
async def submit_critique_feedback(
    capsule_id: str,
    feedback: Dict[str, Any],
    db_session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Submit user feedback on critique accuracy
    
    Expected feedback format:
    {
        "critique_was_accurate": true/false,
        "actual_usefulness": 0-100,
        "comments": "string",
        "used_in_production": true/false
    }
    """
    
    # This would store feedback for improving the critic agent
    # For now, just acknowledge receipt
    
    logger.info(
        f"Received critique feedback for capsule {capsule_id}",
        user_id=current_user["user_id"],
        feedback=feedback
    )
    
    return {
        "status": "success",
        "message": "Feedback recorded for continuous improvement"
    }


# Simple question endpoint for natural language critique queries
@router.post("/ask/{capsule_id}")
async def ask_about_capsule(
    capsule_id: str,
    question: str,
    db_session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Ask a specific question about capsule quality
    
    Examples:
    - "Was this capsule useful? Why or why not?"
    - "What are the main issues with this code?"
    - "Is this ready for production?"
    """
    
    try:
        service = CapsuleCriticService(db_session)
        
        # Get existing critique
        critique = await service.get_critique(capsule_id)
        
        if not critique:
            # Run new critique if needed
            critique_obj = await service.critique_stored_capsule(capsule_id)
            if not critique_obj:
                raise HTTPException(status_code=404, detail="Capsule not found")
            
            critique = {
                "overall_usefulness": critique_obj.overall_usefulness,
                "is_useful": critique_obj.is_useful,
                "recommendation": critique_obj.recommendation,
                "overall_reasoning": critique_obj.overall_reasoning,
                "key_strengths": critique_obj.key_strengths,
                "key_weaknesses": critique_obj.key_weaknesses
            }
        
        # Answer common questions
        question_lower = question.lower()
        
        if "useful" in question_lower:
            answer = f"{'Yes' if critique['is_useful'] else 'No'}, this capsule has a usefulness score of {critique['overall_usefulness']:.1f}/100. "
            answer += critique['overall_reasoning']
            
            if critique['key_weaknesses']:
                answer += f" Main issues: {', '.join(critique['key_weaknesses'][:2])}."
        
        elif "production" in question_lower or "ready" in question_lower:
            if critique['recommendation'] == "use_as_is":
                answer = "Yes, this capsule is production-ready and can be used as-is."
            elif critique['recommendation'] == "use_with_modifications":
                answer = f"Almost ready for production. Needs minor modifications: {', '.join(critique['key_weaknesses'][:2])}."
            else:
                answer = f"Not production-ready. Recommendation: {critique['recommendation']}. Major issues need to be addressed."
        
        elif "issues" in question_lower or "problems" in question_lower:
            if critique['key_weaknesses']:
                answer = f"Main issues found: {', '.join(critique['key_weaknesses'])}."
            else:
                answer = "No significant issues found. The capsule meets quality standards."
        
        else:
            # Generic answer
            answer = critique['overall_reasoning']
        
        return {
            "status": "success",
            "question": question,
            "answer": answer,
            "usefulness_score": critique['overall_usefulness'],
            "recommendation": critique['recommendation']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error answering question about capsule: {e}")
        raise HTTPException(status_code=500, detail=str(e))