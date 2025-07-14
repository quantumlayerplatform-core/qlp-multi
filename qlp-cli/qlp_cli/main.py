#!/usr/bin/env python3
"""
QuantumLayer CLI - Main entry point
"""

import click
import asyncio
import sys
from pathlib import Path
from typing import Optional
import json
import httpx

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import print as rprint

from .api_client import QLPClient, GenerationError
from .interactive import InteractiveSession
from .utils import (
    extract_capsule,
    format_time,
    get_random_tip,
    validate_description,
    ensure_config
)
from .config import Config

console = Console()

@click.group()
@click.version_option(version="0.1.0", prog_name="QuantumLayer CLI")
@click.option('--api-url', envvar='QLP_API_URL', help='API endpoint URL')
@click.option('--api-key', envvar='QLP_API_KEY', help='API key for authentication')
@click.pass_context
def cli(ctx, api_url: Optional[str], api_key: Optional[str]):
    """
    🧠 QuantumLayer - Build entire systems with one command
    
    Examples:
        qlp generate "REST API for task management"
        qlp generate "React dashboard with charts" --deploy aws
        qlp interactive
        qlp from-image architecture.png
    """
    ctx.ensure_object(dict)
    
    # Create config instance
    config = Config()
    
    # Update config if provided
    if api_url:
        config.api_url = api_url
    if api_key:
        config.api_key = api_key
    
    ctx.obj['client'] = QLPClient(config)
    ctx.obj['config'] = config


@cli.command()
@click.argument('description')
@click.option('--language', '-l', type=click.Choice(['python', 'javascript', 'typescript', 'go', 'java', 'auto']), 
              default='auto', help='Programming language')
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.option('--deploy', type=click.Choice(['aws', 'azure', 'gcp', 'local']), 
              help='Deploy after generation')
@click.option('--github', is_flag=True, help='Push to GitHub after generation')
@click.option('--dry-run', is_flag=True, help='Preview what would be generated')
@click.option('--timeout', '-t', type=int, default=10, help='Timeout in minutes (default: 10)')
@click.pass_context
def generate(ctx, description: str, language: str, output: Optional[str], 
             deploy: Optional[str], github: bool, dry_run: bool, timeout: int):
    """Generate a complete project from natural language description"""
    
    # Validate description
    if not validate_description(description):
        console.print("[red]Error:[/] Description too short. Please provide more detail.")
        return
    
    # Show what we're about to do
    console.print(Panel(
        f"[bold cyan]Project:[/] {description}\n"
        f"[bold cyan]Language:[/] {language}\n"
        f"[bold cyan]Output:[/] {output or './generated'}\n"
        f"[bold cyan]Deploy:[/] {deploy or 'none'}\n"
        f"[bold cyan]GitHub:[/] {'yes' if github else 'no'}",
        title="🚀 Generation Request",
        border_style="cyan"
    ))
    
    if dry_run:
        console.print("\n[yellow]This is a dry run. No files will be generated.[/]")
        return
    
    # Confirm if needed
    if not Confirm.ask("\nProceed with generation?", default=True):
        console.print("[yellow]Generation cancelled.[/]")
        return
    
    # Run async generation
    client = ctx.obj['client']
    asyncio.run(_generate_async(client, description, language, output, deploy, github, timeout))


async def _generate_async(client: QLPClient, description: str, language: str, 
                         output: Optional[str], deploy: Optional[str], github: bool, timeout: int = 30):
    """Async implementation of generation"""
    
    workflow_id = None
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            
            # Start generation
            task = progress.add_task("Starting generation...", total=100)
            
            result = await client.start_generation(
                description=description,
                language=language,
                deploy_target=deploy,
                push_to_github=github
            )
            
            workflow_id = result['workflow_id']
            console.print(f"[dim]Workflow ID: {workflow_id}[/]")
            progress.update(task, advance=10, description="Workflow started...")
            
            # Poll for status with timeout from command line
            status = await client.poll_workflow_status(
                workflow_id=workflow_id,
                progress=progress,
                task=task,
                timeout_minutes=timeout
            )
            
            if status['status'] == 'completed':
                progress.update(task, completed=100, description="Generation complete!")
                
                # Get capsule info safely
                result = status.get('result', {})
                capsule_id = result.get('capsule_id') if isinstance(result, dict) else None
                
                if not capsule_id:
                    console.print("\n[red]Error:[/] Workflow completed but no capsule ID found")
                    console.print(f"[dim]Result: {json.dumps(result, indent=2)}[/]")
                    sys.exit(1)
                
                # Download and extract
                console.print("\n[cyan]Downloading generated files...[/]")
                output_path = output or f"./generated/{capsule_id}"
                
                try:
                    await client.download_capsule(
                        capsule_id=capsule_id,
                        output_path=output_path
                    )
                    
                    # Show results
                    _show_generation_results(result, output_path)
                    
                    # Deploy if requested
                    if deploy:
                        console.print(f"\n[cyan]Deploying to {deploy}...[/]")
                        await _deploy_project(client, capsule_id, deploy)
                    
                    # Show tip
                    console.print(f"\n💡 [italic]{get_random_tip()}[/]")
                    
                except Exception as e:
                    console.print(f"\n[red]Error downloading capsule:[/] {e}")
                    console.print(f"[dim]Capsule ID: {capsule_id}[/]")
                    sys.exit(1)
                
            else:
                console.print(f"\n[red]Generation failed:[/] {status.get('error', 'Unknown error')}")
                console.print(f"[dim]Status: {status.get('status', 'unknown')}[/]")
                if workflow_id:
                    console.print(f"[dim]Workflow ID: {workflow_id}[/]")
                    console.print(f"\n[yellow]Tip:[/] Use 'qlp status {workflow_id}' to check the workflow status")
                sys.exit(1)
                
    except GenerationError as e:
        console.print(f"\n[red]Generation error:[/] {e}")
        if workflow_id:
            console.print(f"[dim]Workflow ID: {workflow_id}[/]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Generation cancelled by user.[/]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Unexpected error:[/] {e}")
        sys.exit(1)


def _show_generation_results(result: dict, output_path: str):
    """Display generation results in a nice format"""
    
    console.print("\n[bold green]✅ Generation Complete![/]\n")
    
    # Create summary table
    table = Table(title="Generation Summary", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    
    # Extract metadata
    metadata = result.get('metadata', {})
    capsule_info = metadata.get('capsule_info', {})
    files_info = capsule_info.get('files', {})
    
    # Count files
    total_files = 0
    all_files = []
    for category, file_list in files_info.items():
        total_files += len(file_list)
        for f in file_list:
            all_files.append(f)
    
    table.add_row("Capsule ID", result.get('capsule_id', 'N/A'))
    table.add_row("Files Generated", str(total_files))
    table.add_row("Execution Time", f"{result.get('execution_time', 0):.1f}s")
    table.add_row("Tasks Completed", f"{result.get('tasks_completed', 0)}/{result.get('tasks_total', 0)}")
    table.add_row("Output Path", output_path)
    
    console.print(table)
    
    # Show file tree by category
    if files_info:
        console.print("\n[bold]Generated Files:[/]")
        for category, files in files_info.items():
            if files:
                console.print(f"  📁 {category}/")
                for file in files[:5]:  # Show first 5 per category
                    console.print(f"    📄 {file}")
                if len(files) > 5:
                    console.print(f"    ... and {len(files) - 5} more files")


@cli.command()
@click.pass_context
def interactive(ctx):
    """Start interactive mode for conversational project generation"""
    
    console.print(Panel(
        "[bold cyan]🧠 QuantumLayer Interactive Mode[/]\n\n"
        "Build complete systems through conversation.\n"
        "Type 'help' for commands or 'exit' to quit.",
        border_style="cyan"
    ))
    
    client = ctx.obj['client']
    session = InteractiveSession(client, console)
    
    try:
        asyncio.run(session.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Exiting interactive mode.[/]")


@cli.command()
@click.argument('image_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.pass_context
def from_image(ctx, image_path: str, output: Optional[str]):
    """Generate system from architecture diagram or mockup"""
    
    console.print(f"[cyan]🎨 Analyzing image:[/] {image_path}")
    
    # Show image info
    from PIL import Image
    try:
        img = Image.open(image_path)
        console.print(f"[dim]Image size: {img.size[0]}x{img.size[1]}, Format: {img.format}[/]")
    except:
        pass
    
    client = ctx.obj['client']
    
    try:
        # Upload and analyze image
        with console.status("Analyzing architecture diagram..."):
            asyncio.run(_generate_from_image(client, image_path, output))
            
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


async def _generate_from_image(client: QLPClient, image_path: str, output: Optional[str]):
    """Generate project from image"""
    
    # Upload image
    result = await client.analyze_image(image_path)
    
    # Show what was detected
    console.print("\n[bold]Detected Architecture:[/]")
    console.print(result['description'])
    
    # Confirm generation
    if Confirm.ask("\nGenerate this system?", default=True):
        # Use regular generation with extracted description
        await _generate_async(
            client=client,
            description=result['description'],
            language='auto',
            output=output,
            deploy=None,
            github=False
        )


@cli.command()
@click.argument('workflow_id')
@click.pass_context
def status(ctx, workflow_id: str):
    """Check the status of a running workflow"""
    
    client = ctx.obj['client']
    
    try:
        asyncio.run(_check_status(client, workflow_id))
    except Exception as e:
        console.print(f"[red]Error checking status:[/] {e}")
        sys.exit(1)


async def _check_status(client: QLPClient, workflow_id: str):
    """Check workflow status"""
    
    async with httpx.AsyncClient(timeout=10.0) as http_client:
        response = await http_client.get(
            f"{client.base_url}/workflow/status/{workflow_id}",
            headers=client.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            
            status = data.get('status', 'unknown')
            
            # Check if completed
            if status == 'completed':
                console.print("[bold green]✅ Workflow completed![/]\n")
                
                table = Table(show_header=False)
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="white")
                
                # Get result data
                result = data.get('result', {})
                
                table.add_row("Workflow ID", workflow_id)
                table.add_row("Status", status)
                
                if isinstance(result, dict) and 'capsule_id' in result:
                    table.add_row("Capsule ID", result.get('capsule_id', 'N/A'))
                    table.add_row("Execution Time", f"{result.get('execution_time', 0):.1f}s")
                    table.add_row("Tasks Completed", f"{result.get('tasks_completed', 0)}/{result.get('tasks_total', 0)}")
                    
                    console.print(table)
                    
                    # Show files if available
                    if 'metadata' in result and 'capsule_info' in result['metadata']:
                        files_info = result['metadata']['capsule_info'].get('files', {})
                        if files_info:
                            console.print("\n[bold]Generated Files:[/]")
                            for category, files in files_info.items():
                                if files:
                                    console.print(f"  📁 {category}/")
                                    for file in files[:3]:
                                        console.print(f"    📄 {file}")
                                    if len(files) > 3:
                                        console.print(f"    ... and {len(files) - 3} more")
                else:
                    console.print(table)
                    console.print("\n[dim]Run 'qlp generate' with --output to download the files[/]")
                    
            elif status in ['failed', 'error', 'terminated', 'canceled']:
                console.print(f"[red]❌ Workflow {status}[/]")
                console.print(f"Error: {data.get('error', 'Unknown error')}")
            else:
                # Still running
                console.print(f"[yellow]⏳ Workflow {workflow_id} is {status}[/]")
                
                # Show timing info
                if 'started_at' in data:
                    console.print(f"Started: {data['started_at']}")
                
                console.print("\n[dim]Check again in a few moments or use Ctrl+C to exit[/]")
        else:
            console.print(f"[red]Workflow not found or error checking status[/]")


@cli.command()
def watch():
    """Watch for // TODO: QL comments and generate code"""
    
    console.print("[yellow]👀 Watching for QL comments...[/]")
    console.print("[dim]Add '// TODO: QL: <description>' to any file[/]")
    console.print("[dim]Press Ctrl+C to stop watching[/]\n")
    
    from .watcher import CodeWatcher
    watcher = CodeWatcher(console)
    
    try:
        asyncio.run(watcher.watch())
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped watching.[/]")


@cli.command()
@click.argument('command', type=click.Choice(['global', 'personal', 'leaderboard']))
def stats(command: str):
    """Show QuantumLayer statistics"""
    
    if command == 'global':
        _show_global_stats()
    elif command == 'personal':
        _show_personal_stats()
    elif command == 'leaderboard':
        _show_leaderboard()


def _show_global_stats():
    """Display global platform statistics"""
    
    # Mock data for now - will connect to real API
    console.print(Panel(
        "[bold cyan]🚀 QuantumLayer Global Stats[/]\n\n"
        "• Projects generated today: [bold]12,847[/]\n"
        "• Lines of code created: [bold]48,293,847[/]\n"
        "• Developer hours saved: [bold]384,737[/]\n"
        "• Active developers: [bold]3,421[/]\n"
        "• Languages supported: [bold]15[/]\n"
        "• Average generation time: [bold]47.3s[/]",
        title="Platform Statistics",
        border_style="cyan"
    ))


def _show_personal_stats():
    """Display user's personal statistics"""
    
    console.print(Panel(
        "[bold cyan]📊 Your QuantumLayer Stats[/]\n\n"
        "• Projects generated: [bold]23[/]\n"
        "• Lines of code: [bold]142,381[/]\n"
        "• Hours saved: [bold]~284[/]\n"
        "• Favorite language: [bold]Python[/]\n"
        "• Success rate: [bold]91.3%[/]\n"
        "• Global rank: [bold]#342[/]",
        title="Personal Statistics",
        border_style="green"
    ))


def _show_leaderboard():
    """Display developer leaderboard"""
    
    table = Table(title="🏆 Top Developers This Week")
    table.add_column("Rank", style="cyan", justify="center")
    table.add_column("Developer", style="white")
    table.add_column("Projects", style="green", justify="right")
    table.add_column("Lines", style="yellow", justify="right")
    
    # Mock data
    leaderboard = [
        ("1", "alice_dev", "127", "523,492"),
        ("2", "bob_builder", "98", "412,381"),
        ("3", "charlie_code", "87", "398,123"),
        ("...", "...", "...", "..."),
        ("342", "you", "23", "142,381"),
    ]
    
    for rank, dev, projects, lines in leaderboard:
        table.add_row(rank, dev, projects, lines)
    
    console.print(table)


@cli.command()
@click.option('--init', is_flag=True, help='Initialize configuration')
@click.option('--show', is_flag=True, help='Show current configuration')
@click.pass_context
def config(ctx, init: bool, show: bool):
    """Manage QuantumLayer CLI configuration"""
    
    if init:
        ensure_config()
        console.print("[green]✅ Configuration initialized![/]")
    elif show:
        config_obj = ctx.obj.get('config', Config())
        config_data = config_obj.to_dict()
        console.print(Syntax(
            json.dumps(config_data, indent=2),
            "json",
            theme="monokai"
        ))
    else:
        console.print("Use --init to initialize or --show to display config")


async def _deploy_project(client: QLPClient, capsule_id: str, target: str):
    """Deploy generated project to cloud"""
    
    with console.status(f"Deploying to {target}..."):
        result = await client.deploy_capsule(capsule_id, target)
        
    if result['status'] == 'success':
        console.print(f"[green]✅ Deployed successfully![/]")
        console.print(f"[cyan]URL:[/] {result['url']}")
    else:
        console.print(f"[red]Deployment failed:[/] {result['error']}")


if __name__ == "__main__":
    cli()