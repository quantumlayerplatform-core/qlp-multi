"""
Agent roles and base classes for specialized agents
Separated to avoid circular imports
"""

from enum import Enum
from typing import Dict, Any
from src.agents.base_agents import Agent
from src.common.models import AgentTier


class AgentRole(str, Enum):
    """Specialized agent roles in ensemble"""
    ARCHITECT = "architect"
    IMPLEMENTER = "implementer"
    REVIEWER = "reviewer"
    OPTIMIZER = "optimizer"
    SECURITY_EXPERT = "security_expert"
    TEST_ENGINEER = "test_engineer"
    DOCUMENTOR = "documentor"


class SpecializedAgent(Agent):
    """Base class for specialized agents in ensemble"""
    
    def __init__(self, agent_id: str, role: AgentRole, tier: AgentTier):
        super().__init__(agent_id, tier)
        self.role = role
        self.specialization_prompts = self._get_specialization_prompts()
    
    def _get_specialization_prompts(self) -> Dict[str, str]:
        """Get role-specific prompts"""
        return {
            AgentRole.ARCHITECT: """You are a senior software architect. Focus on:
- System design and architecture patterns
- Scalability and performance considerations
- Clean code principles and SOLID
- Design patterns and best practices
- Error handling and resilience""",
            
            AgentRole.IMPLEMENTER: """You are an expert programmer. Focus on:
- Writing clean, efficient, production-ready code
- Following language-specific best practices
- Proper error handling and edge cases
- Code optimization and performance
- Clear naming and code organization""",
            
            AgentRole.REVIEWER: """You are a meticulous code reviewer. Focus on:
- Finding bugs and potential issues
- Code quality and maintainability
- Security vulnerabilities
- Performance bottlenecks
- Suggesting improvements""",
            
            AgentRole.OPTIMIZER: """You are a performance optimization expert. Focus on:
- Algorithm efficiency and complexity
- Memory usage optimization
- Caching strategies
- Database query optimization
- Concurrency and parallelization""",
            
            AgentRole.SECURITY_EXPERT: """You are a security specialist. Focus on:
- Identifying security vulnerabilities
- Input validation and sanitization
- Authentication and authorization
- Encryption and data protection
- Security best practices""",
            
            AgentRole.TEST_ENGINEER: """You are a test automation expert. Focus on:
- Comprehensive test coverage
- Unit, integration, and e2e tests
- Edge cases and error scenarios
- Test data generation
- Performance and load testing""",
            
            AgentRole.DOCUMENTOR: """You are a technical documentation expert. Focus on:
- Clear API documentation
- Usage examples and tutorials
- Architecture documentation
- Deployment guides
- Troubleshooting guides"""
        }