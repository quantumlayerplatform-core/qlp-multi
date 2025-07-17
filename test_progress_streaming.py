#!/usr/bin/env python3
"""
Test script for progress streaming functionality
Demonstrates real-time progress tracking during workflow execution
"""

import asyncio
import sys
import time
from datetime import datetime
import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel

from src.common.progress_client import ProgressClient

console = Console()


class WorkflowProgressTracker:
    """Rich UI for tracking workflow progress"""
    
    def __init__(self):
        self.activities = {}
        self.logs = []
        self.status = "Starting..."
        self.start_time = time.time()
        self.completed = False
        self.failed = False
        self.error = None
    
    def create_layout(self) -> Layout:
        """Create the UI layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="progress", size=10),
            Layout(name="logs", size=10),
            Layout(name="footer", size=3)
        )
        
        return layout
    
    def render_header(self) -> Panel:
        """Render the header"""
        elapsed = time.time() - self.start_time
        status_emoji = "✅" if self.completed else "❌" if self.failed else "🔄"
        
        content = f"{status_emoji} Status: {self.status}\n"
        content += f"⏱️  Elapsed: {elapsed:.1f}s\n"
        content += f"📅 Started: {datetime.fromtimestamp(self.start_time).strftime('%H:%M:%S')}"
        
        return Panel(content, title="Workflow Progress Tracker", border_style="blue")
    
    def render_progress(self) -> Panel:
        """Render activity progress"""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Activity", style="cyan", width=30)
        table.add_column("Status", width=15)
        table.add_column("Progress", width=20)
        table.add_column("Message", width=40)
        
        for activity_id, activity_info in self.activities.items():
            status = activity_info['status']
            progress = activity_info.get('progress', 0)
            message = activity_info.get('message', '')
            
            # Status emoji
            if status == 'completed':
                status_display = "✅ Completed"
            elif status == 'failed':
                status_display = "❌ Failed"
            elif status == 'in_progress':
                status_display = "🔄 Running"
            else:
                status_display = "⏳ Pending"
            
            # Progress bar
            progress_bar = f"[{'█' * int(progress * 20)}{' ' * (20 - int(progress * 20))}] {progress*100:.0f}%"
            
            table.add_row(
                activity_info.get('name', activity_id),
                status_display,
                progress_bar,
                message[:40] + "..." if len(message) > 40 else message
            )
        
        return Panel(table, title="Activities", border_style="green")
    
    def render_logs(self) -> Panel:
        """Render recent logs"""
        # Keep only last 8 logs
        recent_logs = self.logs[-8:]
        log_content = "\n".join(recent_logs) if recent_logs else "No logs yet..."
        
        return Panel(log_content, title="Recent Events", border_style="yellow")
    
    def render_footer(self) -> Panel:
        """Render the footer"""
        if self.completed:
            content = "✅ Workflow completed successfully!"
            style = "green"
        elif self.failed:
            content = f"❌ Workflow failed: {self.error or 'Unknown error'}"
            style = "red"
        else:
            content = "🔄 Workflow in progress... Press Ctrl+C to stop tracking."
            style = "blue"
        
        return Panel(content, border_style=style)
    
    async def handle_event(self, event: dict):
        """Handle a progress event"""
        event_type = event.get('type')
        data = event.get('data', {})
        timestamp = event.get('timestamp', '')
        
        # Update based on event type
        if event_type == 'workflow_started':
            self.status = "Workflow started"
            self.logs.append(f"[{timestamp}] Workflow started: {data.get('description', '')}")
        
        elif event_type == 'workflow_completed':
            self.status = "Completed"
            self.completed = True
            self.logs.append(f"[{timestamp}] Workflow completed successfully")
        
        elif event_type == 'workflow_failed':
            self.status = "Failed"
            self.failed = True
            self.error = data.get('error', 'Unknown error')
            self.logs.append(f"[{timestamp}] Workflow failed: {self.error}")
        
        elif event_type == 'activity_started':
            activity_id = event.get('activity_id', 'unknown')
            self.activities[activity_id] = {
                'name': data.get('activity_name', activity_id),
                'status': 'in_progress',
                'progress': 0,
                'message': 'Started'
            }
            self.logs.append(f"[{timestamp}] Activity started: {data.get('activity_name', '')}")
        
        elif event_type == 'activity_progress':
            activity_id = event.get('activity_id', 'unknown')
            if activity_id in self.activities:
                self.activities[activity_id]['progress'] = data.get('progress', 0)
                self.activities[activity_id]['message'] = data.get('message', '')
        
        elif event_type == 'activity_completed':
            activity_id = event.get('activity_id', 'unknown')
            if activity_id in self.activities:
                self.activities[activity_id]['status'] = 'completed'
                self.activities[activity_id]['progress'] = 1.0
                self.activities[activity_id]['message'] = 'Completed'
            self.logs.append(f"[{timestamp}] Activity completed: {self.activities.get(activity_id, {}).get('name', activity_id)}")
        
        elif event_type == 'activity_failed':
            activity_id = event.get('activity_id', 'unknown')
            if activity_id in self.activities:
                self.activities[activity_id]['status'] = 'failed'
                self.activities[activity_id]['message'] = data.get('error', 'Failed')
            self.logs.append(f"[{timestamp}] Activity failed: {data.get('error', '')}")
        
        elif event_type == 'log_message':
            self.logs.append(f"[{timestamp}] {data.get('level', 'INFO')}: {data.get('message', '')}")
        
        elif event_type == 'status_update':
            self.status = data.get('message', self.status)


async def test_progress_streaming(workflow_id: str = None):
    """Test progress streaming with a nice UI"""
    
    if not workflow_id:
        # First, create a test workflow
        console.print("[yellow]Creating a test workflow...[/yellow]")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/execute",
                json={
                    "description": "Create a Python web scraper with BeautifulSoup that extracts product information",
                    "tenant_id": "test-tenant",
                    "user_id": "test-user"
                }
            )
            
            if response.status_code != 200:
                console.print(f"[red]Failed to create workflow: {response.text}[/red]")
                return
            
            result = response.json()
            workflow_id = result.get('workflow_id')
            console.print(f"[green]Created workflow: {workflow_id}[/green]")
    
    # Create progress tracker
    tracker = WorkflowProgressTracker()
    layout = tracker.create_layout()
    
    # Create progress client
    client = ProgressClient(use_websocket=True)
    
    # Track the workflow with live updates
    with Live(layout, refresh_per_second=4) as live:
        # Update UI periodically
        async def update_ui():
            while not tracker.completed and not tracker.failed:
                layout["header"].update(tracker.render_header())
                layout["progress"].update(tracker.render_progress())
                layout["logs"].update(tracker.render_logs())
                layout["footer"].update(tracker.render_footer())
                await asyncio.sleep(0.25)
            
            # Final update
            layout["header"].update(tracker.render_header())
            layout["progress"].update(tracker.render_progress())
            layout["logs"].update(tracker.render_logs())
            layout["footer"].update(tracker.render_footer())
        
        # Start UI update task
        ui_task = asyncio.create_task(update_ui())
        
        try:
            # Track workflow
            await client.track_workflow(
                workflow_id=workflow_id,
                callback=tracker.handle_event
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped tracking workflow[/yellow]")
        finally:
            # Cancel UI task
            ui_task.cancel()
            try:
                await ui_task
            except asyncio.CancelledError:
                pass
    
    # Print summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"Total events: {len(client.get_events())}")
    console.print(f"Activities tracked: {len(tracker.activities)}")
    console.print(f"Completed: {'Yes' if tracker.completed else 'No'}")
    console.print(f"Failed: {'Yes' if tracker.failed else 'No'}")


async def test_simple_progress():
    """Simple test without UI"""
    console.print("[yellow]Testing simple progress streaming...[/yellow]")
    
    # Create a test workflow
    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            "http://localhost:8000/execute",
            json={
                "description": "Write a factorial function in Python",
                "tenant_id": "test",
                "user_id": "test"
            }
        )
        
        if response.status_code != 200:
            console.print(f"[red]Failed to create workflow: {response.text}[/red]")
            return
        
        result = response.json()
        workflow_id = result['workflow_id']
        console.print(f"[green]Workflow ID: {workflow_id}[/green]")
    
    # Track progress
    client = ProgressClient(use_websocket=False)  # Use SSE
    
    async def print_event(event: dict):
        event_type = event.get('type')
        data = event.get('data', {})
        
        if event_type == 'activity_progress':
            console.print(f"📊 Progress: {data.get('progress', 0)*100:.0f}% - {data.get('message', '')}")
        elif event_type == 'activity_started':
            console.print(f"🚀 Started: {data.get('activity_name', 'Unknown activity')}")
        elif event_type == 'activity_completed':
            console.print(f"✅ Completed: {data.get('activity_name', 'Unknown activity')}")
        elif event_type == 'workflow_completed':
            console.print("[green bold]🎉 Workflow completed![/green bold]")
        elif event_type == 'workflow_failed':
            console.print(f"[red bold]❌ Workflow failed: {data.get('error', 'Unknown error')}[/red bold]")
    
    await client.track_workflow(workflow_id, callback=print_event)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test progress streaming")
    parser.add_argument("--workflow-id", help="Existing workflow ID to track")
    parser.add_argument("--simple", action="store_true", help="Use simple output instead of UI")
    
    args = parser.parse_args()
    
    try:
        if args.simple:
            asyncio.run(test_simple_progress())
        else:
            asyncio.run(test_progress_streaming(args.workflow_id))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
