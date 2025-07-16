# Agent Tier Override Feature

## Overview

The Quantum Layer Platform (QLP) now supports explicit agent tier selection through the `tier_override` parameter. This allows users to force specific agent tiers (T0, T1, T2, T3) for their tasks, overriding the automatic tier selection system.

## How It Works

### Automatic Tier Selection (Default)
By default, QLP automatically selects the appropriate agent tier based on:
1. **Historical Performance Data**: Analyzes similar past tasks and their success rates
2. **Task Complexity**: Falls back to complexity-based mapping if no historical data exists
   - `trivial` → T0
   - `simple` → T0
   - `medium` → T1
   - `complex` → T2
   - `meta` → T3

### Manual Tier Override
You can now override this automatic selection by specifying a `tier_override` in your execution request.

## API Usage

### Request Structure

```json
POST /execute
{
  "tenant_id": "your-tenant-id",
  "user_id": "your-user-id",
  "description": "Your task description",
  "requirements": "Optional requirements",
  "tier_override": "T3"  // Force T3 tier for all tasks
}
```

### Available Tiers

- **T0**: Simple task execution (Llama 3 8B, GPT-3.5-turbo)
- **T1**: Context-aware generation (GPT-4-mini, Claude Sonnet)
- **T2**: Reasoning + validation loops (GPT-4-turbo, Claude 3.5 Sonnet)
- **T3**: Meta-agents that spawn sub-agents (GPT-4.1, Claude Opus)

## Examples

### Example 1: Force T3 for Complex Architecture

```python
import httpx
import asyncio

async def create_complex_system():
    request = {
        "tenant_id": "enterprise-tenant",
        "user_id": "architect-user",
        "description": """
        Create a complete microservices architecture for an e-commerce platform with:
        - User service with authentication
        - Product catalog service
        - Shopping cart service
        - Order processing service
        - Payment integration
        - API Gateway
        - Service discovery
        - Load balancing
        - Monitoring and logging
        """,
        "requirements": "Production-ready code with comprehensive error handling",
        "tier_override": "T3"  # Ensure meta-agent handles this complex task
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/execute", json=request)
        result = response.json()
        print(f"Workflow started: {result['workflow_id']}")

asyncio.run(create_complex_system())
```

### Example 2: Force T0 for Cost Optimization

```python
# Use T0 for simple tasks to minimize costs
simple_request = {
    "tenant_id": "budget-tenant",
    "user_id": "developer",
    "description": "Create a function to reverse a string",
    "tier_override": "T0"  # Force cheapest tier
}
```

### Example 3: Force T2 for Quality Assurance

```python
# Use T2 for tasks requiring validation loops
qa_request = {
    "tenant_id": "qa-tenant",
    "user_id": "qa-engineer",
    "description": "Create a REST API endpoint with comprehensive error handling",
    "requirements": "Must pass all security and performance validations",
    "tier_override": "T2"  # Ensure validation loops are used
}
```

## Implementation Details

### 1. Request Flow
1. User submits request with `tier_override` parameter
2. Orchestrator passes tier override to decomposition activity
3. All tasks inherit the tier override in their metadata
4. Agent tier selection activity checks for override before automatic selection

### 2. Override Precedence
The system checks for tier override in this order:
1. Task metadata `tier_override`
2. Task context `preferred_tier`
3. Historical performance data (if no override)
4. Complexity-based fallback (if no data)

### 3. Cost Implications

| Tier | Approximate Cost per Task | Use Case |
|------|--------------------------|----------|
| T0   | $0.00005 - $0.0001      | Simple transformations, basic code |
| T1   | $0.001 - $0.01          | Standard features, API endpoints |
| T2   | $0.01 - $0.05           | Complex algorithms, validated code |
| T3   | $0.05 - $0.20           | System architecture, recursive solutions |

## Best Practices

### When to Use Tier Override

1. **Force T3 When:**
   - Building complex multi-component systems
   - Need recursive problem decomposition
   - Require meta-cognitive analysis
   - Working on system architecture

2. **Force T2 When:**
   - Code quality is critical
   - Need validation and refinement loops
   - Working on algorithms or optimization
   - Security-sensitive implementations

3. **Force T1 When:**
   - Standard feature development
   - Need context-aware generation
   - Working with existing patterns
   - Balance of cost and quality

4. **Force T0 When:**
   - Simple code generation
   - Cost optimization is priority
   - Trivial transformations
   - High-volume simple tasks

### Performance Considerations

- **T3 Performance**: T3 spawns sub-agents (T0, T1, T2), so execution time varies based on task decomposition
- **Parallel Execution**: Multiple T0/T1 tasks can run in parallel for better performance
- **Cost vs Quality**: Higher tiers provide better quality but at increased cost and time

## Monitoring Tier Usage

After execution, check which tiers were used:

```python
# Get workflow status
status_response = await client.get(f"http://localhost:8000/workflow/status/{workflow_id}")
result = status_response.json()

# Check tier usage in outputs
for output in result["result"]["outputs"]:
    agent_tier = output["execution"]["agent_tier"]
    task_id = output["task"]["task_id"]
    print(f"Task {task_id} used tier: {agent_tier}")
```

## Future Enhancements

1. **Granular Control**: Per-task tier override instead of global
2. **Dynamic Override**: Change tier based on execution progress
3. **Cost Limits**: Automatically downgrade tier if cost exceeds budget
4. **Smart Routing**: ML-based tier recommendation system

## Conclusion

The tier override feature provides fine-grained control over agent selection, allowing you to optimize for cost, quality, or specific capabilities based on your requirements. Use it wisely to balance performance, cost, and output quality.