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
    ensure_config,
    get_random_thought,
    format_cost,
    estimate_cost
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
    
    # Estimate cost
    estimated_cost = estimate_cost(description, language)
    
    # Show what we're about to do with enhanced formatting
    request_table = Table(show_header=False, box=None)
    request_table.add_column(style="bold cyan", width=15)
    request_table.add_column(style="white")
    
    request_table.add_row("Project", description)
    request_table.add_row("Language", language)
    request_table.add_row("Output", output or './generated')
    request_table.add_row("Deploy", deploy or 'none')
    request_table.add_row("GitHub", '✅ Yes' if github else '❌ No')
    request_table.add_row("Est. Cost", format_cost(estimated_cost))
    request_table.add_row("Est. Time", f"{timeout} minutes")
    
    console.print(Panel(
        request_table,
        title="🚀 Generation Request",
        border_style="cyan",
        padding=(1, 2)
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
    table.add_row("Execution Time", format_time(result.get('execution_time', 0)))
    table.add_row("Tasks Completed", f"{result.get('tasks_completed', 0)}/{result.get('tasks_total', 0)}")
    
    # Add cost if available
    cost = metadata.get('total_cost', 0)
    if cost > 0:
        table.add_row("Total Cost", format_cost(cost))
    
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
@click.argument('capsule_id')
@click.option('--detailed', '-d', is_flag=True, help='Show detailed validation results')
@click.pass_context
def validate(ctx, capsule_id: str, detailed: bool):
    """Validate a generated capsule"""
    
    client = ctx.obj['client']
    
    try:
        asyncio.run(_validate_capsule(client, capsule_id, detailed))
    except Exception as e:
        console.print(f"[red]Error validating capsule:[/] {e}")
        sys.exit(1)


async def _validate_capsule(client: QLPClient, capsule_id: str, detailed: bool):
    """Validate capsule implementation"""
    
    with console.status("Validating capsule..."):
        # Get capsule details
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.get(
                f"{client.base_url}/capsule/{capsule_id}",
                headers=client.headers
            )
            
            if response.status_code != 200:
                console.print(f"[red]Capsule not found:[/] {capsule_id}")
                return
            
            capsule_data = response.json()
    
    # Display validation results
    validation_info = capsule_data.get('validation', {})
    
    if not validation_info:
        console.print("[yellow]No validation data available for this capsule[/]")
        return
    
    # Create validation summary
    status = validation_info.get('overall_status', 'unknown')
    confidence = validation_info.get('confidence_score', 0)
    
    # Status emoji and color
    status_display = {
        'passed': ('✅', 'green', 'All Checks Passed'),
        'failed': ('❌', 'red', 'Validation Failed'),
        'passed_with_warnings': ('⚠️', 'yellow', 'Passed with Warnings')
    }
    
    emoji, color, message = status_display.get(status, ('❓', 'white', 'Unknown'))
    
    # Summary panel
    summary_table = Table(show_header=False, box=None)
    summary_table.add_column(style="cyan", width=20)
    summary_table.add_column(style=color)
    
    summary_table.add_row("Status", f"{emoji} {message}")
    summary_table.add_row("Confidence", f"{confidence:.1%}")
    summary_table.add_row("Capsule ID", capsule_id)
    
    console.print(Panel(
        summary_table,
        title="[bold]🧪 Validation Summary[/]",
        border_style=color
    ))
    
    # Detailed checks if requested
    if detailed and 'checks' in validation_info:
        checks = validation_info['checks']
        
        check_table = Table(title="Detailed Validation Checks")
        check_table.add_column("Check", style="cyan")
        check_table.add_column("Status", justify="center")
        check_table.add_column("Details", style="dim")
        
        for check in checks:
            check_name = check.get('name', 'Unknown')
            check_passed = check.get('passed', False)
            check_status = '✅' if check_passed else '❌'
            check_details = check.get('message', '')
            
            check_table.add_row(check_name, check_status, check_details)
        
        console.print("\n")
        console.print(check_table)


@cli.command()
@click.argument('capsule_id')
@click.option('--files', '-f', is_flag=True, help='List all files in capsule')
@click.option('--metadata', '-m', is_flag=True, help='Show capsule metadata')
@click.pass_context
def inspect(ctx, capsule_id: str, files: bool, metadata: bool):
    """Inspect a capsule's contents and metadata"""
    
    client = ctx.obj['client']
    
    try:
        asyncio.run(_inspect_capsule(client, capsule_id, files, metadata))
    except Exception as e:
        console.print(f"[red]Error inspecting capsule:[/] {e}")
        sys.exit(1)


async def _inspect_capsule(client: QLPClient, capsule_id: str, show_files: bool, show_metadata: bool):
    """Inspect capsule implementation"""
    
    with console.status("Loading capsule details..."):
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.get(
                f"{client.base_url}/capsule/{capsule_id}",
                headers=client.headers
            )
            
            if response.status_code != 200:
                console.print(f"[red]Capsule not found:[/] {capsule_id}")
                return
            
            capsule_data = response.json()
    
    # Basic info
    info_table = Table(show_header=False, box=None)
    info_table.add_column(style="cyan", width=20)
    info_table.add_column(style="white")
    
    info_table.add_row("Capsule ID", capsule_id)
    info_table.add_row("Status", capsule_data.get('status', 'unknown'))
    info_table.add_row("Created", capsule_data.get('created_at', 'N/A'))
    
    # Extract metadata
    metadata_obj = capsule_data.get('metadata', {})
    capsule_info = metadata_obj.get('capsule_info', {})
    
    if capsule_info:
        info_table.add_row("Language", capsule_info.get('language', 'auto'))
        info_table.add_row("Framework", capsule_info.get('framework', 'N/A'))
        
        # Count files
        files_info = capsule_info.get('files', {})
        total_files = sum(len(files) for files in files_info.values())
        info_table.add_row("Total Files", str(total_files))
    
    console.print(Panel(
        info_table,
        title="[bold]📦 Capsule Information[/]",
        border_style="blue"
    ))
    
    # Show files if requested
    if show_files and capsule_info and 'files' in capsule_info:
        files_info = capsule_info['files']
        
        console.print("\n[bold]📁 File Structure:[/]\n")
        
        for category, file_list in files_info.items():
            if file_list:
                console.print(f"[cyan]{category}/[/]")
                for file in sorted(file_list):
                    console.print(f"  📄 {file}")
                console.print()
    
    # Show metadata if requested
    if show_metadata:
        console.print("\n[bold]📊 Metadata:[/]\n")
        console.print(Syntax(
            json.dumps(metadata_obj, indent=2),
            "json",
            theme="monokai"
        ))


@cli.command()
@click.argument('repo_url')
@click.option('--validate', '-v', is_flag=True, help='Validate the repository contents')
@click.pass_context 
def check_github(ctx, repo_url: str, validate: bool):
    """Check a GitHub repository created by QuantumLayer"""
    
    client = ctx.obj['client']
    
    try:
        asyncio.run(_check_github_repo(client, repo_url, validate))
    except Exception as e:
        console.print(f"[red]Error checking GitHub repo:[/] {e}")
        sys.exit(1)


async def _check_github_repo(client: QLPClient, repo_url: str, validate: bool):
    """Check GitHub repository implementation"""
    
    # Parse GitHub URL
    import re
    match = re.match(r'https://github.com/([^/]+)/([^/]+)', repo_url)
    if not match:
        console.print("[red]Invalid GitHub URL format[/]")
        console.print("Expected: https://github.com/owner/repo")
        return
    
    owner, repo = match.groups()
    repo = repo.rstrip('.git')
    
    with console.status(f"Checking repository {owner}/{repo}..."):
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # Check if repo exists using GitHub API
            response = await http_client.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            
            if response.status_code == 404:
                console.print(f"[red]Repository not found:[/] {owner}/{repo}")
                return
            elif response.status_code != 200:
                console.print(f"[red]GitHub API error:[/] {response.status_code}")
                return
            
            repo_data = response.json()
    
    # Display repository info
    info_table = Table(show_header=False, box=None)
    info_table.add_column(style="cyan", width=20)
    info_table.add_column(style="white")
    
    info_table.add_row("Repository", f"{owner}/{repo}")
    info_table.add_row("Description", repo_data.get('description', 'No description'))
    info_table.add_row("Language", repo_data.get('language', 'Unknown'))
    info_table.add_row("Stars", str(repo_data.get('stargazers_count', 0)))
    info_table.add_row("Created", repo_data.get('created_at', 'Unknown'))
    info_table.add_row("Last Updated", repo_data.get('updated_at', 'Unknown'))
    info_table.add_row("Default Branch", repo_data.get('default_branch', 'main'))
    
    console.print(Panel(
        info_table,
        title="[bold]🐙 GitHub Repository[/]",
        border_style="blue"
    ))
    
    # Check for QuantumLayer metadata
    with console.status("Checking for QuantumLayer metadata..."):
        # Try to fetch qlp-metadata.json
        metadata_response = await http_client.get(
            f"https://raw.githubusercontent.com/{owner}/{repo}/{repo_data.get('default_branch', 'main')}/qlp-metadata.json"
        )
        
        if metadata_response.status_code == 200:
            console.print("\n[green]✅ QuantumLayer metadata found![/]")
            
            if validate:
                metadata = metadata_response.json()
                
                # Show generation info
                gen_table = Table(title="Generation Details", show_header=False)
                gen_table.add_column(style="cyan")
                gen_table.add_column(style="white")
                
                gen_table.add_row("Capsule ID", metadata.get('capsule_id', 'Unknown'))
                gen_table.add_row("Generated At", metadata.get('generated_at', 'Unknown'))
                gen_table.add_row("Platform Version", metadata.get('platform_version', 'Unknown'))
                
                console.print("\n")
                console.print(gen_table)
        else:
            console.print("\n[yellow]⚠️  No QuantumLayer metadata found[/]")
            console.print("[dim]This may not be a QuantumLayer-generated repository[/]")
    
    # Show repository structure
    console.print(f"\n[bold]View repository:[/] {repo_url}")
    console.print(f"[bold]Clone:[/] git clone {repo_url}.git")


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