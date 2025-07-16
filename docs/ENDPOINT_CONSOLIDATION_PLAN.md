# Endpoint Consolidation Implementation Plan

## Overview

This document outlines the plan to consolidate 56+ endpoints down to ~10 core endpoints, making the API simpler and more maintainable.

## Current State Analysis

### Endpoint Categories
1. **Code Generation** (6 endpoints) → Consolidate to 1
2. **Workflow Management** (4 endpoints) → Consolidate to 2
3. **Capsule Management** (12 endpoints) → Consolidate to 3
4. **HITL/AITL** (10 endpoints) → Consolidate to 2
5. **Analysis/Patterns** (11 endpoints) → Keep as optional advanced features
6. **GitHub Integration** (2 endpoints) → Integrate into main flow
7. **Marketing** (3 endpoints) → Keep separate (different domain)
8. **System** (2 endpoints) → Keep as-is

## Implementation Phases

### Phase 1: Create Unified API (Completed ✅)

**What we've done:**
1. Created `/v2/execute` endpoint that replaces:
   - `/execute`
   - `/generate/capsule`
   - `/generate/complete-with-github`
   - `/generate/complete-pipeline`
   - `/generate/robust-capsule`

2. Created unified workflow endpoints:
   - `/v2/workflows/{id}` - Get status
   - `/v2/workflows/{id}/result` - Get result
   - `/v2/workflows/{id}/cancel` - Cancel workflow

3. Added options-based configuration:
   ```json
   {
     "options": {
       "mode": "basic|complete|robust",
       "github": {...},
       "delivery": {...},
       "validation": {...}
     }
   }
   ```

### Phase 2: Add Deprecation Layer (In Progress 🔄)

**What we've done:**
1. Created deprecation middleware
2. Added warning headers to old endpoints
3. Created migration documentation

**Next steps:**
1. Apply deprecation decorator to all old endpoints
2. Add middleware to main.py
3. Update all endpoint documentation

### Phase 3: Update Documentation (TODO 📝)

1. **Update OpenAPI/Swagger:**
   - Mark old endpoints as deprecated
   - Highlight v2 endpoints as primary
   - Add migration examples

2. **Create Quick Start Guide:**
   - Focus on v2 endpoints only
   - Simple examples for common use cases
   - Link to migration guide for existing users

3. **Update all examples:**
   - README examples
   - Test scripts
   - Documentation snippets

### Phase 4: Client Library Updates (TODO 📦)

Create official client libraries with v2 support:

```python
# Python client example
from qlp import QLPClient

client = QLPClient(api_key="...")

# Simple usage
result = client.generate(
    "Create a REST API",
    mode="complete",
    github={"repo_name": "my-api"}
)

# Status checking
status = client.get_status(result.workflow_id)
```

### Phase 5: Internal Refactoring (TODO 🔧)

1. **Consolidate duplicate code:**
   - Merge similar endpoint implementations
   - Create shared utility functions
   - Remove redundant validation

2. **Simplify routing:**
   - Use single router for v2
   - Consistent parameter handling
   - Unified error responses

3. **Database cleanup:**
   - Single table for all workflows
   - Consistent status tracking
   - Remove duplicate fields

## Endpoint Mapping

### Before (56 endpoints) → After (10 endpoints)

#### Core Endpoints (Keep)
1. `POST /v2/execute` - Main entry point
2. `GET /v2/workflows/{id}` - Get status
3. `GET /v2/workflows/{id}/result` - Get result
4. `POST /v2/workflows/{id}/cancel` - Cancel
5. `GET /v2/capsules/{id}/download` - Download result
6. `GET /health` - Health check
7. `POST /v2/workflows/{id}/approve` - HITL approval
8. `GET /v2/workflows/{id}/logs` - Get logs

#### Optional Advanced Endpoints
9. `POST /v2/analyze` - Advanced analysis (for power users)
10. `POST /v2/patterns` - Pattern management (for ML features)

#### Remove/Deprecate (46 endpoints)
- All `/generate/*` variants
- Duplicate status endpoints
- Complex HITL endpoints
- Test endpoints
- Redundant capsule endpoints

## Benefits

### For Users
1. **Simpler API** - Learn one endpoint instead of many
2. **Consistent behavior** - All options work the same way
3. **Better documentation** - Focus on one clear path
4. **Easier integration** - Less code to write

### For Developers
1. **Less code to maintain** - 80% reduction in endpoint code
2. **Clearer architecture** - Single flow to understand
3. **Easier testing** - Test one path thoroughly
4. **Faster feature development** - Add options, not endpoints

## Metrics for Success

1. **API Usage**
   - 90% of requests use v2 endpoints within 3 months
   - 50% reduction in support tickets about "which endpoint to use"

2. **Developer Experience**
   - Time to first successful API call reduced by 50%
   - Client library adoption rate > 70%

3. **Maintenance**
   - 80% reduction in endpoint-related code
   - 60% faster to add new features

## Risk Mitigation

1. **Breaking Changes**
   - 6-month deprecation period
   - Automatic migration for common patterns
   - Clear migration guide with examples

2. **Feature Parity**
   - Ensure all v1 functionality available in v2
   - Extensive testing of migration paths
   - Beta period with select users

3. **Performance**
   - Benchmark v2 vs v1 performance
   - Optimize option parsing
   - Cache common configurations

## Timeline

- **Week 1-2**: Complete deprecation layer ✅
- **Week 3-4**: Update all documentation
- **Week 5-6**: Release client libraries
- **Week 7-8**: Internal refactoring
- **Month 3**: Beta release of v2
- **Month 4-5**: Migration period
- **Month 6**: Sunset v1 endpoints

## Next Immediate Steps

1. Add deprecation middleware to main.py
2. Update OpenAPI documentation
3. Create simple examples for v2
4. Test migration paths
5. Notify users of upcoming changes

## Code Snippets

### Adding Deprecation to Existing Endpoint
```python
from src.orchestrator.deprecation_middleware import create_deprecation_decorator

@app.post("/generate/capsule")
@create_deprecation_decorator(
    alternative="/v2/execute with options.mode='basic'",
    sunset_date="2025-07-01"
)
async def generate_capsule(request: ExecutionRequest):
    # Existing implementation
```

### Middleware Integration
```python
# In main.py
from src.orchestrator.deprecation_middleware import deprecation_middleware

app.add_middleware(deprecation_middleware)
```

## Conclusion

This consolidation will transform the QLP API from a complex 56-endpoint system to a simple, powerful 10-endpoint API. Users will have a clearer path to success, and developers will have a more maintainable codebase.