# 🚂 Railway Quick Start Guide for QLP

## 🎯 Goal: Deploy QLP in 30 Minutes

### Prerequisites
- Railway account (sign up at railway.app)
- GitHub account
- Your environment variables ready

## 🚀 Step 1: Quick Deploy (5 minutes)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Run our deployment script
./scripts/deploy-to-railway.sh
```

## 📋 Step 2: Environment Variables (10 minutes)

### Required Variables (Add in Railway Dashboard)

```env
# LLM (Pick one)
AZURE_OPENAI_ENDPOINT=https://your.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# GitHub (for code push)
GITHUB_TOKEN=ghp_your_token_here

# Security (Generate these)
JWT_SECRET=your-super-secret-jwt-key
REFRESH_SECRET=your-super-secret-refresh-key
```

### How to Add Variables

1. Go to Railway Dashboard
2. Click on each service (orchestrator, agent-factory, etc.)
3. Go to "Variables" tab
4. Click "Raw Editor"
5. Paste your variables

## 🔗 Step 3: Connect Services (5 minutes)

Railway provides internal networking automatically. Your services can talk to each other using:

- `http://orchestrator.railway.internal:8000`
- `http://agent-factory.railway.internal:8001`
- etc.

No configuration needed! 🎉

## 🌐 Step 4: Access Your Services (2 minutes)

Railway provides public URLs automatically:

- Orchestrator: `https://orchestrator-production.up.railway.app`
- Agent Factory: `https://agent-factory-production.up.railway.app`
- etc.

Find these in your Railway dashboard under each service.

## 🧪 Step 5: Test Your Deployment (5 minutes)

```bash
# Test orchestrator health
curl https://your-orchestrator.up.railway.app/health

# Test code generation
curl -X POST https://your-orchestrator.up.railway.app/execute \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a hello world function",
    "requirements": "Simple Python function",
    "tier_override": "T1",
    "user_id": "test-user",
    "tenant_id": "test"
  }'
```

## 💰 Step 6: Monitor Costs (2 minutes)

Railway shows real-time usage:

1. Go to Railway Dashboard
2. Click "Usage" tab
3. You'll see:
   - Current month costs
   - Per-service breakdown
   - Resource usage graphs

## 🔧 Troubleshooting

### Service Won't Start?
```bash
# Check logs
railway logs --service orchestrator

# Common issues:
# 1. Missing environment variables
# 2. Port conflicts (Railway sets PORT automatically)
# 3. Database connection issues
```

### Can't Connect Services?
```bash
# Services use internal URLs
# ❌ Wrong: http://localhost:8001
# ✅ Right: http://agent-factory.railway.internal:8001
```

### High Costs?
```bash
# Enable sleep mode for dev
# In Railway Dashboard > Service > Settings
# Enable "Sleep when inactive"
```

## 🎯 Next Steps

### 1. **Optimize Costs** (Save 50%)
Move to hybrid deployment:
- Keep APIs on Railway
- Move database to Supabase (free)
- Use Temporal Cloud (free)

### 2. **Add GitHub Auto-Deploy**
- Connect GitHub in Railway dashboard
- Every push = automatic deploy

### 3. **Add Custom Domain**
- Add your domain in service settings
- Railway handles SSL automatically

### 4. **Set Up Monitoring**
```bash
# Railway has built-in monitoring
# For advanced monitoring, add:
railway variables set SENTRY_DSN=your-sentry-dsn
```

## 📊 Expected Costs

### Full Deployment
- All services on Railway: ~$215/month

### Optimized Deployment
- Core services on Railway: ~$100/month
- Database on Supabase: Free (using credits)
- Temporal on Cloud: Free (using credits)

## 🏃‍♂️ Quick Commands

```bash
# View all services
railway status

# View logs
railway logs --service orchestrator

# SSH into service
railway shell --service orchestrator

# Run one-off commands
railway run --service orchestrator npm test

# Restart service
railway restart --service orchestrator

# Open dashboard
railway open
```

## 🚨 Important Notes

1. **Database Migrations**: Run after PostgreSQL is ready
   ```bash
   railway run --service orchestrator npm run migrate
   ```

2. **Temporal Worker**: Needs external Temporal server
   - Either use Temporal Cloud (recommended)
   - Or deploy Temporal separately

3. **Qdrant**: Use Qdrant Cloud free tier
   - Sign up at qdrant.io
   - Get API key and URL

## 🎉 Success Checklist

- [ ] All services show "Active" in dashboard
- [ ] Health checks return 200 OK
- [ ] Can generate code via API
- [ ] Logs show no errors
- [ ] Costs are within budget

## 🆘 Need Help?

1. Railway Discord: https://discord.gg/railway
2. Railway Docs: https://docs.railway.app
3. QLP Issues: Check logs first!

---

**You're now deployed on Railway!** 🚂

Your platform is live and ready to generate code. Total time: ~30 minutes.