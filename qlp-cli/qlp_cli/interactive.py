"""
Interactive mode for QuantumLayer CLI
"""

import asyncio
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.syntax import Syntax
from rich import box

from .api_client import QLPClient


class InteractiveSession:
    """Manages an interactive conversation session"""
    
    def __init__(self, client: QLPClient, console: Console):
        self.client = client
        self.console = console
        self.session_id = str(uuid.uuid4())
        self.context = {
            "language": None,
            "framework": None,
            "features": [],
            "description_parts": []
        }
        self.commands = {
            "help": self._show_help,
            "clear": self._clear_context,
            "context": self._show_context,
            "generate": self._generate_from_context,
            "examples": self._show_examples,
            "tips": self._show_tips,
            "exit": self._exit,
            "quit": self._exit
        }
    
    async def run(self):
        """Run the interactive session"""
        
        self._show_welcome()
        
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold cyan]You[/]")
                
                if not user_input.strip():
                    continue
                
                # Check for commands
                if user_input.lower() in self.commands:
                    result = await self.commands[user_input.lower()]()
                    if result == "exit":
                        break
                    continue
                
                # Process as project description
                await self._process_input(user_input)
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'exit' to quit.[/]")
            except Exception as e:
                self.console.print(f"[red]Error:[/] {e}")
    
    def _show_welcome(self):
        """Show welcome message"""
        welcome_text = """
# Welcome to QuantumLayer Interactive Mode! 🧠

I'll help you build a complete software system through conversation.

## Quick Start:
- Describe what you want to build
- I'll ask clarifying questions
- When ready, I'll generate the complete project

## Commands:
- **help** - Show available commands
- **examples** - See example projects
- **context** - View current project context
- **generate** - Generate with current context
- **clear** - Start over
- **exit** - Leave interactive mode
        """
        
        self.console.print(Markdown(welcome_text))
    
    async def _process_input(self, user_input: str):
        """Process user input as part of project description"""
        
        # Add to context
        self.context["description_parts"].append(user_input)
        
        # Analyze input for key information
        analysis = self._analyze_input(user_input)
        
        # Update context
        if analysis["language"]:
            self.context["language"] = analysis["language"]
        if analysis["framework"]:
            self.context["framework"] = analysis["framework"]
        if analysis["features"]:
            self.context["features"].extend(analysis["features"])
        
        # Generate response
        response = self._generate_response(analysis)
        self.console.print(f"\n[bold green]QL:[/] {response}")
        
        # Check if we have enough info to generate
        if self._has_enough_context():
            self.console.print("\n[dim]💡 I have enough information. Type 'generate' when ready![/]")
    
    def _analyze_input(self, text: str) -> Dict[str, Any]:
        """Analyze user input for project details"""
        
        text_lower = text.lower()
        
        # Detect programming language
        language = None
        languages = {
            "python": ["python", "django", "flask", "fastapi"],
            "javascript": ["javascript", "js", "node", "react", "vue", "angular"],
            "typescript": ["typescript", "ts"],
            "go": ["go", "golang"],
            "java": ["java", "spring"]
        }
        
        for lang, keywords in languages.items():
            if any(kw in text_lower for kw in keywords):
                language = lang
                break
        
        # Detect framework
        framework = None
        frameworks = {
            "fastapi": "fastapi",
            "django": "django",
            "flask": "flask",
            "express": "express",
            "react": "react",
            "vue": "vue",
            "angular": "angular",
            "spring": "spring"
        }
        
        for fw, name in frameworks.items():
            if fw in text_lower:
                framework = name
                break
        
        # Detect features
        features = []
        feature_keywords = {
            "api": ["api", "rest", "graphql"],
            "database": ["database", "db", "postgres", "mysql", "mongodb"],
            "auth": ["auth", "authentication", "login", "users"],
            "frontend": ["frontend", "ui", "interface"],
            "testing": ["test", "testing", "tdd"],
            "docker": ["docker", "container"],
            "ci/cd": ["ci/cd", "pipeline", "deployment"]
        }
        
        for feature, keywords in feature_keywords.items():
            if any(kw in text_lower for kw in keywords):
                features.append(feature)
        
        return {
            "language": language,
            "framework": framework,
            "features": features,
            "has_detail": len(text.split()) > 10
        }
    
    def _generate_response(self, analysis: Dict[str, Any]) -> str:
        """Generate an appropriate response based on analysis"""
        
        if not self.context["description_parts"]:
            return "What would you like to build today?"
        
        # Build response based on what we know/need
        if not self.context["language"] and not analysis["language"]:
            return "What programming language would you prefer? (Python, JavaScript, Go, etc.)"
        
        if analysis["has_detail"]:
            missing = []
            if "database" not in self.context["features"]:
                missing.append("database")
            if "auth" not in self.context["features"] and "api" in self.context["features"]:
                missing.append("authentication")
            
            if missing:
                return f"Great! Should I include {' and '.join(missing)}?"
            else:
                return "That sounds like a solid project! Any other features you'd like to add?"
        
        return "Tell me more about what this system should do."
    
    def _has_enough_context(self) -> bool:
        """Check if we have enough context to generate"""
        full_description = " ".join(self.context["description_parts"])
        return (
            len(full_description.split()) > 15 and
            (self.context["language"] is not None or len(self.context["features"]) > 2)
        )
    
    async def _show_help(self):
        """Show help information"""
        
        table = Table(title="Available Commands", box=box.ROUNDED)
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")
        
        commands = [
            ("help", "Show this help message"),
            ("examples", "See example projects you can build"),
            ("context", "View current project context"),
            ("generate", "Generate project with current context"),
            ("clear", "Clear context and start over"),
            ("tips", "Show tips for better results"),
            ("exit/quit", "Leave interactive mode")
        ]
        
        for cmd, desc in commands:
            table.add_row(cmd, desc)
        
        self.console.print(table)
    
    async def _show_examples(self):
        """Show example projects"""
        
        examples = """
## Example Projects You Can Build:

### 🌐 **Web Applications**
- "Build a task management API with user authentication"
- "Create a blog platform with React frontend and Node.js backend"
- "E-commerce site with payment integration"

### 📱 **Mobile Backends**
- "REST API for a social media app with real-time messaging"
- "Food delivery app backend with order tracking"

### 🤖 **Automation & Tools**
- "CLI tool for managing AWS resources"
- "GitHub webhook processor for CI/CD"
- "Web scraper with scheduling and notifications"

### 📊 **Data Applications**
- "Real-time analytics dashboard"
- "ML model serving API with versioning"
- "ETL pipeline for data warehouse"

### 🎮 **Fun Projects**
- "Multiplayer game server with WebSocket"
- "Discord bot with moderation features"
- "URL shortener with analytics"
        """
        
        self.console.print(Markdown(examples))
    
    async def _show_tips(self):
        """Show tips for better results"""
        
        tips = """
## 💡 Tips for Better Results:

1. **Be Specific** - Instead of "build an app", say "build a task management app with user accounts"

2. **Mention Key Features** - Include important requirements like "with authentication", "using PostgreSQL", "include API documentation"

3. **Specify Preferences** - If you have a preferred language or framework, mention it

4. **Think Production** - Mention if you need Docker, tests, CI/CD, or deployment configs

5. **Iterate** - Start simple and add features through conversation

### Example of a Great Description:
> "Build a REST API for a blog platform using Python FastAPI. Include user authentication with JWT, PostgreSQL database, post CRUD operations, comments system, and API documentation. Add Docker configuration and pytest tests."
        """
        
        self.console.print(Markdown(tips))
    
    async def _show_context(self):
        """Show current project context"""
        
        self.console.print(Panel(
            f"[bold]Full Description:[/]\n{' '.join(self.context['description_parts'])}\n\n"
            f"[bold]Language:[/] {self.context['language'] or 'Not specified'}\n"
            f"[bold]Framework:[/] {self.context['framework'] or 'Not specified'}\n"
            f"[bold]Features:[/] {', '.join(self.context['features']) or 'None detected'}",
            title="Current Project Context",
            border_style="cyan"
        ))
    
    async def _generate_from_context(self):
        """Generate project from current context"""
        
        if not self.context["description_parts"]:
            self.console.print("[yellow]No project description yet. Tell me what you'd like to build![/]")
            return
        
        full_description = " ".join(self.context["description_parts"])
        
        # Enhance description with detected context
        if self.context["language"]:
            full_description += f" using {self.context['language']}"
        if self.context["framework"]:
            full_description += f" with {self.context['framework']}"
        if self.context["features"]:
            full_description += f" including {', '.join(self.context['features'])}"
        
        self.console.print(f"\n[cyan]Generating:[/] {full_description}\n")
        
        # Import and use the generation function
        from .main import _generate_async
        
        try:
            await _generate_async(
                client=self.client,
                description=full_description,
                language=self.context["language"] or "auto",
                output=None,
                deploy=None,
                github=False
            )
            
            # Ask if they want to continue
            another = Prompt.ask("\nWould you like to build something else?", choices=["yes", "no"], default="no")
            if another == "yes":
                await self._clear_context()
            else:
                return "exit"
                
        except Exception as e:
            self.console.print(f"[red]Generation failed:[/] {e}")
    
    async def _clear_context(self):
        """Clear the current context"""
        self.context = {
            "language": None,
            "framework": None,
            "features": [],
            "description_parts": []
        }
        self.console.print("[green]Context cleared! Let's start fresh.[/]")
    
    async def _exit(self):
        """Exit interactive mode"""
        self.console.print("\n[cyan]Thanks for using QuantumLayer! Happy coding! 🚀[/]")
        return "exit"