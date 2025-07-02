"""
Meta Prompt Engineer - The brain that creates and evolves prompts
Implements recursive self-improvement for code generation
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import json
import asyncio
from pathlib import Path

import structlog
from src.agents.meta_prompts.prompt_genome import PromptGenome
from src.agents.meta_prompts.principle_library import PrincipleLibrary
from src.memory.client import VectorMemoryClient
from src.common.config import settings

logger = structlog.get_logger()


class PromptEvolutionStrategy(Enum):
    """Strategies for evolving prompts based on Popperian epistemology"""
    CONJECTURE_REFUTATION = "conjecture_refutation"  # Generate hypotheses, test, refute
    EXPLANATION_DEPTH = "explanation_depth"  # Seek deeper, harder-to-vary explanations
    ERROR_CORRECTION = "error_correction"  # Learn from mistakes
    PRINCIPLE_EXTRACTION = "principle_extraction"  # Extract universal principles
    CREATIVE_DESTRUCTION = "creative_destruction"  # Deliberately break to understand
    CONTRARIAN = "contrarian"  # Challenge conventional wisdom
    SYNTHESIS = "synthesis"  # Combine best aspects of multiple approaches


class MetaPromptEngineer:
    """
    The meta-level prompt engineer that creates and evolves prompts
    This is the key to continuous improvement in code quality
    """
    
    def __init__(self, genome_storage_path: Optional[str] = None):
        self.principle_library = PrincipleLibrary()
        self.genome_storage_path = genome_storage_path or "/app/data/prompt_genomes"
        self.memory_client = None
        self._ensure_storage_exists()
        self.active_genomes: Dict[str, PromptGenome] = {}
        self.performance_history: List[Dict[str, Any]] = []
        self._load_existing_genomes()
    
    def _ensure_storage_exists(self):
        """Ensure genome storage directory exists"""
        Path(self.genome_storage_path).mkdir(parents=True, exist_ok=True)
    
    def _load_existing_genomes(self):
        """Load existing genomes from storage"""
        genome_path = Path(self.genome_storage_path)
        for genome_file in genome_path.glob("*.json"):
            try:
                with open(genome_file, 'r') as f:
                    genome_data = json.load(f)
                    key = genome_file.stem
                    self.active_genomes[key] = PromptGenome.from_json(json.dumps(genome_data))
                    logger.info(f"Loaded genome: {key}")
            except Exception as e:
                logger.error(f"Failed to load genome {genome_file}: {e}")
    
    async def generate_meta_prompt(
        self,
        task_description: str,
        agent_role: str,
        context: Dict[str, Any],
        evolution_strategy: PromptEvolutionStrategy = PromptEvolutionStrategy.EXPLANATION_DEPTH
    ) -> str:
        """
        Generate an evolved meta-prompt for the given task
        This is the main entry point for the ensemble agents
        """
        logger.info(f"Generating meta-prompt for {agent_role} using {evolution_strategy.value}")
        
        # 1. Analyze the task deeply
        task_analysis = await self._deep_task_analysis(task_description, context)
        
        # 2. Retrieve or create genome
        genome_key = f"{agent_role}:{task_analysis['primary_category']}"
        genome = self.active_genomes.get(genome_key)
        
        if not genome:
            genome = await self._create_initial_genome(agent_role, task_analysis)
            self.active_genomes[genome_key] = genome
        
        # 3. Apply evolution strategy
        evolved_genome = await self._evolve_genome(genome, evolution_strategy, task_analysis)
        
        # 4. Construct the meta-prompt
        meta_prompt = self._construct_meta_prompt(evolved_genome, task_description, context)
        
        # 5. Add recursive self-improvement layer
        meta_prompt = self._add_recursive_improvement_layer(meta_prompt, agent_role, evolution_strategy)
        
        # 6. Store evolved genome
        self.active_genomes[genome_key] = evolved_genome
        self._save_genome(genome_key, evolved_genome)
        
        return meta_prompt
    
    async def _deep_task_analysis(self, description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deeply analyze the task to understand its nature, complexity, and requirements
        This goes beyond simple keyword matching
        """
        description_lower = description.lower()
        
        # Category detection with weights
        category_signals = {
            "api": ["api", "endpoint", "rest", "graphql", "webhook", "http", "request", "response"],
            "database": ["database", "sql", "orm", "migration", "schema", "postgres", "mysql", "mongo"],
            "security": ["secure", "auth", "encrypt", "permission", "oauth", "jwt", "token", "credential"],
            "concurrency": ["async", "concurrent", "parallel", "thread", "worker", "queue", "stream"],
            "distributed": ["microservice", "distributed", "kafka", "rabbit", "event", "message", "pubsub"],
            "ml": ["ml", "ai", "model", "train", "predict", "neural", "tensorflow", "pytorch"],
            "performance": ["fast", "optimize", "cache", "scale", "latency", "throughput", "benchmark"],
            "testing": ["test", "tdd", "bdd", "coverage", "mock", "fixture", "assertion"],
            "frontend": ["react", "vue", "angular", "ui", "component", "state", "redux", "css"],
            "blockchain": ["blockchain", "crypto", "smart contract", "web3", "defi", "nft"]
        }
        
        # Calculate category scores
        category_scores = {}
        for category, signals in category_signals.items():
            score = sum(2 if signal in description_lower else 0 for signal in signals)
            if score > 0:
                category_scores[category] = score
        
        # Sort categories by score
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        primary_category = sorted_categories[0][0] if sorted_categories else "general"
        all_categories = [cat for cat, score in sorted_categories if score > 2]
        
        # Complexity assessment
        complexity_factors = {
            "description_length": len(description) / 100,
            "category_count": len(all_categories),
            "requirement_count": len(context.get("requirements", {})),
            "constraint_count": len(context.get("constraints", {})),
            "has_performance_requirements": any(
                perf in str(context.get("constraints", {})).lower() 
                for perf in ["latency", "throughput", "tps", "qps"]
            ),
            "has_security_requirements": "security" in all_categories or "auth" in description_lower,
            "is_distributed": "distributed" in all_categories or "microservice" in description_lower
        }
        
        complexity_score = (
            complexity_factors.get("description_length", 0) * 0.1 +
            complexity_factors.get("category_count", 0) * 2 +
            complexity_factors.get("requirement_count", 0) * 1 +
            complexity_factors.get("constraint_count", 0) * 1.5 +
            (3 if complexity_factors.get("has_performance_requirements") else 0) +
            (3 if complexity_factors.get("has_security_requirements") else 0) +
            (4 if complexity_factors.get("is_distributed") else 0)
        )
        
        complexity = (
            "trivial" if complexity_score < 5 else
            "simple" if complexity_score < 10 else
            "medium" if complexity_score < 20 else
            "complex" if complexity_score < 30 else
            "meta"
        )
        
        # Extract key patterns and concepts
        patterns = self._extract_patterns(description, context)
        
        return {
            "primary_category": primary_category,
            "all_categories": all_categories,
            "complexity": complexity,
            "complexity_score": complexity_score,
            "patterns": patterns,
            "requirements": context.get("requirements", {}),
            "constraints": context.get("constraints", {}),
            "has_examples": bool(context.get("examples")),
            "needs_architecture": complexity in ["complex", "meta"] or "architect" in description_lower,
            "needs_security": "security" in all_categories or any(
                sec in description_lower for sec in ["secure", "auth", "password", "token"]
            ),
            "needs_performance": "performance" in all_categories or any(
                perf in description_lower for perf in ["fast", "scale", "optimize", "latency"]
            )
        }
    
    def _extract_patterns(self, description: str, context: Dict[str, Any]) -> List[str]:
        """Extract design patterns and architectural patterns from the task"""
        patterns = []
        
        pattern_indicators = {
            "factory": ["create", "instantiate", "build"],
            "singleton": ["single instance", "global", "shared state"],
            "observer": ["notify", "subscribe", "event", "listener"],
            "strategy": ["algorithm", "behavior", "policy"],
            "decorator": ["wrap", "enhance", "extend functionality"],
            "adapter": ["convert", "interface", "compatibility"],
            "repository": ["data access", "persistence", "storage"],
            "mvc": ["model", "view", "controller"],
            "cqrs": ["command", "query", "separation"],
            "event_sourcing": ["event", "audit", "history"],
            "microservices": ["service", "distributed", "independent"],
            "layered": ["layer", "tier", "separation of concerns"]
        }
        
        desc_lower = description.lower()
        for pattern, indicators in pattern_indicators.items():
            if any(indicator in desc_lower for indicator in indicators):
                patterns.append(pattern)
        
        return patterns
    
    async def _create_initial_genome(
        self, 
        agent_role: str, 
        task_analysis: Dict[str, Any]
    ) -> PromptGenome:
        """Create an initial genome based on role and task analysis"""
        
        # Base objectives that apply to all code generation
        base_objectives = [
            "Generate production-ready code that completely solves the stated problem",
            "Include comprehensive error handling for all edge cases",
            "Follow language-specific idioms and best practices",
            "Ensure code is self-documenting with clear naming and structure",
            "Provide working code without placeholders or TODOs"
        ]
        
        # Role-specific objectives
        role_objectives = {
            "architect": [
                "Design a scalable and maintainable system architecture",
                "Define clear module boundaries and interfaces",
                "Consider future extensibility and change scenarios",
                "Document architectural decisions and trade-offs",
                "Ensure the design supports the stated non-functional requirements"
            ],
            "implementer": [
                "Write clean, efficient, and readable implementation code",
                "Handle all specified requirements completely",
                "Optimize for both correctness and performance",
                "Use appropriate data structures and algorithms",
                "Include helpful comments for complex logic"
            ],
            "reviewer": [
                "Identify potential bugs, security issues, and inefficiencies",
                "Suggest improvements for code clarity and maintainability",
                "Verify adherence to best practices and principles",
                "Check for edge cases and error handling completeness",
                "Provide actionable feedback with specific examples"
            ],
            "test_engineer": [
                "Create comprehensive test coverage (>90% for critical paths)",
                "Include unit, integration, and edge case tests",
                "Use appropriate testing patterns and frameworks",
                "Ensure tests are deterministic and independent",
                "Include performance and security tests where relevant"
            ],
            "security_expert": [
                "Identify all potential security vulnerabilities",
                "Implement defense-in-depth strategies",
                "Follow OWASP guidelines and security best practices",
                "Include security tests and validation",
                "Document security considerations and mitigations"
            ],
            "optimizer": [
                "Analyze performance bottlenecks and optimization opportunities",
                "Implement efficient algorithms and data structures",
                "Consider caching, indexing, and parallelization strategies",
                "Balance performance with code readability",
                "Provide benchmarks and performance metrics"
            ],
            "documentor": [
                "Create comprehensive and clear documentation",
                "Include API documentation with examples",
                "Document design decisions and trade-offs",
                "Provide setup and deployment instructions",
                "Create user guides and troubleshooting sections"
            ]
        }
        
        # Get relevant principles from library
        principles = self.principle_library.get_principles_for_task(task_analysis["all_categories"])
        
        # Task-specific constraints
        constraints = [
            "Code must be syntactically correct and executable",
            "No placeholder comments or incomplete implementations",
            "All imports must be valid and available",
            "Follow the specified framework/library conventions",
            "Respect the stated performance and security requirements"
        ]
        
        # Add complexity-specific constraints
        if task_analysis["complexity"] in ["complex", "meta"]:
            constraints.extend([
                "Include comprehensive error handling and recovery",
                "Design for horizontal scalability",
                "Consider distributed system challenges",
                "Include monitoring and observability"
            ])
        
        # Meta-instructions for thinking process
        meta_instructions = [
            "First, deeply understand the problem before coding",
            "Consider multiple approaches and choose the best",
            "Think about edge cases and failure modes",
            "Validate assumptions before implementing",
            "Question if the solution could be simpler",
            "Consider the long-term maintainability"
        ]
        
        # Add strategy-specific meta-instructions
        if task_analysis["needs_architecture"]:
            meta_instructions.append("Start with high-level design before implementation")
        if task_analysis["needs_security"]:
            meta_instructions.append("Think like an attacker - how could this be exploited?")
        if task_analysis["needs_performance"]:
            meta_instructions.append("Consider performance implications of design decisions")
        
        # Success criteria
        critique_criteria = [
            "Does the code completely solve the stated problem?",
            "Is the code production-ready without modifications?",
            "Are all edge cases and errors handled properly?",
            "Is the code maintainable and well-structured?",
            "Does it follow the specified requirements and constraints?",
            "Would a senior engineer approve this in a code review?"
        ]
        
        genome = PromptGenome(
            objectives=base_objectives + role_objectives.get(agent_role, []),
            constraints=constraints,
            principles=principles,
            examples=[],  # Will be populated from memory
            meta_instructions=meta_instructions,
            critique_criteria=critique_criteria,
            evolution_history=[{
                "timestamp": datetime.utcnow().isoformat(),
                "type": "creation",
                "role": agent_role,
                "task_complexity": task_analysis["complexity"]
            }],
            performance_metrics={},
            mutation_rate=0.1
        )
        
        return genome
    
    async def _evolve_genome(
        self,
        genome: PromptGenome,
        strategy: PromptEvolutionStrategy,
        task_analysis: Dict[str, Any]
    ) -> PromptGenome:
        """
        Evolve the genome using the specified strategy
        This is where the magic of improvement happens
        """
        evolved = PromptGenome(
            objectives=genome.objectives.copy(),
            constraints=genome.constraints.copy(),
            principles=genome.principles.copy(),
            examples=genome.examples.copy(),
            meta_instructions=genome.meta_instructions.copy(),
            critique_criteria=genome.critique_criteria.copy(),
            evolution_history=genome.evolution_history.copy(),
            performance_metrics=genome.performance_metrics.copy(),
            mutation_rate=genome.mutation_rate
        )
        
        # Apply strategy-specific evolution
        if strategy == PromptEvolutionStrategy.EXPLANATION_DEPTH:
            # Deepen the requirement for explanatory depth
            evolved.meta_instructions.extend([
                "Explain WHY each design decision was made, not just what",
                "Show how each component contributes to the whole system",
                "Demonstrate why this solution is hard to vary without breaking",
                "Identify the core principles that guide the implementation",
                "Make the implicit explicit - surface hidden assumptions"
            ])
            evolved.critique_criteria.extend([
                "Are the explanations deep and hard to vary?",
                "Do the design decisions follow from first principles?",
                "Is the 'why' as clear as the 'what' and 'how'?"
            ])
            evolved.objectives.append(
                "Create solutions that embody good explanations - hard to vary while maintaining function"
            )
            
        elif strategy == PromptEvolutionStrategy.CONJECTURE_REFUTATION:
            # Add Popperian method to problem-solving
            evolved.meta_instructions.extend([
                "List at least 3 different approaches to solve this problem",
                "For each approach, identify its strengths and potential failure modes",
                "Explicitly state why you're rejecting alternative approaches",
                "Choose the approach that best survives criticism",
                "Document what could falsify or break your solution"
            ])
            evolved.objectives.append(
                "Demonstrate critical thinking through explicit conjecture and refutation"
            )
            evolved.critique_criteria.append(
                "Were alternatives seriously considered and properly refuted?"
            )
            
        elif strategy == PromptEvolutionStrategy.ERROR_CORRECTION:
            # Learn from past mistakes
            if self.performance_history:
                # Analyze recent failures
                recent_failures = [
                    record for record in self.performance_history[-20:]
                    if record.get("success", True) is False
                ]
                
                if recent_failures:
                    common_issues = self._extract_common_issues(recent_failures)
                    evolved.constraints.extend([
                        f"Specifically avoid: {issue}" for issue in common_issues[:3]
                    ])
                    evolved.meta_instructions.append(
                        "Double-check for these common mistakes: " + ", ".join(common_issues[:3])
                    )
            
            evolved.meta_instructions.extend([
                "Actively look for potential errors in your approach",
                "Consider what could go wrong and preemptively address it",
                "Build in error correction mechanisms, not just error prevention",
                "Make errors informative - they should guide toward the solution"
            ])
            
        elif strategy == PromptEvolutionStrategy.PRINCIPLE_EXTRACTION:
            # Focus on extracting and applying universal principles
            task_principles = self.principle_library.get_principles_for_task(
                task_analysis["all_categories"]
            )
            evolved.principles = task_principles
            
            evolved.meta_instructions.extend([
                "Identify the universal principles that apply to this problem",
                "Show how timeless principles manifest in this specific solution",
                "Extract new principles from the problem-solving process",
                "Demonstrate how principles compose and interact"
            ])
            evolved.objectives.append(
                "Surface and apply universal principles that transcend specific technologies"
            )
            
        elif strategy == PromptEvolutionStrategy.CREATIVE_DESTRUCTION:
            # Antifragile approach - design for chaos
            evolved.meta_instructions.extend([
                "Consider how a malicious actor might abuse this system",
                "Design with failure modes as first-class concerns",
                "Build in chaos engineering principles from the start",
                "Make the system stronger under stress, not just resistant",
                "Explicitly handle the 'what could possibly go wrong' scenarios"
            ])
            evolved.objectives.extend([
                "Create antifragile systems that improve under stress",
                "Design for graceful degradation and recovery"
            ])
            evolved.constraints.append(
                "Every component must handle failure of its dependencies"
            )
            
        elif strategy == PromptEvolutionStrategy.CONTRARIAN:
            # Challenge conventional wisdom
            contrarian_principles = self.principle_library.get_contrarian_principles()
            evolved.principles.extend(contrarian_principles)
            
            evolved.meta_instructions.extend([
                "Question conventional wisdom - is the 'best practice' actually best here?",
                "Consider if the opposite approach might work better",
                "Challenge assumptions that everyone takes for granted",
                "Look for solutions that are simple but non-obvious",
                "Sometimes the 'wrong' way is right for this context"
            ])
            evolved.objectives.append(
                "Find elegant solutions by questioning conventional approaches"
            )
            
        elif strategy == PromptEvolutionStrategy.SYNTHESIS:
            # Combine best aspects of multiple approaches
            evolved.meta_instructions.extend([
                "Identify complementary approaches that could be combined",
                "Look for synergies between different design philosophies",
                "Create novel solutions by synthesizing existing patterns",
                "Balance competing concerns through creative integration",
                "Find the 'third way' that transcends typical trade-offs"
            ])
            evolved.objectives.append(
                "Synthesize novel solutions from existing approaches"
            )
        
        # Record evolution
        evolved.evolution_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "strategy": strategy.value,
            "task_complexity": task_analysis["complexity"],
            "categories": task_analysis["all_categories"],
            "parent_fitness": genome.fitness_score()
        })
        
        return evolved
    
    def _construct_meta_prompt(
        self,
        genome: PromptGenome,
        task_description: str,
        context: Dict[str, Any]
    ) -> str:
        """Construct the actual prompt from the evolved genome"""
        
        sections = []
        
        # 1. Identity and Role
        sections.append("# Your Identity and Expertise")
        sections.append(
            "You are a world-class software engineer with deep expertise in system design, "
            "algorithms, and software craftsmanship. You embody the principles of critical "
            "rationalism - seeking better explanations through conjecture and refutation."
        )
        sections.append("")
        
        # 2. Primary Objectives
        sections.append("# Primary Objectives")
        for i, objective in enumerate(genome.objectives, 1):
            sections.append(f"{i}. {objective}")
        sections.append("")
        
        # 3. Guiding Principles
        sections.append("# Guiding Principles")
        sections.append("Let these principles guide your solution:")
        for principle in genome.principles:
            sections.append(f"• {principle}")
        sections.append("")
        
        # 4. The Task
        sections.append("# The Task")
        sections.append(task_description)
        sections.append("")
        
        # 5. Requirements and Constraints
        if context.get("requirements"):
            sections.append("# Requirements")
            sections.append("```json")
            sections.append(json.dumps(context["requirements"], indent=2))
            sections.append("```")
            sections.append("")
        
        if context.get("constraints") or genome.constraints:
            sections.append("# Constraints")
            if context.get("constraints"):
                sections.append("Project constraints:")
                sections.append("```json")
                sections.append(json.dumps(context["constraints"], indent=2))
                sections.append("```")
            sections.append("Technical constraints:")
            for constraint in genome.constraints:
                sections.append(f"• {constraint}")
            sections.append("")
        
        # 6. Thinking Process (Meta-Instructions)
        sections.append("# Your Thinking Process")
        for instruction in genome.meta_instructions:
            sections.append(f"→ {instruction}")
        sections.append("")
        
        # 7. Success Criteria
        sections.append("# Success Criteria")
        sections.append("Your solution will be evaluated based on:")
        for criterion in genome.critique_criteria:
            sections.append(f"□ {criterion}")
        sections.append("")
        
        # 8. Output Requirements
        sections.append("# Output Requirements")
        sections.append(
            "Provide complete, production-ready code that can be deployed immediately. "
            "This means:"
        )
        sections.append("• Full implementation with no placeholders or TODOs")
        sections.append("• All error cases handled with appropriate messages")
        sections.append("• Clear documentation explaining design decisions")
        sections.append("• Example usage or test cases demonstrating functionality")
        sections.append("• Any necessary configuration or setup instructions")
        sections.append("")
        
        # 9. Examples (if available)
        if genome.examples:
            sections.append("# Examples of Excellence")
            sections.append("Here are examples of high-quality solutions:")
            for i, example in enumerate(genome.examples[:3], 1):
                sections.append(f"\nExample {i}:")
                sections.append("```")
                sections.append(str(example.get("code", "")))
                sections.append("```")
                if example.get("explanation"):
                    sections.append(f"Key insight: {example['explanation']}")
            sections.append("")
        
        return "\n".join(sections)
    
    def _add_recursive_improvement_layer(
        self,
        prompt: str,
        agent_role: str,
        strategy: PromptEvolutionStrategy
    ) -> str:
        """
        Add meta-cognitive layer for recursive self-improvement
        This is what makes the system truly intelligent
        """
        
        recursive_layer = f"""

# 🔄 Recursive Self-Improvement Process

Before finalizing your solution, engage in meta-cognitive reflection:

## 1. Self-Critique (Be Your Own Harshest Critic)
- What are the weakest parts of your solution?
- Where might it fail under stress or edge cases?
- What assumptions are you making that could be wrong?
- Is there unnecessary complexity that could be removed?

## 2. Alternative Exploration (Challenge Your Approach)
- What's a completely different way to solve this?
- What would the opposite approach look like?
- How would an expert in a different paradigm solve this?
- What non-obvious solution might be simpler?

## 3. Principle Validation (Check Against Timeless Truths)
- Which principles does your solution embody?
- Are there principles you're violating? Why?
- Could applying different principles improve the solution?
- What new principles emerge from your solution?

## 4. Explanation Depth (Make It Hard to Vary)
- Why is this the right solution (not just a solution)?
- What would break if you changed any key component?
- How does each part contribute to the whole?
- Where are the boundaries of this solution's applicability?

## 5. Error Correction Built-In (Antifragility)
- How does your solution handle its own failures?
- What feedback loops exist for improvement?
- How would you debug issues in production?
- What would make this solution stronger over time?

## 6. Synthesis and Transcendence
After this reflection:
1. Identify at least ONE specific improvement
2. Implement that improvement in your solution
3. Document why this makes it better
4. Present your ENHANCED final solution

Remember: You're not just writing code, you're creating an explanation of how to solve this class of problems. The code is merely the executable form of that explanation.

---

Now, provide your solution with the understanding that it should demonstrate not just competence, but mastery through critical thinking and continuous improvement.
"""
        
        # Add strategy-specific recursive elements
        strategy_specific = {
            PromptEvolutionStrategy.EXPLANATION_DEPTH: """
## Special Focus: Explanatory Depth
- Ensure every design decision has a deep 'why'
- Show how changing any part would break the whole
- Make the solution a teaching tool, not just working code
""",
            PromptEvolutionStrategy.CONJECTURE_REFUTATION: """
## Special Focus: Conjecture and Refutation
- Present your initial approach, then refute it
- Show the evolution of your thinking
- Document failed approaches and why they failed
""",
            PromptEvolutionStrategy.ERROR_CORRECTION: """
## Special Focus: Error Correction
- Explicitly identify potential failure modes
- Build in mechanisms for error detection and recovery
- Show how the system learns from errors
""",
            PromptEvolutionStrategy.CREATIVE_DESTRUCTION: """
## Special Focus: Creative Destruction
- Try to break your own solution
- Identify the breaking points
- Strengthen those exact points
""",
            PromptEvolutionStrategy.CONTRARIAN: """
## Special Focus: Contrarian Thinking
- Challenge at least one "best practice"
- Justify why the unconventional approach is better here
- Show when conventional wisdom would be wrong
"""
        }
        
        if strategy in strategy_specific:
            recursive_layer += strategy_specific[strategy]
        
        return prompt + recursive_layer
    
    def _extract_common_issues(self, failures: List[Dict[str, Any]]) -> List[str]:
        """Extract common issues from failure records"""
        issues = []
        for failure in failures:
            if "error" in failure:
                issues.append(failure["error"])
            if "validation_errors" in failure:
                issues.extend(failure["validation_errors"])
        
        # Count frequencies
        from collections import Counter
        issue_counts = Counter(issues)
        
        # Return most common issues
        return [issue for issue, _ in issue_counts.most_common(5)]
    
    async def learn_from_execution(
        self,
        agent_role: str,
        task_category: str,
        result: Dict[str, Any],
        performance_metrics: Dict[str, float]
    ):
        """
        Learn from execution results to improve future prompts
        This is how the system gets better over time
        """
        genome_key = f"{agent_role}:{task_category}"
        
        # Record performance
        success = performance_metrics.get("validation_score", 0) > 0.7
        self.performance_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "genome_key": genome_key,
            "success": success,
            "metrics": performance_metrics,
            "result_summary": {
                "has_code": bool(result.get("code")),
                "has_tests": bool(result.get("tests")),
                "has_docs": bool(result.get("documentation")),
                "errors": result.get("errors", [])
            }
        })
        
        # Update genome performance metrics
        if genome_key in self.active_genomes:
            genome = self.active_genomes[genome_key]
            
            # Update metrics with exponential moving average
            alpha = 0.1
            for metric, value in performance_metrics.items():
                current = genome.performance_metrics.get(metric, 0.5)
                genome.performance_metrics[metric] = (1 - alpha) * current + alpha * value
            
            # Update principle success rates
            for principle in genome.principles:
                self.principle_library.record_principle_usage(principle, success)
            
            # If this was an exceptional result, save it as an example
            if performance_metrics.get("validation_score", 0) > 0.95:
                example = {
                    "code": result.get("code", ""),
                    "explanation": f"High-quality solution for {task_category}",
                    "score": performance_metrics["validation_score"]
                }
                genome.examples.append(example)
                # Keep only the best 5 examples
                genome.examples = sorted(
                    genome.examples, 
                    key=lambda x: x.get("score", 0), 
                    reverse=True
                )[:5]
            
            # Save updated genome
            self._save_genome(genome_key, genome)
    
    def _save_genome(self, key: str, genome: PromptGenome):
        """Save genome to persistent storage"""
        filepath = Path(self.genome_storage_path) / f"{key}.json"
        try:
            with open(filepath, 'w') as f:
                f.write(genome.to_json())
            logger.info(f"Saved genome: {key}")
        except Exception as e:
            logger.error(f"Failed to save genome {key}: {e}")
    
    async def evolve_population(self, top_n: int = 5):
        """
        Evolve the population of genomes based on performance
        This implements genetic algorithm concepts
        """
        if len(self.active_genomes) < 2:
            return
        
        # Sort genomes by fitness
        genome_fitness = [
            (key, genome, genome.fitness_score())
            for key, genome in self.active_genomes.items()
        ]
        genome_fitness.sort(key=lambda x: x[2], reverse=True)
        
        # Keep top performers
        new_population = {}
        for key, genome, fitness in genome_fitness[:top_n]:
            new_population[key] = genome
        
        # Create offspring from top performers
        for i in range(min(5, len(genome_fitness) - top_n)):
            # Select parents
            parent1_key, parent1, _ = genome_fitness[i % top_n]
            parent2_key, parent2, _ = genome_fitness[(i + 1) % top_n]
            
            # Create offspring
            offspring = parent1.crossover(parent2)
            
            # Mutate offspring
            offspring = offspring.mutate("add_principle")
            
            # Create new key for offspring
            offspring_key = f"{parent1_key.split(':')[0]}:{parent1_key.split(':')[1]}_evolved_{i}"
            new_population[offspring_key] = offspring
        
        # Update population
        self.active_genomes = new_population
        
        # Save all genomes
        for key, genome in self.active_genomes.items():
            self._save_genome(key, genome)
    
    def get_best_genome_for_role(self, agent_role: str) -> Optional[PromptGenome]:
        """Get the best performing genome for a specific role"""
        role_genomes = [
            (key, genome) for key, genome in self.active_genomes.items()
            if key.startswith(f"{agent_role}:")
        ]
        
        if not role_genomes:
            return None
        
        # Sort by fitness
        role_genomes.sort(key=lambda x: x[1].fitness_score(), reverse=True)
        return role_genomes[0][1]
    
    def get_evolution_report(self) -> Dict[str, Any]:
        """Generate a report on genome evolution and performance"""
        report = {
            "total_genomes": len(self.active_genomes),
            "total_executions": len(self.performance_history),
            "genomes_by_role": {},
            "top_principles": [],
            "evolution_strategies_used": {},
            "performance_trends": {},
            "average_fitness": 0.0
        }
        
        # Analyze genomes by role
        from collections import defaultdict
        role_counts = defaultdict(int)
        role_fitness = defaultdict(list)
        
        for key, genome in self.active_genomes.items():
            role = key.split(":")[0]
            role_counts[role] += 1
            role_fitness[role].append(genome.fitness_score())
        
        for role, count in role_counts.items():
            report["genomes_by_role"][role] = {
                "count": count,
                "avg_fitness": sum(role_fitness[role]) / len(role_fitness[role])
            }
        
        # Calculate overall average fitness
        all_fitness_scores = []
        for fitness_list in role_fitness.values():
            all_fitness_scores.extend(fitness_list)
        
        if all_fitness_scores:
            report["average_fitness"] = sum(all_fitness_scores) / len(all_fitness_scores)
        else:
            report["average_fitness"] = 0.0
        
        # Top performing principles
        principle_scores = sorted(
            self.principle_library.principle_success_rate.items(),
            key=lambda x: x[1],
            reverse=True
        )
        # Convert to dictionary format for compatibility
        report["top_principles"] = {
            p: s for p, s in principle_scores[:10]
        }
        
        # Evolution strategy usage
        strategy_counts = defaultdict(int)
        for record in self.performance_history:
            if "evolution_strategy" in record:
                strategy_counts[record["evolution_strategy"]] += 1
        
        report["evolution_strategies_used"] = dict(strategy_counts)
        
        return report


# Convenience function for easy integration
async def create_enhanced_prompt(
    task_description: str,
    agent_role: str,
    context: Dict[str, Any] = None,
    strategy: PromptEvolutionStrategy = PromptEvolutionStrategy.EXPLANATION_DEPTH
) -> str:
    """
    Convenience function to create an enhanced prompt
    This is what the ensemble agents will call
    """
    engineer = MetaPromptEngineer()
    return await engineer.generate_meta_prompt(
        task_description,
        agent_role,
        context or {},
        strategy
    )
