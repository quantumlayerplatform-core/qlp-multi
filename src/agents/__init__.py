"""
Quantum Layer Platform - Agent Module

This module contains:
- Base agent implementations (T0, T1, T2, T3)
- Specialized production agents (Architect, Implementer, Reviewer, etc.)
- Ensemble orchestration system
- Agent factory for creating and managing agents
"""

# Export base agents
from .base_agents import Agent, T0Agent, T1Agent, T2Agent, T3Agent

# Export ensemble components if available
try:
    from .ensemble import (
        ProductionCodeGenerator,
        EnsembleOrchestrator,
        EnsembleConfiguration,
        VotingStrategy,
        AgentRole
    )
    from .specialized import (
        ProductionArchitectAgent,
        ProductionImplementerAgent,
        ProductionReviewerAgent,
        ProductionSecurityAgent,
        ProductionTestAgent,
        ProductionOptimizerAgent,
        ProductionDocumentorAgent,
        create_specialized_agent
    )
    ENSEMBLE_AVAILABLE = True
except ImportError:
    ENSEMBLE_AVAILABLE = False

__all__ = [
    # Base agents
    "Agent",
    "T0Agent", 
    "T1Agent",
    "T2Agent",
    "T3Agent",
    # Ensemble components (if available)
    "ProductionCodeGenerator",
    "EnsembleOrchestrator",
    "EnsembleConfiguration",
    "VotingStrategy",
    "AgentRole",
    # Specialized agents (if available)
    "ProductionArchitectAgent",
    "ProductionImplementerAgent",
    "ProductionReviewerAgent",
    "ProductionSecurityAgent",
    "ProductionTestAgent",
    "ProductionOptimizerAgent",
    "ProductionDocumentorAgent",
    "create_specialized_agent",
    # Flag
    "ENSEMBLE_AVAILABLE"
]
