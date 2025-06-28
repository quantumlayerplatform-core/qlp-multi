"""
Debug utilities for QLP development
"""

import sys
import asyncio
from typing import Any, Dict, List
from datetime import datetime
import json
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich import print as rprint

# For visual debugging in terminal
console = Console()


def visual_breakpoint(locals_dict: Dict[str, Any] = None, message: str = ""):
    """
    Enhanced breakpoint with visual display of variables
    
    Usage:
        visual_breakpoint(locals(), "Checking agent response")
    """
    console.rule(f"[red]🔍 DEBUG BREAKPOINT[/red] {message}")
    
    if locals_dict:
        table = Table(title="Local Variables")
        table.add_column("Variable", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Value", style="green")
        
        for name, value in locals_dict.items():
            if not name.startswith('__'):
                value_str = str(value)[:100]
                if len(str(value)) > 100:
                    value_str += "..."
                table.add_row(name, type(value).__name__, value_str)
        
        console.print(table)
    
    console.print("\n[yellow]Press Enter to continue, or 'q' to quit...[/yellow]")
    response = input()
    if response.lower() == 'q':
        sys.exit(0)


def debug_async_task(coro):
    """
    Decorator to debug async functions
    
    Usage:
        @debug_async_task
        async def my_function():
            ...
    """
    async def wrapper(*args, **kwargs):
        console.print(f"\n[blue]→ Entering {coro.__name__}[/blue]")
        console.print(f"  Args: {args}")
        console.print(f"  Kwargs: {kwargs}")
        
        start_time = datetime.now()
        try:
            result = await coro(*args, **kwargs)
            elapsed = (datetime.now() - start_time).total_seconds()
            console.print(f"[green]← Exiting {coro.__name__} (took {elapsed:.2f}s)[/green]")
            console.print(f"  Result: {str(result)[:200]}")
            return result
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            console.print(f"[red]✗ Exception in {coro.__name__} (after {elapsed:.2f}s)[/red]")
            console.print(f"  Error: {str(e)}")
            raise
    
    return wrapper


def print_json(data: Any, title: str = "JSON Data"):
    """Pretty print JSON data with syntax highlighting"""
    console.rule(f"[cyan]{title}[/cyan]")
    json_str = json.dumps(data, indent=2)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
    console.print(syntax)


def print_code(code: str, language: str = "python", title: str = "Code"):
    """Pretty print code with syntax highlighting"""
    console.rule(f"[cyan]{title}[/cyan]")
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    console.print(syntax)


class AsyncDebugger:
    """
    Context manager for debugging async code blocks
    
    Usage:
        async with AsyncDebugger("Processing request"):
            result = await some_async_operation()
    """
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        
    async def __aenter__(self):
        self.start_time = datetime.now()
        console.print(f"\n[blue]▶ {self.name} started[/blue]")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if exc_type:
            console.print(f"[red]✗ {self.name} failed after {elapsed:.2f}s[/red]")
            console.print(f"  Error: {exc_val}")
        else:
            console.print(f"[green]✓ {self.name} completed in {elapsed:.2f}s[/green]")


def trace_llm_calls(func):
    """
    Decorator to trace LLM API calls
    
    Usage:
        @trace_llm_calls
        async def chat_completion(...):
            ...
    """
    async def wrapper(*args, **kwargs):
        call_id = datetime.now().strftime("%H%M%S%f")[:10]
        
        # Extract key info
        messages = kwargs.get('messages', [])
        model = kwargs.get('model', 'unknown')
        
        console.print(f"\n[magenta]🤖 LLM Call {call_id}[/magenta]")
        console.print(f"  Model: {model}")
        console.print(f"  Messages: {len(messages)}")
        
        if messages and len(messages) > 0:
            last_message = messages[-1]
            console.print(f"  Last message: {last_message.get('content', '')[:100]}...")
        
        start_time = datetime.now()
        try:
            result = await func(*args, **kwargs)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            console.print(f"[green]✓ LLM Response {call_id} ({elapsed:.2f}s)[/green]")
            if isinstance(result, dict):
                tokens = result.get('usage', {})
                console.print(f"  Tokens: {tokens}")
                content = result.get('content', '')[:100]
                console.print(f"  Response: {content}...")
            
            return result
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            console.print(f"[red]✗ LLM Error {call_id} ({elapsed:.2f}s)[/red]")
            console.print(f"  Error: {str(e)}")
            raise
    
    return wrapper


# Example usage in code:
if __name__ == "__main__":
    # Test visual breakpoint
    test_var = {"name": "test", "value": 42}
    test_list = [1, 2, 3, 4, 5]
    
    visual_breakpoint(locals(), "Testing debug utilities")
    
    # Test JSON printing
    print_json({"status": "ok", "data": {"items": [1, 2, 3]}}, "API Response")
    
    # Test code printing
    code = """
def hello_world():
    print("Hello, World!")
    return 42
"""
    print_code(code, "python", "Sample Function")