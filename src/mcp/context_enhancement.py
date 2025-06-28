"""
MCP Context Enhancement for Ensemble Execution
Adds context awareness to code generation
"""

from typing import Dict, Any, Optional
from src.mcp import ContextManager, MCPContextBridge
import structlog

logger = structlog.get_logger()

# Get shared context manager from MCP API
def get_shared_instances():
    """Get shared context manager and bridge instances"""
    try:
        from src.mcp.mcp_api import get_shared_context_manager
        return get_shared_context_manager()
    except ImportError:
        # Fallback to creating new instances
        return ContextManager(max_frames=200), None

# Use shared instances
mcp_context_manager, mcp_context_bridge = get_shared_instances()
if mcp_context_bridge is None:
    mcp_context_bridge = MCPContextBridge(mcp_context_manager)


def enhance_request_with_mcp_context(request_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Enhance request with MCP context"""
    
    # Check for MCP context in request
    if 'mcp_context' in request_dict:
        mcp_context = request_dict['mcp_context']
        
        # Add task context
        if 'task_description' in mcp_context:
            mcp_context_manager.add_task_context(
                description=mcp_context['task_description'],
                requirements=mcp_context.get('requirements', {})
            )
        
        # Add previous code context
        if 'previous_code' in mcp_context:
            mcp_context_manager.add_code_context(
                code=mcp_context['previous_code'],
                metadata={'source': 'mcp_client'}
            )
        
        # Add feedback context
        if 'feedback' in mcp_context:
            mcp_context_manager.add_feedback_context(
                feedback=mcp_context['feedback']
            )
    
    # Add active context to requirements
    if 'requirements' not in request_dict:
        request_dict['requirements'] = {}
    
    active_context = mcp_context_manager.get_active_context()
    request_dict['requirements']['mcp_context'] = {
        'active_task': active_context.get('task'),
        'recent_code': active_context.get('recent_code', [])[:2],  # Last 2 code samples
        'unaddressed_feedback': active_context.get('unaddressed_feedback', []),
        'principles_applied': active_context.get('principles_applied', []),
        'patterns_recognized': active_context.get('patterns_recognized', []),
        'context_narrative': mcp_context_manager.build_narrative_context()
    }
    
    return request_dict


def update_mcp_from_result(result: Dict[str, Any], source: str = "ensemble"):
    """Update MCP context with generation results"""
    
    # Add generated code to context
    if 'code' in result:
        metadata = {
            'source': source,
            'confidence': result.get('confidence', 0),
            'quality_score': result.get('quality_score', 0)
        }
        mcp_context_manager.add_code_context(
            code=result['code'],
            metadata=metadata
        )
    
    # Extract and add patterns
    if 'patterns_detected' in result:
        for pattern in result['patterns_detected']:
            mcp_context_manager.add_pattern_context(
                pattern=pattern,
                implementation={'source': source}
            )
    
    # Extract and add principles
    if 'principles_applied' in result:
        for principle in result['principles_applied']:
            mcp_context_manager.add_principle_context(
                principle=principle,
                application=f"Applied in {source} generation"
            )
    
    # Add MCP metadata to result
    result['mcp_metadata'] = {
        'context_frames': len(mcp_context_manager.frames),
        'principles_applied': list(mcp_context_manager.principles_applied),
        'patterns_recognized': list(mcp_context_manager.patterns_recognized),
        'context_narrative': mcp_context_manager.build_narrative_context()
    }
    
    return result


def get_context_manager():
    """Get the global MCP context manager"""
    return mcp_context_manager


def get_context_bridge():
    """Get the global MCP context bridge"""
    return mcp_context_bridge
