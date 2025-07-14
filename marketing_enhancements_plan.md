# Marketing System Enhancement Plan

## 1. LinkedIn Thread Generation - Test Multi-Channel Capability

### Current State
- ✅ System generates Twitter threads
- ✅ LinkedIn publisher exists but only handles single posts
- ❌ No LinkedIn thread/article support

### Implementation Plan

#### Phase 1: Enhance Content Models (30 min)
```python
# Add to src/agents/marketing/models.py
class ContentType(str, Enum):
    TWEET = "tweet"
    TWEET_THREAD = "tweet_thread"
    LINKEDIN_POST = "linkedin_post"
    LINKEDIN_ARTICLE = "linkedin_article"  # NEW
    LINKEDIN_THREAD = "linkedin_thread"    # NEW
```

#### Phase 2: Update Content Generator (1 hour)
```python
# In src/agents/marketing/content_generator.py
async def generate_linkedin_content(request):
    if request.content_type == "linkedin_article":
        # Generate long-form article (1500-3000 words)
        # Include sections, formatting, images placeholders
    elif request.content_type == "linkedin_thread":
        # Generate multi-part LinkedIn posts
        # Each part 1300 chars max
        # Connected narrative across posts
```

#### Phase 3: Enhance Publisher (45 min)
```python
# In src/agents/marketing/social_publisher.py
class LinkedInPublisher:
    async def publish_thread(self, posts: List[str]):
        # Post initial content
        # Add comments as thread continuation
        # Link posts together
```

#### Phase 4: Test Multi-Channel Campaign (15 min)
```bash
# Test request with both Twitter and LinkedIn
{
    "channels": ["twitter", "linkedin"],
    "content_mix": {
        "twitter": ["tweet_thread"],
        "linkedin": ["linkedin_article", "linkedin_thread"]
    }
}
```

---

## 2. Credential Config Scaffolding - Streamline API Setup

### Current State
- ❌ Manual .env editing required
- ❌ No validation of credentials
- ❌ No guided setup

### Implementation Plan

#### Phase 1: Create Setup Script (45 min)
```python
# scripts/setup_social_credentials.py
class SocialMediaSetup:
    def __init__(self):
        self.env_file = Path(".env")
        self.credentials = {}
    
    def interactive_setup(self):
        print("🚀 Social Media API Setup Wizard")
        self.setup_twitter()
        self.setup_linkedin()
        self.validate_all()
        self.write_env()
    
    def setup_twitter(self):
        print("\n📱 Twitter/X Setup")
        print("1. Go to https://developer.twitter.com")
        print("2. Create a new app")
        print("3. Generate all tokens\n")
        
        self.credentials['TWITTER_API_KEY'] = input("API Key: ")
        self.credentials['TWITTER_API_SECRET'] = getpass("API Secret: ")
        # ... etc
```

#### Phase 2: Add Credential Validation (30 min)
```python
# src/common/credential_validator.py
class CredentialValidator:
    async def validate_twitter(self, creds):
        try:
            client = tweepy.Client(**creds)
            user = client.get_me()
            return True, f"✅ Connected as @{user.data.username}"
        except Exception as e:
            return False, f"❌ Twitter auth failed: {e}"
    
    async def validate_linkedin(self, creds):
        # Similar validation
```

#### Phase 3: Create Health Check Endpoint (30 min)
```python
# Add to src/orchestrator/main.py
@app.get("/api/v2/marketing/health/social-media")
async def check_social_media_health():
    return {
        "twitter": {
            "configured": bool(settings.TWITTER_API_KEY),
            "validated": await validate_twitter_creds(),
            "rate_limit": await get_twitter_limits()
        },
        "linkedin": {
            "configured": bool(settings.LINKEDIN_EMAIL),
            "validated": await validate_linkedin_creds()
        }
    }
```

#### Phase 4: Setup Documentation (15 min)
```markdown
# docs/SOCIAL_MEDIA_SETUP.md
## Quick Start
```bash
python scripts/setup_social_credentials.py
```

## Manual Setup
### Twitter
1. Visit https://developer.twitter.com/en/portal/dashboard
2. Create project → Create app
3. Keys and tokens → Generate all
4. Add to .env

### LinkedIn
1. For testing: Use email/password
2. For production: https://www.linkedin.com/developers/
```

---

## 3. Scheduler Template - Enable Recurring Campaigns

### Current State
- ✅ One-time campaign generation
- ✅ Scheduled publisher exists but not integrated
- ❌ No recurring campaign support

### Implementation Plan

#### Phase 1: Create Campaign Templates (1 hour)
```python
# src/orchestrator/campaign_templates.py
class CampaignTemplate:
    def __init__(self):
        self.name: str
        self.schedule: CronSchedule
        self.base_config: Dict
        self.variable_config: Dict  # Changes each run
    
TEMPLATES = {
    "weekly_product_update": {
        "schedule": "0 10 * * MON",  # Every Monday 10am
        "base_config": {
            "objective": "product_update",
            "channels": ["twitter", "linkedin"],
            "tone_preferences": ["informative", "engaging"]
        },
        "variable_config": {
            "product_features": "{{fetch_latest_features}}",
            "metrics": "{{fetch_weekly_metrics}}"
        }
    },
    
    "daily_tech_tips": {
        "schedule": "0 14 * * *",  # Daily at 2pm
        "base_config": {
            "objective": "thought_leadership",
            "channels": ["twitter"],
            "content_type": "tweet",
            "tone_preferences": ["educational", "concise"]
        }
    }
}
```

#### Phase 2: Implement Scheduler Service (1.5 hours)
```python
# src/orchestrator/campaign_scheduler.py
class CampaignScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.temporal_client = get_temporal_client()
    
    async def schedule_campaign(self, template_name: str, config: Dict):
        template = TEMPLATES[template_name]
        
        # Create cron job
        self.scheduler.add_job(
            func=self.execute_campaign,
            trigger=CronTrigger.from_crontab(template["schedule"]),
            args=[template, config],
            id=f"campaign_{template_name}"
        )
    
    async def execute_campaign(self, template, custom_config):
        # Merge configs
        config = {**template["base_config"], **custom_config}
        
        # Process variable config
        config = await self.process_variables(config)
        
        # Start workflow
        await self.temporal_client.start_workflow(
            MarketingWorkflow.run,
            MarketingWorkflowRequest(**config)
        )
```

#### Phase 3: Add Management Endpoints (45 min)
```python
# Add to src/orchestrator/main.py
@app.post("/api/v2/marketing/campaigns/schedule")
async def schedule_recurring_campaign(
    template_name: str,
    custom_config: Dict = {},
    start_date: Optional[datetime] = None
):
    campaign_id = await scheduler.schedule_campaign(
        template_name, 
        custom_config,
        start_date
    )
    return {"campaign_id": campaign_id, "status": "scheduled"}

@app.get("/api/v2/marketing/campaigns/scheduled")
async def list_scheduled_campaigns():
    return scheduler.list_active_campaigns()

@app.delete("/api/v2/marketing/campaigns/scheduled/{campaign_id}")
async def cancel_scheduled_campaign(campaign_id: str):
    scheduler.remove_job(campaign_id)
```

#### Phase 4: Create UI/CLI for Management (30 min)
```python
# scripts/manage_campaigns.py
def main():
    print("📅 Campaign Scheduler")
    print("1. Schedule new campaign")
    print("2. View scheduled campaigns")
    print("3. Cancel campaign")
    
    # Interactive menu
    # List available templates
    # Configure and schedule
```

---

## Implementation Priority & Timeline

### Quick Wins (Do First) - 2 hours
1. **Credential Scaffolding** - Most immediate value
   - Setup script: 45 min
   - Validation: 30 min
   - Health endpoint: 30 min
   - Documentation: 15 min

### Medium Effort (Do Second) - 2.5 hours
2. **LinkedIn Enhancement** - Expands capability
   - Update models: 30 min
   - Content generator: 1 hour
   - Publisher updates: 45 min
   - Testing: 15 min

### Larger Effort (Do Third) - 4 hours
3. **Scheduler Template** - Long-term value
   - Templates: 1 hour
   - Scheduler service: 1.5 hours
   - Endpoints: 45 min
   - Management UI: 30 min
   - Testing: 15 min

---

## Testing Strategy

### Unit Tests
```python
# tests/test_social_publisher.py
async def test_linkedin_thread_publishing()
async def test_credential_validation()
async def test_campaign_scheduling()
```

### Integration Tests
```python
# tests/test_multi_channel.py
async def test_twitter_linkedin_campaign()
async def test_scheduled_campaign_execution()
```

### E2E Test Script
```bash
# test_enhanced_marketing.sh
#!/bin/bash

# 1. Setup credentials
python scripts/setup_social_credentials.py --test-mode

# 2. Test multi-channel
curl -X POST http://localhost:8000/test-marketing-no-auth \
  -d '{"channels": ["twitter", "linkedin"], ...}'

# 3. Schedule recurring campaign
curl -X POST http://localhost:8000/api/v2/marketing/campaigns/schedule \
  -d '{"template_name": "weekly_product_update"}'
```

---

## Success Metrics

1. **Credential Setup**
   - Time to configure: < 5 minutes
   - Validation success rate: 100%
   - Clear error messages

2. **Multi-Channel**
   - LinkedIn article generation: < 30s
   - Thread publishing success: > 95%
   - Content quality consistency

3. **Scheduler**
   - Campaign execution accuracy: 100%
   - Schedule management ease
   - Template flexibility

---

## Risk Mitigation

1. **API Rate Limits**
   - Implement backoff strategies
   - Queue management
   - Rate limit monitoring

2. **Credential Security**
   - Encrypted storage option
   - Rotate token reminders
   - Audit logging

3. **Content Quality**
   - Preview before publish
   - A/B testing capability
   - Performance tracking