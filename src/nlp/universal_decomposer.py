"""
Universal NLP Decomposer - Core foundation for universal agent system
Creates emergent understanding without domain constraints or templates
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import structlog
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from src.common.config import settings
from src.common.models import Task, TaskStatus, ExecutionRequest
from src.memory.client import VectorMemoryClient

logger = structlog.get_logger()


@dataclass
class Pattern:
    """Universal pattern learned from successful decompositions"""
    complexity_indicators: List[str] = field(default_factory=list)
    dependency_patterns: List[Dict[str, Any]] = field(default_factory=list)
    execution_patterns: List[Dict[str, Any]] = field(default_factory=list)
    success_indicators: List[str] = field(default_factory=list)
    context_signals: List[str] = field(default_factory=list)
    abstraction_level: str = "medium"
    pattern_confidence: float = 0.0
    usage_count: int = 0
    success_rate: float = 0.0


@dataclass
class Intent:
    """Emergent intent understanding without pre-defined categories"""
    primary_goal: str
    expected_output: str
    constraints: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    complexity_level: str = "medium"
    urgency_level: str = "normal"
    scope: str = "single"
    confidence: float = 0.0
    
    @classmethod
    def from_analysis(cls, analysis: Dict[str, Any]) -> 'Intent':
        """Create Intent from LLM analysis"""
        return cls(
            primary_goal=analysis.get("primary_goal", ""),
            expected_output=analysis.get("expected_output", ""),
            constraints=analysis.get("constraints", []),
            success_criteria=analysis.get("success_criteria", []),
            complexity_level=analysis.get("complexity_level", "medium"),
            urgency_level=analysis.get("urgency_level", "normal"),
            scope=analysis.get("scope", "single"),
            confidence=analysis.get("confidence", 0.0)
        )


@dataclass
class Requirements:
    """Dynamic requirements extracted without templates"""
    functional: List[str] = field(default_factory=list)
    non_functional: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    
    @classmethod
    def from_extraction(cls, extraction: Dict[str, Any]) -> 'Requirements':
        """Create Requirements from extraction"""
        return cls(
            functional=extraction.get("functional", []),
            non_functional=extraction.get("non_functional", []),
            constraints=extraction.get("constraints", []),
            success_criteria=extraction.get("success_criteria", []),
            dependencies=extraction.get("dependencies", []),
            assumptions=extraction.get("assumptions", []),
            risks=extraction.get("risks", [])
        )


@dataclass
class DecompositionResult:
    """Result of universal decomposition"""
    tasks: List[Task]
    intent: Intent
    requirements: Requirements
    patterns_used: List[Pattern]
    confidence: float
    reasoning: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class PatternMemory:
    """Learns decomposition patterns without domain constraints"""
    
    def __init__(self, memory_client: VectorMemoryClient):
        self.memory_client = memory_client
        self.patterns: Dict[str, Pattern] = {}
        self.pattern_embeddings: Dict[str, List[float]] = {}
        
    async def learn_pattern(self, request: str, successful_decomposition: List[Task], 
                           execution_result: Dict[str, Any]):
        """Learn from successful decompositions"""
        logger.info("Learning new pattern from successful decomposition")
        
        # Extract abstract pattern
        abstract_pattern = self.extract_abstract_pattern(request, successful_decomposition, execution_result)
        
        # Generate unique pattern ID
        pattern_id = f"pattern_{datetime.utcnow().isoformat()}_{hash(request)}"
        
        # Store pattern with embeddings for similarity matching
        pattern_embedding = await self.get_embedding(self.pattern_to_text(abstract_pattern))
        
        self.patterns[pattern_id] = abstract_pattern
        self.pattern_embeddings[pattern_id] = pattern_embedding
        
        # Store in vector memory for persistence
        await self.store_pattern(pattern_id, abstract_pattern, pattern_embedding)
        
        logger.info(f"Learned pattern {pattern_id} with confidence {abstract_pattern.pattern_confidence}")
    
    def extract_abstract_pattern(self, request: str, decomposition: List[Task], 
                               execution_result: Dict[str, Any]) -> Pattern:
        """Extract universal patterns from successful decompositions"""
        
        # Extract complexity indicators from request
        complexity_indicators = self.extract_complexity_signals(request)
        
        # Extract dependency patterns
        dependency_patterns = self.extract_dependency_patterns(decomposition)
        
        # Extract execution patterns
        execution_patterns = self.extract_execution_patterns(decomposition, execution_result)
        
        # Extract success indicators
        success_indicators = self.extract_success_indicators(execution_result)
        
        # Extract context signals
        context_signals = self.extract_context_signals(request)
        
        # Determine abstraction level
        abstraction_level = self.determine_abstraction_level(request, decomposition)
        
        # Calculate pattern confidence
        pattern_confidence = self.calculate_pattern_confidence(execution_result)
        
        return Pattern(
            complexity_indicators=complexity_indicators,
            dependency_patterns=dependency_patterns,
            execution_patterns=execution_patterns,
            success_indicators=success_indicators,
            context_signals=context_signals,
            abstraction_level=abstraction_level,
            pattern_confidence=pattern_confidence,
            usage_count=1,
            success_rate=1.0
        )
    
    def extract_complexity_signals(self, request: str) -> List[str]:
        """Extract complexity signals from request"""
        signals = []
        
        # Length and structure complexity
        if len(request) > 1000:
            signals.append("long_description")
        if len(request.split('.')) > 10:
            signals.append("multi_requirement")
        
        # Technical complexity signals
        technical_terms = ["distributed", "microservice", "real-time", "scalable", "concurrent", 
                          "async", "performance", "security", "authentication", "database",
                          "api", "integration", "deployment", "monitoring"]
        
        for term in technical_terms:
            if term in request.lower():
                signals.append(f"technical_{term}")
        
        # Structural complexity
        if "and" in request.lower():
            signals.append("multi_component")
        if any(word in request.lower() for word in ["integrate", "connect", "combine"]):
            signals.append("integration_required")
        
        return signals
    
    def extract_dependency_patterns(self, decomposition: List[Task]) -> List[Dict[str, Any]]:
        """Extract dependency patterns from decomposition"""
        patterns = []
        
        # Sequential patterns
        sequential_count = 0
        parallel_count = 0
        
        for task in decomposition:
            if task.dependencies:
                sequential_count += 1
            else:
                parallel_count += 1
        
        if sequential_count > parallel_count:
            patterns.append({"type": "sequential_heavy", "ratio": sequential_count / len(decomposition)})
        else:
            patterns.append({"type": "parallel_heavy", "ratio": parallel_count / len(decomposition)})
        
        # Common dependency structures
        dependency_graph = {}
        for task in decomposition:
            dependency_graph[task.id] = task.dependencies or []
        
        # Identify common patterns
        if self.has_linear_dependency(dependency_graph):
            patterns.append({"type": "linear_dependency", "strength": 1.0})
        
        if self.has_fan_out_pattern(dependency_graph):
            patterns.append({"type": "fan_out", "strength": 1.0})
        
        if self.has_convergent_pattern(dependency_graph):
            patterns.append({"type": "convergent", "strength": 1.0})
        
        return patterns
    
    def extract_execution_patterns(self, decomposition: List[Task], 
                                 execution_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract execution patterns"""
        patterns = []
        
        # Task type distribution
        task_types = {}
        for task in decomposition:
            task_type = task.type.value if hasattr(task.type, 'value') else str(task.type)
            task_types[task_type] = task_types.get(task_type, 0) + 1
        
        patterns.append({"type": "task_distribution", "distribution": task_types})
        
        # Execution timing patterns
        if "execution_time" in execution_result:
            patterns.append({"type": "execution_time", "value": execution_result["execution_time"]})
        
        # Success/failure patterns
        if "task_results" in execution_result:
            success_rate = sum(1 for result in execution_result["task_results"] if result.get("success", False)) / len(execution_result["task_results"])
            patterns.append({"type": "success_rate", "value": success_rate})
        
        return patterns
    
    def extract_success_indicators(self, execution_result: Dict[str, Any]) -> List[str]:
        """Extract success indicators from execution result"""
        indicators = []
        
        if execution_result.get("success", False):
            indicators.append("execution_success")
        
        if execution_result.get("validation_score", 0) > 0.8:
            indicators.append("high_validation_score")
        
        if execution_result.get("confidence_score", 0) > 0.8:
            indicators.append("high_confidence")
        
        if execution_result.get("human_review_required", True) == False:
            indicators.append("no_human_review_needed")
        
        return indicators
    
    def extract_context_signals(self, request: str) -> List[str]:
        """Extract context signals from request"""
        signals = []
        
        # Technology signals
        if "python" in request.lower():
            signals.append("python_context")
        if "javascript" in request.lower():
            signals.append("javascript_context")
        if "api" in request.lower():
            signals.append("api_context")
        if "web" in request.lower():
            signals.append("web_context")
        
        # Domain signals (but not domain buckets)
        if any(word in request.lower() for word in ["auth", "login", "user"]):
            signals.append("user_management_context")
        if any(word in request.lower() for word in ["data", "database", "storage"]):
            signals.append("data_context")
        if any(word in request.lower() for word in ["deploy", "production", "server"]):
            signals.append("deployment_context")
        
        return signals
    
    def determine_abstraction_level(self, request: str, decomposition: List[Task]) -> str:
        """Determine abstraction level of the pattern"""
        
        # High abstraction: few, complex tasks
        if len(decomposition) <= 3:
            return "high"
        
        # Low abstraction: many, simple tasks
        if len(decomposition) >= 10:
            return "low"
        
        # Medium abstraction: balanced
        return "medium"
    
    def calculate_pattern_confidence(self, execution_result: Dict[str, Any]) -> float:
        """Calculate confidence in this pattern"""
        confidence = 0.0
        
        if execution_result.get("success", False):
            confidence += 0.3
        
        validation_score = execution_result.get("validation_score", 0)
        confidence += validation_score * 0.4
        
        confidence_score = execution_result.get("confidence_score", 0)
        confidence += confidence_score * 0.3
        
        return min(confidence, 1.0)
    
    def has_linear_dependency(self, dependency_graph: Dict[str, List[str]]) -> bool:
        """Check if dependency graph has linear pattern"""
        # Simple heuristic: each task depends on at most one other
        for task_id, deps in dependency_graph.items():
            if len(deps) > 1:
                return False
        return True
    
    def has_fan_out_pattern(self, dependency_graph: Dict[str, List[str]]) -> bool:
        """Check if dependency graph has fan-out pattern"""
        # One task that many others depend on
        dependency_counts = {}
        for task_id, deps in dependency_graph.items():
            for dep in deps:
                dependency_counts[dep] = dependency_counts.get(dep, 0) + 1
        
        return max(dependency_counts.values()) > 3 if dependency_counts else False
    
    def has_convergent_pattern(self, dependency_graph: Dict[str, List[str]]) -> bool:
        """Check if dependency graph has convergent pattern"""
        # One task that depends on many others
        for task_id, deps in dependency_graph.items():
            if len(deps) > 3:
                return True
        return False
    
    def pattern_to_text(self, pattern: Pattern) -> str:
        """Convert pattern to text for embedding"""
        return f"""
        Complexity: {' '.join(pattern.complexity_indicators)}
        Dependencies: {json.dumps(pattern.dependency_patterns)}
        Execution: {json.dumps(pattern.execution_patterns)}
        Success: {' '.join(pattern.success_indicators)}
        Context: {' '.join(pattern.context_signals)}
        Abstraction: {pattern.abstraction_level}
        """
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text"""
        try:
            if hasattr(settings, 'AZURE_OPENAI_ENDPOINT') and settings.AZURE_OPENAI_ENDPOINT:
                from openai import AsyncAzureOpenAI
                client = AsyncAzureOpenAI(
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
                )
            else:
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            response = await client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return [0.0] * 1536  # Default embedding size
    
    async def store_pattern(self, pattern_id: str, pattern: Pattern, embedding: List[float]):
        """Store pattern in vector memory"""
        try:
            await self.memory_client.store_pattern({
                "id": pattern_id,
                "pattern": pattern.__dict__,
                "embedding": embedding,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to store pattern: {e}")
    
    async def find_similar(self, request: str, intent: Intent, limit: int = 5) -> List[Pattern]:
        """Find similar patterns for given request and intent"""
        try:
            # Create query text
            query_text = f"""
            Request: {request}
            Goal: {intent.primary_goal}
            Output: {intent.expected_output}
            Complexity: {intent.complexity_level}
            Constraints: {' '.join(intent.constraints)}
            """
            
            # Get embedding for query
            query_embedding = await self.get_embedding(query_text)
            
            # Search for similar patterns
            similar_patterns = await self.memory_client.search_similar_patterns(
                query_embedding, limit=limit
            )
            
            # Convert to Pattern objects
            patterns = []
            for pattern_data in similar_patterns:
                if "pattern" in pattern_data:
                    pattern_dict = pattern_data["pattern"]
                    pattern = Pattern(**pattern_dict)
                    patterns.append(pattern)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to find similar patterns: {e}")
            return []
    
    def adapt_patterns(self, patterns: List[Pattern], requirements: Requirements) -> List[Pattern]:
        """Adapt patterns to current context"""
        adapted_patterns = []
        
        for pattern in patterns:
            # Create adapted copy
            adapted = Pattern(
                complexity_indicators=pattern.complexity_indicators.copy(),
                dependency_patterns=pattern.dependency_patterns.copy(),
                execution_patterns=pattern.execution_patterns.copy(),
                success_indicators=pattern.success_indicators.copy(),
                context_signals=pattern.context_signals.copy(),
                abstraction_level=pattern.abstraction_level,
                pattern_confidence=pattern.pattern_confidence,
                usage_count=pattern.usage_count,
                success_rate=pattern.success_rate
            )
            
            # Adapt based on current requirements
            if requirements.functional:
                adapted.complexity_indicators.extend([f"functional_{len(requirements.functional)}"])
            
            if requirements.non_functional:
                adapted.complexity_indicators.extend([f"non_functional_{len(requirements.non_functional)}"])
            
            if requirements.constraints:
                adapted.context_signals.extend([f"constraint_{constraint}" for constraint in requirements.constraints[:3]])
            
            adapted_patterns.append(adapted)
        
        return adapted_patterns


class IntentLearner:
    """Learns intent patterns without pre-defined categories"""
    
    def __init__(self):
        self.intent_patterns: Dict[str, List[Intent]] = {}
        if hasattr(settings, 'AZURE_OPENAI_ENDPOINT') and settings.AZURE_OPENAI_ENDPOINT:
            from openai import AsyncAzureOpenAI
            self.openai_client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
        else:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def learn_intent(self, request: str, patterns: List[Pattern]) -> Intent:
        """Learn intent from request and patterns dynamically"""
        logger.info("Learning intent from request and patterns")
        
        # Build context from patterns
        pattern_context = self.build_pattern_context(patterns)
        
        # Use LLM to understand intent
        intent_prompt = f"""
        Analyze this request and determine the underlying intent:
        
        REQUEST: {request}
        
        LEARNED PATTERNS: {pattern_context}
        
        Don't categorize into predefined buckets. Instead, analyze and describe:
        
        1. PRIMARY_GOAL: What is the user ultimately trying to achieve?
        2. EXPECTED_OUTPUT: What type of deliverable do they expect?
        3. CONSTRAINTS: What limitations or requirements exist?
        4. SUCCESS_CRITERIA: How will success be measured?
        5. COMPLEXITY_LEVEL: trivial, simple, medium, complex, or meta
        6. URGENCY_LEVEL: low, normal, high, or critical
        7. SCOPE: single (one deliverable) or multi (multiple deliverables)
        8. CONFIDENCE: How confident are you in this analysis? (0.0-1.0)
        
        Be specific and adaptive to this exact request, not generic.
        
        Respond in JSON format:
        {{
            "primary_goal": "specific goal description",
            "expected_output": "specific output type",
            "constraints": ["constraint1", "constraint2"],
            "success_criteria": ["criteria1", "criteria2"],
            "complexity_level": "medium",
            "urgency_level": "normal",
            "scope": "single",
            "confidence": 0.85
        }}
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at understanding user intent from requests. Be specific and adaptive."},
                    {"role": "user", "content": intent_prompt}
                ],
                temperature=0.3
            )
            
            intent_text = response.choices[0].message.content
            
            # Parse JSON response
            intent_data = json.loads(intent_text)
            intent = Intent.from_analysis(intent_data)
            
            logger.info(f"Learned intent: {intent.primary_goal} (confidence: {intent.confidence})")
            return intent
            
        except Exception as e:
            logger.error(f"Failed to learn intent: {e}")
            
            # Fallback intent
            return Intent(
                primary_goal="Complete the requested task",
                expected_output="Code and documentation",
                constraints=["Must be production-ready"],
                success_criteria=["Works correctly", "Passes tests"],
                complexity_level="medium",
                urgency_level="normal",
                scope="single",
                confidence=0.5
            )
    
    def build_pattern_context(self, patterns: List[Pattern]) -> str:
        """Build context from patterns for intent learning"""
        if not patterns:
            return "No similar patterns found"
        
        context_parts = []
        for i, pattern in enumerate(patterns[:3]):  # Use top 3 patterns
            context_parts.append(f"""
            Pattern {i+1}:
            - Complexity signals: {', '.join(pattern.complexity_indicators[:5])}
            - Success indicators: {', '.join(pattern.success_indicators[:3])}
            - Context: {', '.join(pattern.context_signals[:3])}
            - Abstraction level: {pattern.abstraction_level}
            - Success rate: {pattern.success_rate:.2f}
            """)
        
        return "\n".join(context_parts)
    
    async def reinforce_intent(self, request: str, intent: Intent, success: bool):
        """Reinforce intent learning from execution outcomes"""
        request_hash = str(hash(request))
        
        if request_hash not in self.intent_patterns:
            self.intent_patterns[request_hash] = []
        
        # Update intent confidence based on success
        if success:
            intent.confidence = min(intent.confidence + 0.1, 1.0)
        else:
            intent.confidence = max(intent.confidence - 0.1, 0.0)
        
        self.intent_patterns[request_hash].append(intent)
        logger.info(f"Reinforced intent learning: {intent.primary_goal} (confidence: {intent.confidence})")


class RequirementExtractor:
    """Extracts requirements dynamically without templates"""
    
    def __init__(self):
        if hasattr(settings, 'AZURE_OPENAI_ENDPOINT') and settings.AZURE_OPENAI_ENDPOINT:
            from openai import AsyncAzureOpenAI
            self.openai_client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
        else:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def extract(self, request: str, intent: Intent) -> Requirements:
        """Extract requirements based on learned intent"""
        logger.info("Extracting requirements dynamically")
        
        extraction_prompt = f"""
        Given this request and understood intent, extract ALL requirements comprehensively:
        
        REQUEST: {request}
        
        INTENT ANALYSIS:
        - Primary Goal: {intent.primary_goal}
        - Expected Output: {intent.expected_output}
        - Complexity Level: {intent.complexity_level}
        - Constraints: {intent.constraints}
        - Success Criteria: {intent.success_criteria}
        
        Extract requirements in these categories (be comprehensive but adaptive):
        
        1. FUNCTIONAL: What the system should do (features, behaviors, capabilities)
        2. NON_FUNCTIONAL: How the system should behave (performance, security, usability)
        3. CONSTRAINTS: What limits exist (technical, business, resource constraints)
        4. SUCCESS_CRITERIA: How to measure completion and success
        5. DEPENDENCIES: What external systems, libraries, or components are needed
        6. ASSUMPTIONS: What assumptions are being made
        7. RISKS: What could go wrong or cause issues
        
        Don't use templates. Be specific to this request and intent.
        
        Respond in JSON format:
        {{
            "functional": ["requirement1", "requirement2"],
            "non_functional": ["requirement1", "requirement2"],
            "constraints": ["constraint1", "constraint2"],
            "success_criteria": ["criteria1", "criteria2"],
            "dependencies": ["dependency1", "dependency2"],
            "assumptions": ["assumption1", "assumption2"],
            "risks": ["risk1", "risk2"]
        }}
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at requirement extraction. Be comprehensive and specific."},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.3
            )
            
            requirements_text = response.choices[0].message.content
            
            # Parse JSON response
            requirements_data = json.loads(requirements_text)
            requirements = Requirements.from_extraction(requirements_data)
            
            logger.info(f"Extracted {len(requirements.functional)} functional requirements")
            return requirements
            
        except Exception as e:
            logger.error(f"Failed to extract requirements: {e}")
            
            # Fallback requirements
            return Requirements(
                functional=["Implement the requested functionality"],
                non_functional=["Must be production-ready"],
                constraints=["Use best practices"],
                success_criteria=["Works correctly", "Passes tests"],
                dependencies=["Standard libraries"],
                assumptions=["User input is valid"],
                risks=["Implementation complexity"]
            )
    
    async def learn_from_success(self, request: str, requirements: Requirements, 
                               decomposition: List[Task], success: bool):
        """Learn from successful requirement extractions"""
        if success:
            logger.info("Learning from successful requirement extraction")
            # In a full implementation, this would update extraction patterns
            # For now, we log the success
            pass


class DecompositionEngine:
    """Decomposes based on learned patterns, not templates"""
    
    def __init__(self):
        if hasattr(settings, 'AZURE_OPENAI_ENDPOINT') and settings.AZURE_OPENAI_ENDPOINT:
            from openai import AsyncAzureOpenAI
            self.openai_client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
        else:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def decompose(self, request: str, intent: Intent, requirements: Requirements, 
                       patterns: List[Pattern]) -> Tuple[List[Task], str]:
        """Decompose based on learned patterns"""
        logger.info("Decomposing request using learned patterns")
        
        # Build pattern guidance
        pattern_guidance = self.build_pattern_guidance(patterns)
        
        # Build requirements context
        requirements_context = self.build_requirements_context(requirements)
        
        decomposition_prompt = f"""
        Decompose this request into atomic, executable tasks:
        
        REQUEST: {request}
        
        INTENT ANALYSIS:
        - Primary Goal: {intent.primary_goal}
        - Expected Output: {intent.expected_output}
        - Complexity Level: {intent.complexity_level}
        - Scope: {intent.scope}
        
        REQUIREMENTS:
        {requirements_context}
        
        LEARNED PATTERNS (use as guidance, adapt don't copy):
        {pattern_guidance}
        
        Create tasks that are:
        1. ATOMIC: Each task should do one specific thing
        2. EXECUTABLE: Each task should be actionable by an agent
        3. PROPERLY DEPENDENT: Tasks should have correct dependencies
        4. MEASURABLE: Each task should have clear success criteria
        5. APPROPRIATE: Tasks should match the complexity and scope
        
        Task types to consider:
        - code_generation: Generate code files
        - test_creation: Create test files
        - documentation: Write documentation
        - validation: Validate implementation
        - deployment: Deploy or configure
        - research: Research and analyze
        - optimization: Optimize performance
        - security: Security analysis or implementation
        
        Don't use templates. Be adaptive and specific to this request.
        
        Respond in JSON format:
        {{
            "tasks": [
                {{
                    "id": "task_1",
                    "title": "Specific task title",
                    "description": "Detailed description of what to do",
                    "type": "code_generation",
                    "complexity": "medium",
                    "estimated_time": 30,
                    "dependencies": [],
                    "success_criteria": ["criteria1", "criteria2"],
                    "agent_requirements": ["requirement1", "requirement2"]
                }}
            ],
            "reasoning": "Explanation of why this decomposition approach was chosen"
        }}
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at decomposing complex requests into atomic tasks. Be specific and adaptive."},
                    {"role": "user", "content": decomposition_prompt}
                ],
                temperature=0.3
            )
            
            decomposition_text = response.choices[0].message.content
            
            # Parse JSON response
            decomposition_data = json.loads(decomposition_text)
            
            # Convert to Task objects
            tasks = []
            for task_data in decomposition_data.get("tasks", []):
                task = Task(
                    id=task_data.get("id", f"task_{len(tasks)}"),
                    title=task_data.get("title", "Untitled Task"),
                    description=task_data.get("description", ""),
                    type=TaskType(task_data.get("type", "code_generation")),
                    complexity=task_data.get("complexity", "medium"),
                    estimated_time=task_data.get("estimated_time", 30),
                    dependencies=task_data.get("dependencies", []),
                    status=TaskStatus.PENDING,
                    context={"success_criteria": task_data.get("success_criteria", [])},
                    agent_requirements=task_data.get("agent_requirements", [])
                )
                tasks.append(task)
            
            reasoning = decomposition_data.get("reasoning", "No reasoning provided")
            
            logger.info(f"Decomposed into {len(tasks)} tasks")
            return tasks, reasoning
            
        except Exception as e:
            logger.error(f"Failed to decompose request: {e}")
            
            # Fallback decomposition
            fallback_task = Task(
                id="fallback_task",
                title="Complete the requested task",
                description=request,
                type=TaskType.CODE_GENERATION,
                complexity="medium",
                estimated_time=60,
                dependencies=[],
                status=TaskStatus.PENDING,
                context={"success_criteria": ["Works correctly"]},
                agent_requirements=["General coding ability"]
            )
            
            return [fallback_task], "Fallback decomposition due to parsing error"
    
    def build_pattern_guidance(self, patterns: List[Pattern]) -> str:
        """Build pattern guidance for decomposition"""
        if not patterns:
            return "No similar patterns found - create novel decomposition"
        
        guidance_parts = []
        for i, pattern in enumerate(patterns[:3]):  # Use top 3 patterns
            guidance_parts.append(f"""
            Pattern {i+1} (confidence: {pattern.pattern_confidence:.2f}):
            - Complexity indicators: {', '.join(pattern.complexity_indicators[:5])}
            - Dependency patterns: {json.dumps(pattern.dependency_patterns[:2])}
            - Success indicators: {', '.join(pattern.success_indicators[:3])}
            - Abstraction level: {pattern.abstraction_level}
            - Success rate: {pattern.success_rate:.2f}
            """)
        
        return "\n".join(guidance_parts)
    
    def build_requirements_context(self, requirements: Requirements) -> str:
        """Build requirements context for decomposition"""
        return f"""
        Functional Requirements:
        {chr(10).join(f"- {req}" for req in requirements.functional)}
        
        Non-Functional Requirements:
        {chr(10).join(f"- {req}" for req in requirements.non_functional)}
        
        Constraints:
        {chr(10).join(f"- {constraint}" for constraint in requirements.constraints)}
        
        Success Criteria:
        {chr(10).join(f"- {criteria}" for criteria in requirements.success_criteria)}
        
        Dependencies:
        {chr(10).join(f"- {dep}" for dep in requirements.dependencies)}
        
        Risks:
        {chr(10).join(f"- {risk}" for risk in requirements.risks)}
        """
    
    async def learn_from_failure(self, request: str, intent: Intent, 
                               requirements: Requirements, failure_result: Dict[str, Any]):
        """Learn from decomposition failures"""
        logger.info("Learning from decomposition failure")
        # In a full implementation, this would update decomposition strategies
        # For now, we log the failure for analysis
        pass


class UniversalDecomposer:
    """
    Universal NLP decomposer that learns patterns without domain constraints
    Based on emergent understanding and adaptive pattern recognition
    """
    
    def __init__(self, memory_client: VectorMemoryClient):
        self.pattern_memory = PatternMemory(memory_client)
        self.intent_learner = IntentLearner()
        self.requirement_extractor = RequirementExtractor()
        self.decomposition_engine = DecompositionEngine()
        self.memory_client = memory_client
        
        logger.info("Universal decomposer initialized")
    
    async def decompose_request(self, request: str) -> DecompositionResult:
        """Universal decomposition without domain assumptions"""
        logger.info(f"Starting universal decomposition for request: {request[:100]}...")
        
        try:
            # Step 1: Extract universal patterns (not domain-specific)
            logger.info("Step 1: Extracting universal patterns")
            # For now, we'll use empty patterns - will be populated as system learns
            patterns = []
            
            # Step 2: Learn intent from patterns (emergent, not pre-defined)
            logger.info("Step 2: Learning intent from patterns")
            intent = await self.intent_learner.learn_intent(request, patterns)
            
            # Step 3: Extract requirements dynamically
            logger.info("Step 3: Extracting requirements dynamically")
            requirements = await self.requirement_extractor.extract(request, intent)
            
            # Step 4: Find similar patterns
            logger.info("Step 4: Finding similar patterns")
            similar_patterns = await self.pattern_memory.find_similar(request, intent)
            
            # Step 5: Adapt patterns to current context
            logger.info("Step 5: Adapting patterns to context")
            adapted_patterns = self.pattern_memory.adapt_patterns(similar_patterns, requirements)
            
            # Step 6: Decompose based on learned patterns
            logger.info("Step 6: Decomposing based on learned patterns")
            tasks, reasoning = await self.decomposition_engine.decompose(
                request, intent, requirements, adapted_patterns
            )
            
            # Calculate overall confidence
            confidence = self.calculate_confidence(intent, requirements, adapted_patterns)
            
            result = DecompositionResult(
                tasks=tasks,
                intent=intent,
                requirements=requirements,
                patterns_used=adapted_patterns,
                confidence=confidence,
                reasoning=reasoning,
                metadata={
                    "decomposition_timestamp": datetime.utcnow().isoformat(),
                    "patterns_found": len(similar_patterns),
                    "patterns_adapted": len(adapted_patterns)
                }
            )
            
            logger.info(f"Decomposition complete: {len(tasks)} tasks, confidence: {confidence:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Decomposition failed: {e}")
            
            # Fallback decomposition
            fallback_intent = Intent(
                primary_goal="Complete the requested task",
                expected_output="Working solution",
                confidence=0.3
            )
            
            fallback_requirements = Requirements(
                functional=["Implement the requested functionality"],
                success_criteria=["Works correctly"]
            )
            
            fallback_task = Task(
                id="fallback_task",
                title="Complete the requested task",
                description=request,
                type=TaskType.CODE_GENERATION,
                complexity="medium",
                estimated_time=60,
                dependencies=[],
                status=TaskStatus.PENDING,
                context={"success_criteria": ["Works correctly"]},
                agent_requirements=["General coding ability"]
            )
            
            return DecompositionResult(
                tasks=[fallback_task],
                intent=fallback_intent,
                requirements=fallback_requirements,
                patterns_used=[],
                confidence=0.3,
                reasoning="Fallback decomposition due to error",
                metadata={"error": str(e)}
            )
    
    def calculate_confidence(self, intent: Intent, requirements: Requirements, 
                           patterns: List[Pattern]) -> float:
        """Calculate overall confidence in decomposition"""
        confidence = 0.0
        
        # Intent confidence
        confidence += intent.confidence * 0.3
        
        # Requirements confidence (based on completeness)
        req_score = 0.0
        if requirements.functional:
            req_score += 0.25
        if requirements.non_functional:
            req_score += 0.25
        if requirements.constraints:
            req_score += 0.25
        if requirements.success_criteria:
            req_score += 0.25
        
        confidence += req_score * 0.3
        
        # Pattern confidence (based on similarity and success rate)
        if patterns:
            pattern_score = sum(p.pattern_confidence * p.success_rate for p in patterns) / len(patterns)
            confidence += pattern_score * 0.4
        else:
            confidence += 0.2  # Base confidence when no patterns
        
        return min(confidence, 1.0)
    
    async def learn_from_execution(self, request: str, decomposition_result: DecompositionResult, 
                                 execution_result: Dict[str, Any]):
        """Learn from execution outcomes to improve future decompositions"""
        logger.info("Learning from execution results")
        
        try:
            success = execution_result.get("success", False)
            
            if success:
                # Learn successful patterns
                await self.pattern_memory.learn_pattern(
                    request, decomposition_result.tasks, execution_result
                )
                
                # Reinforce intent understanding
                await self.intent_learner.reinforce_intent(
                    request, decomposition_result.intent, success
                )
                
                # Learn from successful requirement extraction
                await self.requirement_extractor.learn_from_success(
                    request, decomposition_result.requirements, 
                    decomposition_result.tasks, success
                )
                
                logger.info("Successfully learned from execution")
                
            else:
                # Learn from failures
                await self.decomposition_engine.learn_from_failure(
                    request, decomposition_result.intent, 
                    decomposition_result.requirements, execution_result
                )
                
                logger.info("Learned from execution failure")
                
        except Exception as e:
            logger.error(f"Failed to learn from execution: {e}")
    
    async def get_decomposition_stats(self) -> Dict[str, Any]:
        """Get statistics about decomposition performance"""
        return {
            "total_patterns": len(self.pattern_memory.patterns),
            "pattern_success_rates": {
                pattern_id: pattern.success_rate 
                for pattern_id, pattern in self.pattern_memory.patterns.items()
            },
            "intent_patterns": len(self.intent_learner.intent_patterns),
            "system_confidence": "adaptive",
            "learning_status": "active"
        }