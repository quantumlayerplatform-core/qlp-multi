"""
Context Manager for MCP - Handles complex context across interactions
Implements Deutsch's principle of good explanations through context
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import json
import structlog

logger = structlog.get_logger()


@dataclass
class ContextFrame:
    """Represents a frame of context in the conversation"""
    id: str
    type: str  # 'task', 'code', 'feedback', 'principle', 'pattern'
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    references: Set[str] = field(default_factory=set)  # IDs of related frames


class ContextManager:
    """
    Manages context for MCP interactions
    Builds a graph of interconnected context frames
    """
    
    def __init__(self, max_frames: int = 100):
        self.frames: Dict[str, ContextFrame] = {}
        self.frame_order: List[str] = []  # Chronological order
        self.max_frames = max_frames
        self.type_index: Dict[str, Set[str]] = defaultdict(set)
        self.active_task_id: Optional[str] = None
        self.principles_applied: Set[str] = set()
        self.patterns_recognized: Set[str] = set()
    
    def add_frame(self, frame_type: str, content: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a new context frame"""
        frame_id = f"{frame_type}-{datetime.utcnow().timestamp()}"
        
        frame = ContextFrame(
            id=frame_id,
            type=frame_type,
            content=content,
            metadata=metadata or {}
        )
        
        # Add references to active task
        if self.active_task_id and frame_type != 'task':
            frame.references.add(self.active_task_id)
        
        # Store frame
        self.frames[frame_id] = frame
        self.frame_order.append(frame_id)
        self.type_index[frame_type].add(frame_id)
        
        # Maintain size limit
        if len(self.frames) > self.max_frames:
            self._evict_oldest_frames()
        
        logger.info(f"Added context frame: {frame_id}")
        return frame_id
    
    def add_task_context(self, description: str, requirements: Dict[str, Any]) -> str:
        """Add a new task to context"""
        task_id = self.add_frame("task", {
            "description": description,
            "requirements": requirements,
            "status": "active"
        })
        self.active_task_id = task_id
        return task_id
    
    def add_code_context(self, code: str, language: str = "python", metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add generated code to context"""
        return self.add_frame("code", {
            "code": code,
            "language": language
        }, metadata)
    
    def add_feedback_context(self, feedback: str, reference_id: Optional[str] = None) -> str:
        """Add feedback to context"""
        frame_id = self.add_frame("feedback", {
            "feedback": feedback,
            "addressed": False
        })
        
        if reference_id and reference_id in self.frames:
            self.frames[frame_id].references.add(reference_id)
            self.frames[reference_id].references.add(frame_id)
        
        return frame_id
    
    def add_principle_context(self, principle: str, application: str) -> str:
        """Add applied principle to context"""
        self.principles_applied.add(principle)
        return self.add_frame("principle", {
            "principle": principle,
            "application": application
        })
    
    def add_pattern_context(self, pattern: str, implementation: Dict[str, Any]) -> str:
        """Add recognized pattern to context"""
        self.patterns_recognized.add(pattern)
        return self.add_frame("pattern", {
            "pattern": pattern,
            "implementation": implementation
        })
    
    def get_frames_by_type(self, frame_type: str, limit: Optional[int] = None) -> List[ContextFrame]:
        """Get frames of a specific type"""
        frame_ids = list(self.type_index.get(frame_type, set()))
        frame_ids.sort(key=lambda fid: self.frames[fid].created_at, reverse=True)
        
        if limit:
            frame_ids = frame_ids[:limit]
        
        return [self.frames[fid] for fid in frame_ids]
    
    def get_related_frames(self, frame_id: str, depth: int = 1) -> Set[ContextFrame]:
        """Get frames related to a given frame up to specified depth"""
        if frame_id not in self.frames:
            return set()
        
        visited = set()
        to_visit = {frame_id}
        
        for _ in range(depth):
            next_visit = set()
            for fid in to_visit:
                if fid in visited:
                    continue
                visited.add(fid)
                
                frame = self.frames.get(fid)
                if frame:
                    next_visit.update(frame.references)
                    # Add frames that reference this one
                    for other_id, other_frame in self.frames.items():
                        if fid in other_frame.references:
                            next_visit.add(other_id)
            
            to_visit = next_visit
        
        return {self.frames[fid] for fid in visited if fid in self.frames}
    
    def get_active_context(self) -> Dict[str, Any]:
        """Get the currently active context"""
        context = {
            "task": None,
            "recent_code": [],
            "unaddressed_feedback": [],
            "principles_applied": list(self.principles_applied),
            "patterns_recognized": list(self.patterns_recognized)
        }
        
        # Get active task
        if self.active_task_id and self.active_task_id in self.frames:
            context["task"] = self.frames[self.active_task_id].content
        
        # Get recent code
        code_frames = self.get_frames_by_type("code", limit=3)
        context["recent_code"] = [frame.content for frame in code_frames]
        
        # Get unaddressed feedback
        feedback_frames = self.get_frames_by_type("feedback")
        context["unaddressed_feedback"] = [
            frame.content for frame in feedback_frames
            if not frame.content.get("addressed", False)
        ]
        
        return context
    
    def build_narrative_context(self) -> str:
        """Build a narrative description of the context"""
        active = self.get_active_context()
        
        narrative = []
        
        if active["task"]:
            narrative.append(f"Working on: {active['task']['description']}")
        
        if active["recent_code"]:
            narrative.append(f"Recently generated {len(active['recent_code'])} code solutions")
        
        if active["unaddressed_feedback"]:
            narrative.append(f"Have {len(active['unaddressed_feedback'])} feedback items to address")
        
        if active["principles_applied"]:
            narrative.append(f"Applied principles: {', '.join(active['principles_applied'][:3])}")
        
        if active["patterns_recognized"]:
            narrative.append(f"Recognized patterns: {', '.join(active['patterns_recognized'][:3])}")
        
        return ". ".join(narrative)
    
    def extract_learning_context(self) -> Dict[str, Any]:
        """Extract context suitable for learning/evolution"""
        learning_context = {
            "successful_patterns": [],
            "failed_attempts": [],
            "effective_principles": [],
            "improvement_opportunities": []
        }
        
        # Analyze code frames with feedback
        code_frames = self.get_frames_by_type("code")
        for code_frame in code_frames:
            related = self.get_related_frames(code_frame.id)
            
            feedback_frames = [f for f in related if f.type == "feedback"]
            if feedback_frames:
                # Has feedback - potential improvement
                learning_context["improvement_opportunities"].append({
                    "code": code_frame.content["code"][:200] + "...",
                    "feedback": feedback_frames[0].content["feedback"]
                })
            else:
                # No feedback - potentially successful
                principle_frames = [f for f in related if f.type == "principle"]
                if principle_frames:
                    learning_context["successful_patterns"].append({
                        "pattern": code_frame.metadata.get("pattern", "unknown"),
                        "principles": [p.content["principle"] for p in principle_frames]
                    })
        
        return learning_context
    
    def _evict_oldest_frames(self):
        """Remove oldest frames when limit is reached"""
        # Keep at least one frame of each type
        essential_frames = set()
        for frame_type, frame_ids in self.type_index.items():
            if frame_ids:
                # Keep the most recent of each type
                recent_id = max(frame_ids, key=lambda fid: self.frames[fid].created_at)
                essential_frames.add(recent_id)
        
        # Remove oldest non-essential frames
        while len(self.frames) > self.max_frames:
            if not self.frame_order:
                break
            
            oldest_id = self.frame_order[0]
            if oldest_id not in essential_frames:
                self._remove_frame(oldest_id)
            else:
                # Move to end to protect it
                self.frame_order.pop(0)
                self.frame_order.append(oldest_id)
    
    def _remove_frame(self, frame_id: str):
        """Remove a frame and clean up references"""
        if frame_id not in self.frames:
            return
        
        frame = self.frames[frame_id]
        
        # Remove from indices
        self.type_index[frame.type].discard(frame_id)
        self.frame_order.remove(frame_id)
        
        # Clean up references
        for ref_id in frame.references:
            if ref_id in self.frames:
                self.frames[ref_id].references.discard(frame_id)
        
        # Remove frame
        del self.frames[frame_id]
        
        logger.info(f"Evicted context frame: {frame_id}")
    
    def serialize(self) -> str:
        """Serialize context to JSON"""
        data = {
            "frames": {
                fid: {
                    "id": frame.id,
                    "type": frame.type,
                    "content": frame.content,
                    "metadata": frame.metadata,
                    "created_at": frame.created_at.isoformat(),
                    "references": list(frame.references)
                }
                for fid, frame in self.frames.items()
            },
            "frame_order": self.frame_order,
            "active_task_id": self.active_task_id,
            "principles_applied": list(self.principles_applied),
            "patterns_recognized": list(self.patterns_recognized)
        }
        return json.dumps(data, indent=2)
    
    @classmethod
    def deserialize(cls, data: str) -> 'ContextManager':
        """Deserialize context from JSON"""
        parsed = json.loads(data)
        
        manager = cls()
        
        # Restore frames
        for fid, frame_data in parsed["frames"].items():
            frame = ContextFrame(
                id=frame_data["id"],
                type=frame_data["type"],
                content=frame_data["content"],
                metadata=frame_data["metadata"],
                created_at=datetime.fromisoformat(frame_data["created_at"]),
                references=set(frame_data["references"])
            )
            manager.frames[fid] = frame
            manager.type_index[frame.type].add(fid)
        
        # Restore other state
        manager.frame_order = parsed["frame_order"]
        manager.active_task_id = parsed["active_task_id"]
        manager.principles_applied = set(parsed["principles_applied"])
        manager.patterns_recognized = set(parsed["patterns_recognized"])
        
        return manager


class MCPContextBridge:
    """
    Bridges MCP context with QLP's internal systems
    Enables deep integration of context across all components
    """
    
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
    
    def prepare_agent_context(self, agent_role: str) -> Dict[str, Any]:
        """Prepare context specifically for an agent role"""
        base_context = self.context_manager.get_active_context()
        
        # Role-specific context enrichment
        if agent_role == "architect":
            # Architects need patterns and principles
            base_context["focus"] = "design_patterns"
            base_context["relevant_patterns"] = self.context_manager.patterns_recognized
            
        elif agent_role == "implementer":
            # Implementers need recent code and requirements
            base_context["focus"] = "implementation"
            base_context["reference_implementations"] = base_context.get("recent_code", [])
            
        elif agent_role == "reviewer":
            # Reviewers need feedback and quality criteria
            base_context["focus"] = "quality"
            base_context["previous_feedback"] = base_context.get("unaddressed_feedback", [])
            
        elif agent_role == "test_engineer":
            # Test engineers need code and edge cases
            base_context["focus"] = "testing"
            base_context["code_to_test"] = base_context.get("recent_code", [])
            
        return base_context
    
    def update_from_result(self, result: Dict[str, Any], agent_role: str):
        """Update context based on agent result"""
        
        # Add generated code
        if "code" in result:
            self.context_manager.add_code_context(
                result["code"],
                metadata={"agent_role": agent_role, "confidence": result.get("confidence", 0)}
            )
        
        # Extract and add patterns
        if "patterns" in result:
            for pattern in result["patterns"]:
                self.context_manager.add_pattern_context(pattern, {"source": agent_role})
        
        # Extract and add principles
        if "principles_applied" in result:
            for principle in result["principles_applied"]:
                self.context_manager.add_principle_context(principle, agent_role)
    
    def get_evolution_context(self) -> Dict[str, Any]:
        """Get context for genome evolution"""
        return self.context_manager.extract_learning_context()
