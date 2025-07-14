"""
Enhanced live progress display with activity tracking and thought bubbles
"""

import asyncio
import time
import httpx
from typing import Optional, Dict, Any
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.align import Align
from rich import box
from .utils import get_random_thought
from .api_client import GenerationError

console = Console()

class ActivityTracker:
    """Tracks and displays Temporal workflow activities"""
    
    def __init__(self):
        self.activities = []
        self.current_activity = None
        self.start_time = time.time()
        self.thought_interval = 5  # Show thought every 5 seconds
        self.last_thought_time = time.time()
        self.current_thought = None
        
    def add_activity(self, name: str, status: str = "running"):
        """Add a new activity to the tracker"""
        activity = {
            "name": name,
            "status": status,
            "start_time": time.time()
        }
        self.activities.append(activity)
        self.current_activity = activity
        
    def update_current(self, status: str):
        """Update the current activity status"""
        if self.current_activity:
            self.current_activity["status"] = status
            if status == "completed":
                self.current_activity["end_time"] = time.time()
    
    def get_thought(self, stage: str) -> Optional[str]:
        """Get a thought bubble if enough time has passed"""
        current_time = time.time()
        if current_time - self.last_thought_time > self.thought_interval:
            self.current_thought = get_random_thought(stage)
            self.last_thought_time = current_time
        return self.current_thought

class EnhancedProgressDisplay:
    """Enhanced progress display with live updates"""
    
    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.start_time = time.time()
        self.activity_tracker = ActivityTracker()
        self.current_stage = "initializing"
        self.progress_pct = 0
        self.tasks_completed = 0
        self.tasks_total = 0
        self.current_activity = None
        self.current_task = None
        
    def create_layout(self) -> Layout:
        """Create the display layout"""
        layout = Layout()
        
        # Split into sections
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=4)
        )
        
        # Header
        elapsed = time.time() - self.start_time
        header_text = Text()
        header_text.append("🧠 QuantumLayer Generation\n", style="bold cyan")
        header_text.append(f"Workflow: {self.workflow_id[:8]}... | ", style="dim")
        header_text.append(f"Elapsed: {self._format_time(elapsed)}", style="dim")
        
        layout["header"].update(Panel(
            Align.center(header_text),
            border_style="cyan",
            box=box.MINIMAL
        ))
        
        # Main content
        main_content = self._create_main_content()
        layout["main"].update(main_content)
        
        # Footer with activity history
        footer_content = self._create_activity_table()
        layout["footer"].update(Panel(
            footer_content,
            title="[bold]Activity Timeline[/]",
            border_style="blue",
            box=box.ROUNDED
        ))
        
        return layout
    
    def _create_main_content(self) -> Panel:
        """Create the main progress content"""
        from rich.console import Group
        
        # Progress bar
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            expand=False
        )
        
        # Add main task
        task = progress.add_task(
            self._get_status_message(),
            total=100,
            completed=self.progress_pct
        )
        
        # Create content components
        content_parts = [progress]
        
        # Add thought bubble if available
        thought = self.activity_tracker.get_thought(self.current_stage)
        if thought:
            thought_panel = Panel(
                Text(thought, style="italic"),
                title="💭 AI Thinking",
                border_style="yellow",
                box=box.ROUNDED,
                padding=(0, 2)
            )
            content_parts.append("")  # Empty line
            content_parts.append(thought_panel)
        
        # Add task counter
        if self.tasks_total > 0:
            task_text = Text()
            task_text.append("Tasks: ", style="bold")
            task_text.append(f"{self.tasks_completed}/{self.tasks_total}", style="cyan")
            content_parts.append("")  # Empty line
            content_parts.append(Align.center(task_text))
        
        # Use Group to combine all content
        content = Group(*content_parts)
        
        return Panel(
            content,
            title="[bold]🚀 Generation Progress[/]",
            border_style="green",
            box=box.DOUBLE
        )
    
    def _create_activity_table(self) -> Table:
        """Create activity timeline table"""
        table = Table(show_header=True, box=box.SIMPLE, expand=True)
        table.add_column("Activity", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Duration", justify="right")
        
        # Add completed activities
        for activity in self.activity_tracker.activities[-5:]:  # Show last 5
            name = self._format_activity_name(activity["name"])
            status = self._format_status(activity["status"])
            
            if activity["status"] == "completed" and "end_time" in activity:
                duration = activity["end_time"] - activity["start_time"]
                duration_str = f"{duration:.1f}s"
            else:
                duration_str = "..."
            
            table.add_row(name, status, duration_str)
        
        return table
    
    def _get_status_message(self) -> str:
        """Get current status message"""
        if self.current_activity:
            activity_map = {
                'analyze_request_activity': '🔍 Analyzing your request',
                'decompose_tasks_activity': '📋 Breaking down into tasks',
                'create_ql_capsule_activity': '⚡ Generating code',
                'validate_capsule_activity': '🧪 Validating quality',
                'github_push_activity': '🐙 Pushing to GitHub',
                'deploy_activity': '🚀 Deploying application'
            }
            
            base_msg = activity_map.get(self.current_activity, f"🔧 {self.current_activity}")
            
            if self.current_task:
                return f"{base_msg} - {self.current_task}"
            return base_msg
        
        return "Initializing workflow..."
    
    def _format_activity_name(self, name: str) -> str:
        """Format activity name for display"""
        name_map = {
            'analyze_request_activity': 'Analyze Request',
            'decompose_tasks_activity': 'Task Decomposition',
            'create_ql_capsule_activity': 'Code Generation',
            'validate_capsule_activity': 'Quality Validation',
            'github_push_activity': 'GitHub Push',
            'deploy_activity': 'Deployment'
        }
        return name_map.get(name, name.replace('_', ' ').title())
    
    def _format_status(self, status: str) -> str:
        """Format status with emoji"""
        status_map = {
            'running': '[yellow]⏳ Running[/]',
            'completed': '[green]✅ Done[/]',
            'failed': '[red]❌ Failed[/]',
            'skipped': '[dim]⏭️ Skipped[/]'
        }
        return status_map.get(status, status)
    
    def _format_time(self, seconds: float) -> str:
        """Format time duration"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        minutes = seconds / 60
        if minutes < 60:
            return f"{minutes:.1f}m"
        hours = minutes / 60
        return f"{hours:.1f}h"
    
    def update(self, data: Dict[str, Any]):
        """Update display with new data"""
        # Update from workflow status
        result = data.get('result', {})
        
        self.tasks_completed = result.get('tasks_completed', 0)
        self.tasks_total = result.get('tasks_total', 0)
        self.current_stage = result.get('current_stage', 'generating')
        self.current_activity = result.get('current_activity', '')
        self.current_task = result.get('current_task', '')
        
        # Update progress
        if self.tasks_total > 0:
            self.progress_pct = min(90, (self.tasks_completed / self.tasks_total) * 90 + 10)
        else:
            elapsed = time.time() - self.start_time
            self.progress_pct = min(90, 10 + (elapsed / 60) * 20)
        
        # Track activities
        if self.current_activity and (not self.activity_tracker.current_activity or 
                                     self.activity_tracker.current_activity["name"] != self.current_activity):
            # Mark previous as completed
            if self.activity_tracker.current_activity:
                self.activity_tracker.update_current("completed")
            
            # Add new activity
            self.activity_tracker.add_activity(self.current_activity)

async def show_live_progress(client, workflow_id: str, timeout_minutes: int = 30) -> Dict[str, Any]:
    """Show live progress with enhanced display"""
    display = EnhancedProgressDisplay(workflow_id)
    
    with Live(display.create_layout(), refresh_per_second=2, console=console) as live:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            max_attempts = timeout_minutes * 30  # Check every 2 seconds
            
            for attempt in range(max_attempts):
                try:
                    response = await http_client.get(
                        f"{client.base_url}/workflow/status/{workflow_id}",
                        headers=client.headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        status = data.get('status', 'unknown')
                        
                        # Update display
                        display.update(data)
                        live.update(display.create_layout())
                        
                        # Check if completed
                        if status == 'completed':
                            display.progress_pct = 100
                            display.activity_tracker.update_current("completed")
                            live.update(display.create_layout())
                            await asyncio.sleep(1)  # Show completion briefly
                            return data
                        
                        # Check if failed
                        elif status in ['failed', 'error', 'terminated', 'canceled']:
                            raise GenerationError(f"Workflow {status}: {data.get('error', 'Unknown error')}")
                    
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    if attempt >= max_attempts - 1:
                        raise
                    await asyncio.sleep(2)
            
            raise GenerationError(f"Workflow timed out after {timeout_minutes} minutes")