# Cost Tracking Authentication Guide

## Overview

The QLP platform uses Clerk for authentication. All cost tracking endpoints require valid authentication tokens.

## Quick Start

### 1. Get a Clerk Token

#### Option A: Using Clerk Dashboard (Easiest for Testing)
1. Go to [Clerk Dashboard](https://dashboard.clerk.com)
2. Navigate to your application → Users
3. Create or select a test user
4. Click "Impersonate user" to get a session token
5. Copy the JWT token from the developer tools

#### Option B: Using Clerk CLI
```bash
# Install Clerk CLI
npm install -g @clerk/clerk-cli

# Login
clerk login

# Create a session for a user
clerk sessions create --user-id user_123

# Get the token
clerk sessions get-token SESSION_ID
```

#### Option C: From Your Frontend App
```javascript
// In your React app with Clerk
import { useAuth } from '@clerk/clerk-react';

function GetToken() {
  const { getToken } = useAuth();
  
  const handleGetToken = async () => {
    const token = await getToken();
    console.log('Token:', token);
    // Copy from console
  };
  
  return <button onClick={handleGetToken}>Get Token</button>;
}
```

### 2. Test the Endpoints

```bash
# Set your token
export AUTH_TOKEN="your-clerk-token-here"

# Test cost estimation
curl -H "Authorization: Bearer $AUTH_TOKEN" \
     "http://localhost:8000/api/v2/costs/estimate?complexity=medium&tech_stack=Python&tech_stack=FastAPI"

# Get cost report
curl -H "Authorization: Bearer $AUTH_TOKEN" \
     "http://localhost:8000/api/v2/costs?period_days=7"

# Get costs for specific workflow
curl -H "Authorization: Bearer $AUTH_TOKEN" \
     "http://localhost:8000/api/v2/costs?workflow_id=WORKFLOW_ID"
```

## Production Setup

### 1. Environment Configuration

```bash
# .env file
CLERK_SECRET_KEY=sk_live_...
CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_JWKS_URL=https://your-app.clerk.accounts.dev/.well-known/jwks.json
```

### 2. User Metadata

Configure user metadata in Clerk dashboard for proper tenant association:

```json
{
  "public_metadata": {
    "organization_id": "org_123",
    "role": "developer",
    "permissions": ["costs:read", "metrics:read"]
  }
}
```

### 3. Frontend Integration

```typescript
// TypeScript/React example
import { useAuth } from '@clerk/clerk-react';
import { useState, useEffect } from 'react';

interface CostReport {
  total_requests: number;
  total_cost_usd: number;
  model_breakdown: Record<string, any>;
}

function CostDashboard() {
  const { getToken } = useAuth();
  const [costs, setCosts] = useState<CostReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCosts();
  }, []);

  const fetchCosts = async () => {
    try {
      const token = await getToken();
      const response = await fetch('/api/v2/costs?period_days=30', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setCosts(data.data);
      }
    } catch (error) {
      console.error('Failed to fetch costs:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading costs...</div>;
  
  return (
    <div>
      <h2>Cost Report</h2>
      {costs && (
        <>
          <p>Total Requests: {costs.total_requests}</p>
          <p>Total Cost: ${costs.total_cost_usd.toFixed(6)}</p>
          {/* Render model breakdown */}
        </>
      )}
    </div>
  );
}
```

### 4. Backend Middleware

The authentication is already implemented in `src/common/clerk_auth.py`:

```python
from src.common.clerk_auth import get_current_user, require_permission

# Protected endpoint example
@router.get("/api/v2/costs")
async def get_costs(
    user: Dict[str, Any] = Depends(get_current_user)
):
    # user contains:
    # - user_id: Clerk user ID
    # - organization_id: User's organization (used as tenant_id)
    # - permissions: User's permissions
    tenant_id = user.get("organization_id")
    # Query costs for this tenant
```

## Direct Database Access (No Auth Required)

For internal monitoring or debugging, you can query the database directly:

```bash
# Run the verification script
./verify_cost_data.sh

# Or run specific queries
docker exec qlp-postgres psql -U qlp_user -d qlp_db -c "
  SELECT 
    tenant_id,
    DATE(created_at) as date,
    SUM(total_cost_usd) as daily_cost
  FROM llm_usage
  WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
  GROUP BY tenant_id, DATE(created_at)
  ORDER BY date DESC, daily_cost DESC;"
```

## API Endpoints

### 1. Cost Estimation
```
GET /api/v2/costs/estimate
```
Parameters:
- `complexity`: trivial, simple, medium, complex, very_complex
- `tech_stack`: Array of technologies

### 2. Cost Report
```
GET /api/v2/costs
```
Parameters:
- `workflow_id`: Filter by specific workflow
- `period_days`: Number of days to look back (default: 30)

Response:
```json
{
  "success": true,
  "data": {
    "tenant_id": "org_123",
    "total_requests": 150,
    "total_input_tokens": 125000,
    "total_output_tokens": 45000,
    "total_cost_usd": 2.4567,
    "model_breakdown": {
      "azure_openai/gpt-3.5-turbo": {
        "count": 100,
        "cost_usd": 0.5432
      },
      "azure_openai/gpt-4": {
        "count": 50,
        "cost_usd": 1.9135
      }
    }
  }
}
```

### 3. Metrics (Requires metrics:read permission)
```
GET /api/v2/metrics
```

## Troubleshooting

### 401 Unauthorized
- Check that your token is valid and not expired
- Verify CLERK_SECRET_KEY is set correctly
- Check token format: `Authorization: Bearer <token>`

### 403 Forbidden
- User lacks required permissions
- For metrics endpoint, user needs `metrics:read` permission

### No Cost Data
- Costs are tracked asynchronously, wait 2-3 seconds after workflow completion
- Check workflow_id format (might be without "qlp-execution-" prefix in database)
- Verify tenant_id matches user's organization_id

## Security Best Practices

1. **Token Rotation**: Implement regular token rotation
2. **Permissions**: Use granular permissions for different endpoints
3. **Rate Limiting**: Endpoints are rate-limited (60/minute for costs)
4. **Audit Logging**: All API access is logged with user context
5. **HTTPS Only**: Always use HTTPS in production

## Support

For issues with:
- **Authentication**: Check Clerk dashboard logs
- **Cost Data**: Run `./verify_cost_data.sh` to check database
- **API Errors**: Check Docker logs: `docker logs qlp-orchestrator`