"""
Chain of Thought reasoning display for QuantumLayer CLI
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.table import Table
from rich import box

console = Console()

@dataclass
class ThoughtStep:
    """Represents a single step in the reasoning chain"""
    category: str
    thought: str
    details: List[str]
    confidence: float = 1.0
    timestamp: float = 0.0

class ChainOfThought:
    """Manages and displays chain of thought reasoning"""
    
    def __init__(self):
        self.steps: List[ThoughtStep] = []
        self.current_category = None
        self.start_time = time.time()
        
    def add_step(self, category: str, thought: str, details: List[str] = None, confidence: float = 1.0):
        """Add a reasoning step"""
        step = ThoughtStep(
            category=category,
            thought=thought,
            details=details or [],
            confidence=confidence,
            timestamp=time.time() - self.start_time
        )
        self.steps.append(step)
        
    def create_tree(self) -> Tree:
        """Create a rich tree visualization of the reasoning chain"""
        tree = Tree("💭 [bold cyan]Chain of Thought[/]")
        
        current_branch = None
        for step in self.steps:
            if step.category != self.current_category:
                current_branch = tree.add(f"[bold yellow]{step.category}[/]")
                self.current_category = step.category
            
            # Add main thought
            thought_text = Text(step.thought)
            if step.confidence < 0.7:
                thought_text.stylize("dim red")
            elif step.confidence < 0.9:
                thought_text.stylize("yellow")
            else:
                thought_text.stylize("green")
            
            step_branch = current_branch.add(thought_text)
            
            # Add details
            for detail in step.details:
                step_branch.add(f"[dim]└─ {detail}[/]")
        
        return tree
    
    def create_panel(self) -> Panel:
        """Create a panel with the reasoning chain"""
        tree = self.create_tree()
        return Panel(
            tree,
            title="[bold]🧠 AI Reasoning Process[/]",
            border_style="blue",
            box=box.ROUNDED,
            padding=(1, 2)
        )

# Predefined reasoning patterns for different project types
REASONING_PATTERNS = {
    "api": [
        ("Understanding Requirements", [
            "Analyzing API scope and endpoints",
            "Identifying data models needed",
            "Determining authentication requirements"
        ]),
        ("Selecting Architecture", [
            "Choosing framework (FastAPI/Express/etc)",
            "Database selection (SQL vs NoSQL)",
            "Caching strategy evaluation"
        ]),
        ("Planning Implementation", [
            "Endpoint structure design",
            "Middleware configuration",
            "Error handling strategy"
        ])
    ],
    "web": [
        ("Understanding Requirements", [
            "Analyzing UI/UX needs",
            "Identifying component hierarchy",
            "State management requirements"
        ]),
        ("Selecting Tech Stack", [
            "Frontend framework selection",
            "CSS framework evaluation",
            "Build tool configuration"
        ]),
        ("Planning Implementation", [
            "Component structure design",
            "Routing strategy",
            "API integration approach"
        ])
    ],
    "cli": [
        ("Understanding Requirements", [
            "Command structure analysis",
            "Input/output format design",
            "User interaction flow"
        ]),
        ("Tool Selection", [
            "CLI framework evaluation",
            "Argument parsing strategy",
            "Configuration management"
        ]),
        ("Implementation Planning", [
            "Command hierarchy design",
            "Error handling approach",
            "Testing strategy"
        ])
    ]
}

def detect_project_type(description: str) -> str:
    """Detect project type from description"""
    description_lower = description.lower()
    
    if any(word in description_lower for word in ["api", "rest", "graphql", "endpoint"]):
        return "api"
    elif any(word in description_lower for word in ["web", "website", "frontend", "ui", "dashboard"]):
        return "web"
    elif any(word in description_lower for word in ["cli", "command", "terminal", "console"]):
        return "cli"
    else:
        return "general"

def generate_reasoning_chain(description: str, language: str) -> ChainOfThought:
    """Generate a reasoning chain based on the project description"""
    chain = ChainOfThought()
    project_type = detect_project_type(description)
    
    # Initial understanding
    chain.add_step(
        "🔍 Analyzing Request",
        f"Understanding: '{description}'",
        [
            f"Project type detected: {project_type}",
            f"Language preference: {language}",
            f"Complexity assessment: medium"
        ],
        confidence=0.95
    )
    
    # Tech stack reasoning
    if project_type == "api":
        if language == "python":
            chain.add_step(
                "🛠️ Selecting Tech Stack",
                "Choosing FastAPI for modern Python API",
                [
                    "FastAPI: High performance, auto-documentation",
                    "SQLAlchemy: Robust ORM with migrations",
                    "Pydantic: Data validation built-in",
                    "Alternative considered: Flask (simpler but less features)"
                ],
                confidence=0.92
            )
        elif language == "javascript":
            chain.add_step(
                "🛠️ Selecting Tech Stack",
                "Choosing Express.js for Node.js API",
                [
                    "Express: Mature, flexible framework",
                    "Sequelize: Feature-rich ORM",
                    "Joi: Schema validation",
                    "Alternative considered: Fastify (faster but less ecosystem)"
                ],
                confidence=0.88
            )
    
    # Architecture decisions
    chain.add_step(
        "🏗️ Architecture Design",
        "Planning modular architecture",
        [
            "Separation of concerns with layers",
            "Repository pattern for data access",
            "Service layer for business logic",
            "Controller layer for HTTP handling"
        ],
        confidence=0.90
    )
    
    # Security considerations
    chain.add_step(
        "🔒 Security Planning",
        "Implementing security best practices",
        [
            "JWT for stateless authentication",
            "Input validation on all endpoints",
            "Rate limiting for API protection",
            "CORS configuration for web clients"
        ],
        confidence=0.94
    )
    
    # Testing strategy
    chain.add_step(
        "🧪 Testing Strategy",
        "Comprehensive test coverage planned",
        [
            "Unit tests for business logic",
            "Integration tests for API endpoints",
            "Test fixtures for database",
            "CI/CD pipeline configuration"
        ],
        confidence=0.91
    )
    
    # Final optimization
    chain.add_step(
        "⚡ Optimization",
        "Performance and scalability considerations",
        [
            "Database indexing strategy",
            "Caching layer implementation",
            "Async operations where beneficial",
            "Container-ready deployment"
        ],
        confidence=0.87
    )
    
    return chain

async def display_reasoning_live(chain: ChainOfThought, delay: float = 0.5):
    """Display reasoning chain with live updates"""
    with Live(chain.create_panel(), refresh_per_second=4, console=console) as live:
        displayed_steps = 0
        temp_chain = ChainOfThought()
        
        for step in chain.steps:
            temp_chain.steps = chain.steps[:displayed_steps + 1]
            live.update(temp_chain.create_panel())
            displayed_steps += 1
            await asyncio.sleep(delay)

def create_reasoning_summary(chain: ChainOfThought) -> Table:
    """Create a summary table of the reasoning process"""
    table = Table(title="🎯 Decision Summary", show_header=True, box=box.SIMPLE)
    table.add_column("Category", style="cyan")
    table.add_column("Decision", style="white")
    table.add_column("Confidence", justify="center")
    
    # Group steps by category
    category_decisions = {}
    for step in chain.steps:
        if step.category not in category_decisions:
            category_decisions[step.category] = []
        category_decisions[step.category].append((step.thought, step.confidence))
    
    for category, decisions in category_decisions.items():
        for i, (thought, confidence) in enumerate(decisions):
            conf_str = f"{confidence:.0%}"
            if confidence >= 0.9:
                conf_style = "[green]" + conf_str + "[/]"
            elif confidence >= 0.7:
                conf_style = "[yellow]" + conf_str + "[/]"
            else:
                conf_style = "[red]" + conf_str + "[/]"
            
            table.add_row(
                category if i == 0 else "",
                thought,
                conf_style
            )
    
    return table