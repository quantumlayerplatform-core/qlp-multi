"""
Principle Library - Universal software engineering principles
Based on timeless wisdom from Deutsch, Popper, and master programmers
"""

from typing import Dict, List, Optional
import random


class PrincipleLibrary:
    """
    A curated library of software engineering principles
    Organized by domain and validated through experience
    """
    
    def __init__(self):
        self.principles = self._initialize_principles()
        self.principle_usage_count = {}
        self.principle_success_rate = {}
    
    def _initialize_principles(self) -> Dict[str, List[str]]:
        """Initialize the comprehensive principle library"""
        return {
            # Fundamental Programming Principles
            "fundamental": [
                "Programs must be written for people to read, and only incidentally for machines to execute - Abelson & Sussman",
                "Make illegal states unrepresentable - Yaron Minsky",
                "Explicit is better than implicit - Zen of Python",
                "Simple things should be simple, complex things should be possible - Alan Kay",
                "The purpose of abstraction is not to be vague, but to create a new semantic level - Dijkstra",
                "Don't repeat yourself (DRY) - but don't abstract prematurely",
                "You aren't gonna need it (YAGNI) - implement when actually needed",
                "Premature optimization is the root of all evil - Knuth",
                "Make it work, make it right, make it fast - Kent Beck",
                "The best code is no code at all - Jeff Atwood"
            ],
            
            # Critical Rationalism (Popper/Deutsch inspired)
            "critical_rationalism": [
                "All knowledge is conjectural - seek better explanations, not certainty",
                "Good explanations are hard to vary while still solving the problem",
                "Error correction is more important than error prevention",
                "Problems are inevitable, problems are soluble - David Deutsch",
                "The beginning of infinity is the ability to create explanations",
                "Seek criticism to improve, not praise to feel good",
                "Every design decision should be open to refutation",
                "The best theories constrain the most while assuming the least",
                "Knowledge grows through conjecture and criticism",
                "Fallibilism: even our best theories might be wrong"
            ],
            
            # Architecture & Design
            "architecture": [
                "High cohesion, low coupling - modules should be focused and independent",
                "Depend on abstractions, not concretions - Dependency Inversion",
                "Open for extension, closed for modification - Open/Closed Principle",
                "Program to interfaces, not implementations",
                "Favor composition over inheritance",
                "Separate concerns at natural boundaries",
                "The architecture should scream its intent - Uncle Bob",
                "Design for deletion, not for reuse - Write code that's easy to delete",
                "Boundaries should be explicit and well-defined",
                "Make the common case fast and the rare case correct"
            ],
            
            # Error Handling & Resilience
            "error_handling": [
                "Fail fast, fail loudly - make errors obvious immediately",
                "Let it crash - Erlang philosophy for fault isolation",
                "Errors should never pass silently unless explicitly silenced",
                "Return errors, don't throw them (where appropriate)",
                "Make error messages helpful - include context and recovery steps",
                "Design for failure - assume everything can and will fail",
                "Defensive programming at boundaries, assertive programming internally",
                "Use type systems to make errors impossible",
                "Partial failure is worse than total failure - fail completely or succeed",
                "Hope is not a strategy - handle errors explicitly"
            ],
            
            # Testing & Quality
            "testing": [
                "Tests are the first users of your code",
                "Test behavior, not implementation",
                "A test should have one reason to fail",
                "Fast tests, slow tests, no tests - in that order",
                "If it's not tested, it's broken - or will be soon",
                "Property-based testing finds bugs unit tests miss",
                "Tests should be deterministic and isolated",
                "The test pyramid: many unit, some integration, few e2e",
                "Test the contract, not the implementation",
                "Make tests so clear they serve as documentation"
            ],
            
            # Security
            "security": [
                "Never trust user input - validate everything",
                "Defense in depth - multiple layers of security",
                "Principle of least privilege - minimal access rights",
                "Fail securely - errors shouldn't reveal sensitive info",
                "Security is not a feature, it's a requirement",
                "Don't roll your own crypto",
                "Validate on the server, convenience on the client",
                "Time attacks are real - use constant-time comparisons",
                "Log security events, but not sensitive data",
                "Assume breach - design to limit damage"
            ],
            
            # Performance & Scalability
            "performance": [
                "Measure, don't guess - profile before optimizing",
                "The fastest code is the code that doesn't run",
                "Cache answers to expensive questions",
                "Do less work - the best optimization",
                "Batch operations when possible",
                "Async all the way down - no blocking operations",
                "Design for horizontal scaling from day one",
                "Denormalize for read performance, normalize for consistency",
                "Use the right data structure for the job",
                "Performance is a feature, not an afterthought"
            ],
            
            # Concurrency & Parallelism
            "concurrency": [
                "Shared mutable state is the root of all evil",
                "Don't communicate by sharing memory; share memory by communicating - Go proverb",
                "Make concurrency explicit, not implicit",
                "Immutability makes concurrency trivial",
                "Use actors for state, channels for communication",
                "Deadlock is worse than livelock is worse than starvation",
                "The actor model: encapsulate state and behavior",
                "Lock-free when possible, fine-grained locks when necessary",
                "Race conditions hide in the gaps between 'check' and 'act'",
                "Concurrency is about structure, parallelism is about execution"
            ],
            
            # API Design
            "api_design": [
                "Make the simple case simple and the complex case possible",
                "Be liberal in what you accept, conservative in what you send - Postel's Law",
                "A good API is hard to misuse",
                "Consistency is more important than perfection",
                "Names matter - be descriptive and consistent",
                "Version your APIs from day one",
                "Idempotency by default - safe to retry",
                "Pagination is not optional for collections",
                "Use standards where they exist (REST, GraphQL, etc)",
                "Document the why, not just the what"
            ],
            
            # Code Quality
            "code_quality": [
                "Leave the code better than you found it - Boy Scout Rule",
                "Code is written once but read many times - optimize for reading",
                "Names should reveal intent",
                "Functions should do one thing well",
                "Comments should explain why, not what",
                "Delete dead code - version control remembers",
                "Refactor mercilessly but with tests",
                "The length of a variable name should be proportional to its scope",
                "Make the code so clear that comments become unnecessary",
                "If you need to comment, consider refactoring instead"
            ],
            
            # Meta-Programming
            "meta_programming": [
                "Programs writing programs is the ultimate abstraction",
                "Code generation should be deterministic and debuggable",
                "Metaprogramming is powerful - use it sparingly",
                "Generated code should be as readable as hand-written code",
                "Build tools to build tools",
                "DSLs should be minimal and composable",
                "Reflection is a sharp knife - handle with care",
                "Compile-time computation is free runtime performance",
                "Macros should be hygienic - no surprising side effects",
                "The best framework is no framework - libraries over frameworks"
            ],
            
            # Distributed Systems
            "distributed_systems": [
                "The network is reliable - said no one ever",
                "CAP theorem: Choose at most two of Consistency, Availability, Partition tolerance",
                "Eventual consistency is often good enough",
                "Design for partition tolerance - networks will split",
                "Clocks lie - use logical clocks for ordering",
                "At-least-once + idempotency = exactly-once semantics",
                "Distributed transactions are hard - avoid when possible",
                "Service discovery should be dynamic",
                "Circuit breakers prevent cascade failures",
                "Observability is not optional in distributed systems"
            ]
        }
    
    def get_principles_for_task(self, task_categories: List[str]) -> List[str]:
        """Get relevant principles for given task categories"""
        selected_principles = []
        
        # Always include some fundamental principles
        selected_principles.extend(random.sample(self.principles["fundamental"], 3))
        selected_principles.extend(random.sample(self.principles["critical_rationalism"], 2))
        
        # Add category-specific principles
        for category in task_categories:
            if category in self.principles:
                # Select based on past success rate if available
                category_principles = self.principles[category]
                scored_principles = []
                
                for principle in category_principles:
                    success_rate = self.principle_success_rate.get(principle, 0.5)
                    usage_count = self.principle_usage_count.get(principle, 0)
                    
                    # Exploration vs exploitation
                    if usage_count < 5:
                        # Explore lesser-used principles
                        score = 0.7 + random.random() * 0.3
                    else:
                        # Exploit successful principles
                        score = success_rate + random.random() * 0.2
                    
                    scored_principles.append((score, principle))
                
                # Sort by score and take top principles
                scored_principles.sort(reverse=True, key=lambda x: x[0])
                selected_principles.extend([p for _, p in scored_principles[:3]])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_principles = []
        for principle in selected_principles:
            if principle not in seen:
                seen.add(principle)
                unique_principles.append(principle)
        
        return unique_principles[:15]  # Return top 15 principles
    
    def record_principle_usage(self, principle: str, success: bool):
        """Record usage of a principle and whether it led to success"""
        # Update usage count
        self.principle_usage_count[principle] = self.principle_usage_count.get(principle, 0) + 1
        
        # Update success rate (exponential moving average)
        alpha = 0.1  # Learning rate
        current_rate = self.principle_success_rate.get(principle, 0.5)
        new_value = 1.0 if success else 0.0
        self.principle_success_rate[principle] = (1 - alpha) * current_rate + alpha * new_value
    
    def get_contrarian_principles(self) -> List[str]:
        """Get principles that challenge conventional wisdom"""
        contrarian = [
            "The best code is the code you don't write",
            "Duplication is far cheaper than the wrong abstraction - Sandi Metz",
            "Design patterns are a language smell - Paul Graham",
            "Microservices are a solution in search of a problem for most teams",
            "You probably don't need a database - files might be enough",
            "Monoliths are not bad - distributed systems are hard",
            "ORMs are a leaky abstraction - learn SQL",
            "Inheritance is rarely the answer - prefer composition",
            "Comments are a code smell - refactor for clarity instead",
            "100% test coverage is a vanity metric - test what matters"
        ]
        return random.sample(contrarian, 3)
    
    def get_principles_by_thinker(self, thinker: str) -> List[str]:
        """Get principles associated with specific thinkers"""
        thinker_principles = {
            "deutsch": [
                "Problems are inevitable, problems are soluble",
                "Good explanations are hard to vary",
                "The beginning of infinity is the ability to create explanations",
                "Error correction is more important than error prevention",
                "All knowledge is conjectural"
            ],
            "popper": [
                "All knowledge grows through conjecture and refutation",
                "Seek criticism to improve, not praise to feel good",
                "The best theories constrain the most while assuming the least",
                "Fallibilism: even our best theories might be wrong",
                "Critical rationalism: reason critically about everything"
            ],
            "dijkstra": [
                "Simplicity is prerequisite for reliability",
                "The purpose of abstraction is not to be vague, but to create a new semantic level",
                "Program testing can show the presence of bugs, but never their absence",
                "The question of whether machines can think is as relevant as whether submarines can swim",
                "Elegance is not optional"
            ],
            "kay": [
                "Simple things should be simple, complex things should be possible",
                "The best way to predict the future is to invent it",
                "Programming is a pop culture - it spreads much faster than education",
                "Most software is not engineered, it's written",
                "OOP is about messages, not objects"
            ]
        }
        
        return thinker_principles.get(thinker.lower(), [])
    
    def evolve_principle(self, principle: str, context: str) -> str:
        """Evolve a principle based on context and experience"""
        # This is where we'd apply ML/AI to evolve principles
        # For now, simple rule-based evolution
        
        evolutions = {
            "simple": f"{principle} - but remember, simple is not easy",
            "complex": f"{principle} - balanced with the need for completeness",
            "performance": f"{principle} - without sacrificing readability",
            "security": f"{principle} - with defense in depth",
            "testing": f"{principle} - with property-based testing where applicable"
        }
        
        for key, evolution in evolutions.items():
            if key in context.lower():
                return evolution
        
        return principle
