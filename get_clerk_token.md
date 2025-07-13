# How to Get a Valid Clerk Token for Testing

## Your Clerk Dashboard

Based on your credentials, your Clerk dashboard is at:
https://dashboard.clerk.com/apps/knowing-pigeon-89/instances/development

## Steps to Get a Token

### Method 1: Using Clerk Dashboard (Easiest)

1. **Go to your Clerk Dashboard**:
   ```
   https://dashboard.clerk.com/apps/knowing-pigeon-89/instances/development
   ```

2. **Create a Test User**:
   - Navigate to "Users" in the left sidebar
   - Click "Create user"
   - Fill in:
     - Email: test@quantumlayer.com
     - Password: TestPassword123!
   - Click "Create"

3. **Set User Metadata** (Important for tenant association):
   - Click on the created user
   - Go to "Metadata" tab
   - Add to Public metadata:
   ```json
   {
     "organization_id": "org_test_123",
     "permissions": ["costs:read", "metrics:read"]
   }
   ```
   - Save changes

4. **Get the Token**:
   - On the user's page, click "Impersonate user"
   - This opens a new tab with your app
   - Open browser DevTools (F12)
   - Go to Network tab
   - Look for any API call
   - Find the Authorization header
   - Copy the token (everything after "Bearer ")

### Method 2: Using Clerk's Session API

```bash
# Create a session
curl -X POST https://api.clerk.com/v1/sessions \
  -H "Authorization: Bearer sk_test_s8sHdFfUq3ZTHBaXHTdKXxZq6ssVmBdu5b1oYJCGf0" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "YOUR_USER_ID",
    "expires_in_seconds": 3600
  }'

# The response will include a client token
```

### Method 3: Create a Simple Test Page

Create `test-clerk.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Get Clerk Token</title>
    <script src="https://knowing-pigeon-89.clerk.accounts.dev/npm/@clerk/clerk-js@latest/dist/clerk.browser.js"></script>
</head>
<body>
    <div id="app">
        <h1>Clerk Token Getter</h1>
        <div id="sign-in"></div>
        <button id="get-token" style="display:none">Get Token</button>
        <pre id="token"></pre>
    </div>

    <script>
        const clerkPublishableKey = 'pk_test_a25vd24tcGlnZW9uLTg5LmNsZXJrLmFjY291bnRzLmRldiQ';
        
        const clerk = new Clerk(clerkPublishableKey);
        
        clerk.load().then(() => {
            if (clerk.user) {
                document.getElementById('get-token').style.display = 'block';
            } else {
                clerk.mountSignIn(document.getElementById('sign-in'));
            }
        });
        
        document.getElementById('get-token').addEventListener('click', async () => {
            const token = await clerk.session.getToken();
            document.getElementById('token').textContent = 'Token: ' + token;
            console.log('Token:', token);
            
            // Also show how to use it
            console.log('Use this token in your tests:');
            console.log(`curl -H "Authorization: Bearer ${token}" http://localhost:8000/api/v2/costs`);
        });
        
        clerk.addListener(() => {
            if (clerk.user) {
                document.getElementById('sign-in').style.display = 'none';
                document.getElementById('get-token').style.display = 'block';
            }
        });
    </script>
</body>
</html>
```

Open this file in a browser and sign in to get a token.

## Testing with the Token

Once you have a real token:

```bash
# Test cost estimation
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     "http://localhost:8000/api/v2/costs/estimate?complexity=medium&tech_stack=Python"

# Get cost report
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     "http://localhost:8000/api/v2/costs?period_days=7"

# Or use the Python script
python test_cost_with_clerk.py --token "YOUR_TOKEN_HERE"
```

## Direct Database Verification (No Auth Needed)

While setting up authentication, you can always verify costs directly:

```bash
# Check all costs
./verify_cost_data.sh

# Check specific tenant
docker exec qlp-postgres psql -U qlp_user -d qlp_db -c "
  SELECT * FROM llm_usage 
  WHERE tenant_id = 'org_test_123' 
  ORDER BY created_at DESC 
  LIMIT 10;"
```

## Important Notes

1. The `organization_id` in user metadata becomes the `tenant_id` for cost tracking
2. Workflow IDs in the database don't include the "qlp-execution-" prefix
3. Costs are tracked asynchronously (2-3 second delay after workflow completion)
4. Make sure your Clerk application is in Development mode for testing