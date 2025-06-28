"""
Prompt Genome - The DNA of self-improving prompts
Based on evolutionary epistemology and critical rationalism
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


@dataclass
class PromptGenome:
    """
    Represents the 'DNA' of a prompt - its core components that can evolve
    
    Following Deutsch's principle: Good explanations are hard to vary
    Each component should be essential to the prompt's function
    """
    
    # Core objectives - what the prompt aims to achieve
    objectives: List[str] = field(default_factory=list)
    
    # Constraints - boundaries that must not be violated
    constraints: List[str] = field(default_factory=list)
    
    # Principles - universal truths that guide the solution
    principles: List[str] = field(default_factory=list)
    
    # Examples - few-shot learning samples
    examples: List[Dict[str, Any]] = field(default_factory=list)
    
    # Meta-instructions - instructions about how to think
    meta_instructions: List[str] = field(default_factory=list)
    
    # Critique criteria - how to evaluate success
    critique_criteria: List[str] = field(default_factory=list)
    
    # Evolution history - track changes over time
    evolution_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance metrics - track effectiveness
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Mutation rate - how much to vary during evolution
    mutation_rate: float = 0.1
    
    def to_json(self) -> str:
        """Serialize genome to JSON"""
        return json.dumps({
            "objectives": self.objectives,
            "constraints": self.constraints,
            "principles": self.principles,
            "examples": self.examples,
            "meta_instructions": self.meta_instructions,
            "critique_criteria": self.critique_criteria,
            "evolution_history": self.evolution_history,
            "performance_metrics": self.performance_metrics,
            "mutation_rate": self.mutation_rate
        }, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'PromptGenome':
        """Deserialize genome from JSON"""
        data = json.loads(json_str)
        return cls(**data)
    
    def mutate(self, mutation_type: str = "random") -> 'PromptGenome':
        """Create a mutated version of this genome"""
        import random
        
        mutated = PromptGenome(
            objectives=self.objectives.copy(),
            constraints=self.constraints.copy(),
            principles=self.principles.copy(),
            examples=self.examples.copy(),
            meta_instructions=self.meta_instructions.copy(),
            critique_criteria=self.critique_criteria.copy(),
            evolution_history=self.evolution_history.copy(),
            performance_metrics=self.performance_metrics.copy(),
            mutation_rate=self.mutation_rate
        )
        
        # Record mutation
        mutated.evolution_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": "mutation",
            "mutation_type": mutation_type
        })
        
        if mutation_type == "add_principle":
            # Add a new principle from the library
            new_principle = self._get_random_principle()
            if new_principle and new_principle not in mutated.principles:
                mutated.principles.append(new_principle)
                
        elif mutation_type == "strengthen_constraint":
            # Make a constraint more specific
            if mutated.constraints and random.random() < self.mutation_rate:
                idx = random.randint(0, len(mutated.constraints) - 1)
                mutated.constraints[idx] = self._strengthen_constraint(mutated.constraints[idx])
                
        elif mutation_type == "add_meta_instruction":
            # Add a new way of thinking
            new_instruction = self._generate_meta_instruction()
            if new_instruction:
                mutated.meta_instructions.append(new_instruction)
                
        elif mutation_type == "refine_objective":
            # Make an objective more specific
            if mutated.objectives and random.random() < self.mutation_rate:
                idx = random.randint(0, len(mutated.objectives) - 1)
                mutated.objectives[idx] = self._refine_objective(mutated.objectives[idx])
        
        return mutated
    
    def crossover(self, other: 'PromptGenome') -> 'PromptGenome':
        """Create offspring by combining two genomes"""
        import random
        
        # Take best performing elements from each parent
        offspring = PromptGenome()
        
        # Objectives - take union of high-performing objectives
        offspring.objectives = list(set(self.objectives + other.objectives))
        
        # Constraints - keep all (safety first)
        offspring.constraints = list(set(self.constraints + other.constraints))
        
        # Principles - weighted by performance
        self_weight = self.performance_metrics.get('avg_score', 0.5)
        other_weight = other.performance_metrics.get('avg_score', 0.5)
        
        if self_weight + other_weight > 0:
            self_ratio = self_weight / (self_weight + other_weight)
            principles_count = len(self.principles) + len(other.principles)
            self_count = int(principles_count * self_ratio)
            
            offspring.principles = (
                random.sample(self.principles, min(self_count, len(self.principles))) +
                random.sample(other.principles, min(principles_count - self_count, len(other.principles)))
            )
        
        # Meta instructions - combine and deduplicate
        offspring.meta_instructions = list(set(self.meta_instructions + other.meta_instructions))
        
        # Critique criteria - union
        offspring.critique_criteria = list(set(self.critique_criteria + other.critique_criteria))
        
        # Record lineage
        offspring.evolution_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": "crossover",
            "parents": ["parent1", "parent2"],  # Would use actual IDs
            "parent_scores": [self_weight, other_weight]
        })
        
        return offspring
    
    def fitness_score(self) -> float:
        """Calculate overall fitness of this genome"""
        metrics = self.performance_metrics
        
        # Weighted combination of metrics
        weights = {
            'validation_score': 0.3,
            'confidence_score': 0.2,
            'execution_time': 0.1,  # Lower is better
            'error_rate': 0.2,      # Lower is better
            'completeness': 0.2
        }
        
        score = 0.0
        for metric, weight in weights.items():
            value = metrics.get(metric, 0.5)
            
            # Invert metrics where lower is better
            if metric in ['execution_time', 'error_rate']:
                value = 1.0 - min(value, 1.0)
            
            score += value * weight
        
        return score
    
    def _get_random_principle(self) -> Optional[str]:
        """Get a random principle from the library"""
        # This would pull from the PrincipleLibrary
        principles = [
            "Make illegal states unrepresentable",
            "Fail fast with clear error messages",
            "Explicit is better than implicit",
            "Composition over inheritance",
            "Single source of truth"
        ]
        import random
        return random.choice(principles)
    
    def _strengthen_constraint(self, constraint: str) -> str:
        """Make a constraint more specific"""
        strengtheners = {
            "must be": "must always be",
            "should": "must",
            "avoid": "never",
            "minimize": "eliminate",
            "when possible": ""
        }
        
        for weak, strong in strengtheners.items():
            if weak in constraint:
                return constraint.replace(weak, strong)
        
        return constraint + " (strictly enforced)"
    
    def _generate_meta_instruction(self) -> str:
        """Generate a new meta-cognitive instruction"""
        templates = [
            "Before implementing, consider: {}",
            "Validate your assumption that {}",
            "Question whether {}",
            "Ensure that {}",
            "Double-check {}"
        ]
        
        aspects = [
            "the solution handles all edge cases",
            "the design is the simplest possible",
            "error messages are helpful to users",
            "the code is self-documenting",
            "performance requirements are met"
        ]
        
        import random
        template = random.choice(templates)
        aspect = random.choice(aspects)
        return template.format(aspect)
    
    def _refine_objective(self, objective: str) -> str:
        """Make an objective more specific and measurable"""
        refinements = {
            "good": "excellent with measurable metrics",
            "fast": "with <100ms p99 latency",
            "secure": "following OWASP Top 10 guidelines",
            "scalable": "handling 10,000+ concurrent requests",
            "maintainable": "with <10 cognitive complexity score"
        }
        
        for vague, specific in refinements.items():
            if vague in objective.lower():
                return objective.replace(vague, specific)
        
        # Add measurement if not present
        if not any(char.isdigit() for char in objective):
            return objective + " (with quantifiable metrics)"
        
        return objective
