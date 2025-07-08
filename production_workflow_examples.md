# Pattern Selection in Production Workflows - Usage Examples

## 🎯 How Pattern Selection Works in Temporal Workflows

The intelligent pattern selection engine is **automatically integrated** into all production workflows. Here's how to use it:

## 1️⃣ Complete End-to-End Workflow (Recommended)

```bash
# Full Temporal workflow with automatic pattern selection
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "id": "my-project-001",
    "tenant_id": "production",
    "user_id": "developer",
    "description": "Build a real-time chat application with WebSocket support",
    "requirements": "WebSocket, user authentication, message history, file sharing",
    "constraints": {"performance": "high", "scalability": "required"},
    "metadata": {"priority": "high", "complexity": "medium"}
  }'
```

**What Happens:**
- Temporal workflow starts automatically
- Pattern selection analyzes request characteristics  
- Selects optimal reasoning patterns (e.g., abstraction, semantic, constraint)
- Creates better task decomposition
- Executes with Agent Factory (T0-T3 agents)
- Validates with Validation Mesh
- Generates final QLCapsule

## 2️⃣ Direct Pattern-Enhanced Decomposition

```bash
# See pattern selection in action
curl -X POST http://localhost:8000/decompose/enhanced \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a machine learning model for fraud detection",
    "tenant_id": "enterprise",
    "user_id": "data_scientist"
  }'
```

**Benefits:**
- Shows which patterns were selected
- Explains reasoning for pattern choices
- Provides optimized task breakdown
- Includes pattern confidence scores

## 3️⃣ Pattern Analysis (For Debugging/Understanding)

```bash
# Analyze what patterns would be selected
curl -X POST http://localhost:8000/patterns/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Optimize database performance for high-traffic website",
    "context": {"domain": "performance", "constraints": ["existing_schema"]},
    "max_patterns": 3,
    "budget_constraint": 2.0
  }'
```

## 4️⃣ Complete Pipeline with Enhanced Capsule

```bash
# Generate production-ready code with pattern selection
curl -X POST http://localhost:8000/generate/complete-pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "id": "pipeline-001",
    "tenant_id": "production",
    "user_id": "engineer", 
    "description": "Create a REST API for inventory management",
    "metadata": {"target_score": 0.90, "save_to_disk": true}
  }'
```

## 🎪 Pattern Selection Integration Points

### In MetaOrchestrator (Automatic)
```python
# This happens automatically in all workflows:
async def decompose_request(self, request: ExecutionRequest):
    # 1. Analyze request characteristics
    characteristics = await self.pattern_selector.analyze_request_characteristics(...)
    
    # 2. Get optimal pattern recommendations  
    recommendations = await self.pattern_selector.recommend_patterns(...)
    
    # 3. Run targeted analysis with selected patterns
    analysis = await self.extended_nlp.targeted_analysis(..., selected_patterns)
    
    # 4. Generate enhanced task decomposition
    return await self._decompose_with_pattern_selection(...)
```

### In Temporal Workflow (Automatic)
```python
# Step 2 of QLPExecutionWorkflow automatically uses pattern selection:
decomposition = await workflow.execute_activity(
    decompose_request_activity,  # ← Uses MetaOrchestrator with pattern selection
    {"request": request, "similar_executions": similar_executions}
)
```

## 📊 Benefits in Production

### Before Pattern Selection
- Ran ALL 8 reasoning patterns (cost: ~5.5 units)
- Processing time: 3-4 minutes
- Generic task decomposition
- Higher computational overhead

### After Pattern Selection  
- Runs 2-4 optimal patterns (cost: ~1.5-2.5 units)
- Processing time: 1-2 minutes  
- Targeted, high-quality task decomposition
- 60-70% efficiency improvement

## 🎯 When to Use Each Endpoint

| Use Case | Endpoint | Pattern Selection |
|----------|----------|-------------------|
| **Production deployment** | `POST /execute` | ✅ Automatic |
| **Code generation** | `POST /generate/capsule` | ✅ Automatic |
| **Complete pipeline** | `POST /generate/complete-pipeline` | ✅ Automatic |
| **Debug decomposition** | `POST /decompose/enhanced` | ✅ Visible |
| **Understand patterns** | `POST /patterns/recommend` | ✅ Direct |
| **Simple testing** | `POST /test/decompose` | ❌ Not yet integrated |

## 🚀 Production Workflow Status

Check any workflow status:
```bash
curl http://localhost:8000/status/{workflow_id}
```

View Temporal UI:
```
http://localhost:8088
```

## 💡 Key Takeaway

**Pattern selection is automatically integrated into all production workflows.** You don't need to do anything special - just use the regular endpoints and get:

- ✅ 60-70% efficiency improvement
- ✅ Better task quality  
- ✅ Faster execution
- ✅ Intelligent pattern selection
- ✅ Complete transparency

The system now intelligently answers **"which pattern to use for what?"** for every single request automatically!