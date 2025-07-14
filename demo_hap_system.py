#!/usr/bin/env python3
"""
Interactive HAP System Demo
Shows the HAP system in action with real examples
"""

import asyncio
import json
from datetime import datetime
from colorama import init, Fore, Style
import sys

# Initialize colorama for colored output
init()

# Add src to path
sys.path.insert(0, '.')

from src.moderation import (
    hap_service, check_content, 
    CheckContext, Severity, Category
)


def print_header(text):
    """Print colored header"""
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{text}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")


def print_result(result):
    """Print HAP check result with colors"""
    # Color based on severity
    severity_colors = {
        Severity.CLEAN: Fore.GREEN,
        Severity.LOW: Fore.YELLOW,
        Severity.MEDIUM: Fore.YELLOW,
        Severity.HIGH: Fore.RED,
        Severity.CRITICAL: Fore.MAGENTA
    }
    
    color = severity_colors.get(result.severity, Fore.WHITE)
    
    print(f"📊 {Fore.WHITE}Result:{Style.RESET_ALL} {color}{result.result}{Style.RESET_ALL}")
    print(f"⚠️  {Fore.WHITE}Severity:{Style.RESET_ALL} {color}{result.severity}{Style.RESET_ALL}")
    
    if result.categories:
        cats = ", ".join([cat.value for cat in result.categories])
        print(f"🏷️  {Fore.WHITE}Categories:{Style.RESET_ALL} {cats}")
    
    print(f"🎯 {Fore.WHITE}Confidence:{Style.RESET_ALL} {result.confidence:.2%}")
    
    if result.explanation:
        print(f"💬 {Fore.WHITE}Explanation:{Style.RESET_ALL} {result.explanation}")
    
    if result.suggestions:
        print(f"💡 {Fore.WHITE}Suggestions:{Style.RESET_ALL} {Fore.BLUE}{result.suggestions}{Style.RESET_ALL}")
    
    print(f"⚡ {Fore.WHITE}Processing time:{Style.RESET_ALL} {result.processing_time_ms:.2f}ms")


async def demo_basic_checks():
    """Demo 1: Basic content checking"""
    print_header("Demo 1: Basic Content Checking")
    
    # Initialize service
    await hap_service.initialize()
    
    examples = [
        ("Clean request", "Please write a Python function to sort a list"),
        ("Mild profanity", "This damn bug is driving me crazy"),
        ("Disguised profanity", "Fix this sh*t before the deadline"),
        ("Technical terms", "Use kill -9 to terminate the process"),
        ("Threat (joking)", "I'll hurt anyone who uses tabs instead of spaces"),
        ("Harassment", "You're an idiot if you can't understand this code")
    ]
    
    for title, content in examples:
        print(f"\n{Fore.YELLOW}Testing:{Style.RESET_ALL} {title}")
        print(f"{Fore.WHITE}Content:{Style.RESET_ALL} \"{content}\"\n")
        
        result = await check_content(
            content=content,
            context=CheckContext.USER_REQUEST,
            user_id="demo_user",
            tenant_id="demo_tenant"
        )
        
        print_result(result)
        print("-" * 40)
        
        # Small delay for readability
        await asyncio.sleep(0.5)


async def demo_context_sensitivity():
    """Demo 2: Context-aware checking"""
    print_header("Demo 2: Context Sensitivity")
    
    test_content = "The function will kill all child processes"
    
    contexts = [
        (CheckContext.USER_REQUEST, "User Request"),
        (CheckContext.AGENT_OUTPUT, "Agent Output"),
        (CheckContext.CAPSULE_CONTENT, "Capsule Content")
    ]
    
    print(f"{Fore.WHITE}Testing same content in different contexts:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Content:{Style.RESET_ALL} \"{test_content}\"\n")
    
    for context, name in contexts:
        print(f"\n{Fore.YELLOW}Context:{Style.RESET_ALL} {name}")
        
        result = await check_content(
            content=test_content,
            context=context
        )
        
        print(f"Severity: {result.severity}")
        print(f"Categories: {[cat.value for cat in result.categories]}")


async def demo_agent_filtering():
    """Demo 3: Agent output filtering"""
    print_header("Demo 3: Agent Output Filtering")
    
    from src.agents.hap_filtered_agent import HAPFilteredAgent
    from src.agents.base_agents import BaseAgent
    from src.common.models import Task, TaskResult, AgentType
    
    # Create a mock agent that sometimes generates inappropriate content
    class MockAgent(BaseAgent):
        async def execute(self, task: Task) -> TaskResult:
            responses = {
                "angry": "This damn code is broken as hell! What idiot wrote this crap?",
                "threat": "I'll destroy anyone who doesn't follow coding standards",
                "clean": "Here's a well-structured implementation of your request",
                "technical": "The process killer will terminate all running instances"
            }
            
            # Choose response based on task description
            for key in responses:
                if key in task.description.lower():
                    output = responses[key]
                    break
            else:
                output = responses["clean"]
            
            return TaskResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                output=output,
                status="completed",
                execution_time=0.1,
                metadata={}
            )
    
    # Create base and filtered agents
    base_agent = MockAgent(
        agent_id="demo-agent",
        agent_type=AgentType.DEVELOPER,
        tier=1
    )
    
    filtered_agent = HAPFilteredAgent(base_agent, strict_mode=True)
    
    # Test scenarios
    scenarios = [
        ("clean task", "Write a clean function"),
        ("angry task", "Fix the angry developer's code"),
        ("threat task", "Handle threat detection"),
        ("technical task", "Implement technical process management")
    ]
    
    for name, description in scenarios:
        print(f"\n{Fore.YELLOW}Scenario:{Style.RESET_ALL} {name}")
        print(f"{Fore.WHITE}Task:{Style.RESET_ALL} {description}")
        
        task = Task(
            task_id=f"demo-{name}",
            description=description,
            agent_type=AgentType.DEVELOPER,
            metadata={"user_id": "demo_user"}
        )
        
        # Execute without filtering
        print(f"\n{Fore.BLUE}Without HAP filtering:{Style.RESET_ALL}")
        base_result = await base_agent.execute(task)
        print(f"Output: {base_result.output}")
        
        # Execute with filtering
        print(f"\n{Fore.GREEN}With HAP filtering:{Style.RESET_ALL}")
        filtered_result = await filtered_agent.execute(task)
        print(f"Output: {filtered_result.output}")
        
        if filtered_result.metadata.get('hap_filtered'):
            print(f"{Fore.YELLOW}⚠️  Content was filtered!{Style.RESET_ALL}")
        
        print("-" * 60)


async def demo_batch_processing():
    """Demo 4: Batch processing performance"""
    print_header("Demo 4: Batch Processing Performance")
    
    # Create batch of mixed content
    batch_items = [
        "Implement user authentication",
        "This code is terrible",
        "Kill the background process",
        "What the hell is this function doing?",
        "Create REST API endpoints",
        "Fix this sh*t ASAP",
        "Deploy to production server",
        "This is spam spam spam",
        "Normal technical documentation",
        "I hate this framework"
    ]
    
    print(f"Processing {len(batch_items)} items...\n")
    
    # Process individually (for comparison)
    start_time = asyncio.get_event_loop().time()
    individual_results = []
    for item in batch_items:
        result = await check_content(item)
        individual_results.append(result)
    individual_time = asyncio.get_event_loop().time() - start_time
    
    # Process in batch
    start_time = asyncio.get_event_loop().time()
    batch_tasks = [check_content(item) for item in batch_items]
    batch_results = await asyncio.gather(*batch_tasks)
    batch_time = asyncio.get_event_loop().time() - start_time
    
    # Show results
    print(f"{Fore.WHITE}Results Summary:{Style.RESET_ALL}")
    severities = {}
    for i, (content, result) in enumerate(zip(batch_items, batch_results)):
        severity = result.severity
        severities[severity] = severities.get(severity, 0) + 1
        
        color = Fore.GREEN if severity == Severity.CLEAN else Fore.YELLOW
        if severity in [Severity.HIGH, Severity.CRITICAL]:
            color = Fore.RED
            
        print(f"{i+1:2d}. [{color}{severity:8s}{Style.RESET_ALL}] {content[:50]}...")
    
    print(f"\n{Fore.WHITE}Performance Comparison:{Style.RESET_ALL}")
    print(f"Sequential processing: {individual_time*1000:.2f}ms")
    print(f"Batch processing: {batch_time*1000:.2f}ms")
    print(f"Speed improvement: {individual_time/batch_time:.1f}x faster")
    
    print(f"\n{Fore.WHITE}Severity Distribution:{Style.RESET_ALL}")
    for severity, count in severities.items():
        print(f"{severity}: {count} items")


async def demo_real_world_scenario():
    """Demo 5: Real-world integration scenario"""
    print_header("Demo 5: Real-World Scenario - Code Review Request")
    
    # Simulate a complete workflow
    print(f"{Fore.WHITE}Scenario:{Style.RESET_ALL} User submits a code review request\n")
    
    # Step 1: User request
    user_request = """
    Review this crappy code and tell me why it's so damn slow.
    The previous developer was an idiot who didn't know what they were doing.
    I need this fixed ASAP or I'll be really pissed off.
    """
    
    print(f"{Fore.YELLOW}Step 1: Check user request{Style.RESET_ALL}")
    print(f"Original request: {user_request.strip()}\n")
    
    request_result = await check_content(
        content=user_request,
        context=CheckContext.USER_REQUEST,
        user_id="frustrated_dev",
        tenant_id="acme_corp"
    )
    
    print_result(request_result)
    
    if request_result.severity >= Severity.MEDIUM:
        print(f"\n{Fore.YELLOW}Request needs cleaning...{Style.RESET_ALL}")
        cleaned_request = """
        Review this code and identify performance issues.
        The code has quality problems that need addressing.
        This is urgent and needs immediate attention.
        """
        print(f"Cleaned request: {cleaned_request.strip()}")
    
    # Step 2: Agent response
    print(f"\n\n{Fore.YELLOW}Step 2: Check agent response{Style.RESET_ALL}")
    
    agent_response = """
    I've reviewed the code and found several issues:
    
    1. The damn database queries are not optimized
    2. There's a stupid n+1 query problem in the loop
    3. The idiot who wrote this didn't use indexes
    
    Here's how to fix this crap:
    - Add proper indexes
    - Use batch queries
    - Implement caching
    """
    
    print(f"Agent response: {agent_response.strip()}\n")
    
    response_result = await check_content(
        content=agent_response,
        context=CheckContext.AGENT_OUTPUT
    )
    
    print_result(response_result)
    
    if response_result.severity >= Severity.MEDIUM:
        print(f"\n{Fore.YELLOW}Response needs filtering...{Style.RESET_ALL}")
        filtered_response = """
        I've reviewed the code and found several issues:
        
        1. The database queries are not optimized
        2. There's an n+1 query problem in the loop
        3. The code lacks proper database indexes
        
        Here's how to fix these issues:
        - Add proper indexes
        - Use batch queries
        - Implement caching
        """
        print(f"Filtered response: {filtered_response.strip()}")
    
    # Step 3: Final capsule
    print(f"\n\n{Fore.YELLOW}Step 3: Validate final capsule{Style.RESET_ALL}")
    
    final_capsule = """
    Code Review Results:
    
    Performance Issues Identified:
    - Unoptimized database queries
    - N+1 query problem
    - Missing database indexes
    
    Recommended Solutions:
    - Add indexes on frequently queried columns
    - Implement batch query processing
    - Add Redis caching layer
    
    This will improve performance by approximately 10x.
    """
    
    capsule_result = await check_content(
        content=final_capsule,
        context=CheckContext.CAPSULE_CONTENT
    )
    
    print(f"Final capsule content validated:")
    print_result(capsule_result)
    
    print(f"\n{Fore.GREEN}✅ Workflow completed with content safety!{Style.RESET_ALL}")


async def interactive_mode():
    """Interactive testing mode"""
    print_header("Interactive HAP Testing")
    
    print("Enter text to check (or 'quit' to exit):\n")
    
    while True:
        try:
            # Get user input
            text = input(f"{Fore.CYAN}> {Style.RESET_ALL}")
            
            if text.lower() in ['quit', 'exit', 'q']:
                break
            
            if not text.strip():
                continue
            
            # Check content
            result = await check_content(
                content=text,
                context=CheckContext.USER_REQUEST
            )
            
            print()
            print_result(result)
            print()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")


async def main():
    """Run all demos"""
    print(f"{Fore.MAGENTA}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║           HAP System Live Demonstration                   ║")
    print("║     Hate, Abuse & Profanity Detection in Action         ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Style.RESET_ALL}")
    
    # Menu
    while True:
        print(f"\n{Fore.CYAN}Select a demo:{Style.RESET_ALL}")
        print("1. Basic Content Checking")
        print("2. Context Sensitivity")
        print("3. Agent Output Filtering")
        print("4. Batch Processing Performance")
        print("5. Real-World Scenario")
        print("6. Interactive Mode")
        print("7. Run All Demos")
        print("0. Exit")
        
        choice = input(f"\n{Fore.CYAN}Enter choice (0-7): {Style.RESET_ALL}")
        
        try:
            if choice == '0':
                break
            elif choice == '1':
                await demo_basic_checks()
            elif choice == '2':
                await demo_context_sensitivity()
            elif choice == '3':
                await demo_agent_filtering()
            elif choice == '4':
                await demo_batch_processing()
            elif choice == '5':
                await demo_real_world_scenario()
            elif choice == '6':
                await interactive_mode()
            elif choice == '7':
                # Run all demos
                await demo_basic_checks()
                await demo_context_sensitivity()
                await demo_agent_filtering()
                await demo_batch_processing()
                await demo_real_world_scenario()
            else:
                print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}Demo error: {e}{Style.RESET_ALL}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{Fore.GREEN}Thank you for exploring the HAP system!{Style.RESET_ALL}")


if __name__ == "__main__":
    asyncio.run(main())