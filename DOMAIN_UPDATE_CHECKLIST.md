# Domain Update Checklist - quantumlayerplatform.com

## ✅ Completed
- [x] Updated all code references (21 files)
- [x] Updated environment variables in .env
- [x] Restarted orchestrator service
- [x] Created backup in `domain_update_backup_20250720_102604/`

## 📋 External Services to Update

### 1. DNS Configuration
Configure DNS records for the new domain:
```
A Records:
- api.quantumlayerplatform.com → Your server IP
- staging-api.quantumlayerplatform.com → Staging server IP
- app.quantumlayerplatform.com → Frontend server IP
- dashboard.quantumlayerplatform.com → Dashboard server IP
- docs.quantumlayerplatform.com → Documentation server IP
- status.quantumlayerplatform.com → Status page server IP

CNAME Records (if using CDN):
- www.quantumlayerplatform.com → quantumlayerplatform.com
```

### 2. SSL Certificates
Obtain SSL certificates for:
- quantumlayerplatform.com
- *.quantumlayerplatform.com (wildcard)

Or individual certificates for each subdomain.

### 3. OAuth Applications
Update redirect URLs in:

#### GitHub OAuth App
- Authorization callback URL: `https://api.quantumlayerplatform.com/auth/github/callback`
- Homepage URL: `https://quantumlayerplatform.com`

#### Google OAuth
- Authorized redirect URIs: 
  - `https://api.quantumlayerplatform.com/auth/google/callback`
  - `https://app.quantumlayerplatform.com/auth/google/callback`

#### Other OAuth Providers
Update similar callback URLs for any other OAuth providers you use.

### 4. Email Service (SendGrid/AWS SES)
- Add domain: quantumlayerplatform.com
- Verify domain ownership
- Update sender addresses:
  - noreply@quantumlayerplatform.com
  - support@quantumlayerplatform.com
  - alerts@quantumlayerplatform.com

### 5. Third-Party Services
Update webhook URLs and domain references in:
- Stripe webhook endpoints
- Slack webhook URLs
- GitHub webhooks
- Monitoring services (DataDog, New Relic, etc.)
- Error tracking (Sentry)
- Analytics (Google Analytics, Mixpanel)
- CDN configuration (CloudFlare, Fastly)

### 6. Marketing & SEO
- Update Google Search Console
- Update sitemap.xml references
- Update social media profiles
- Update email signatures
- Update marketing materials

### 7. Documentation & Support
- Update API documentation
- Update support documentation
- Update status page
- Update help center articles

## 🔧 Testing Checklist

### Local Testing (with /etc/hosts)
Add to `/etc/hosts`:
```
127.0.0.1 api.quantumlayerplatform.com
127.0.0.1 app.quantumlayerplatform.com
```

Then test:
```bash
# API Health
curl http://api.quantumlayerplatform.com:8000/health

# API Documentation
open http://api.quantumlayerplatform.com:8000/api/v2/docs
```

### Production Testing (after DNS propagation)
```bash
# Test API endpoints
curl https://api.quantumlayerplatform.com/health
curl https://staging-api.quantumlayerplatform.com/health

# Test SSL
openssl s_client -connect api.quantumlayerplatform.com:443 -servername api.quantumlayerplatform.com

# Test OAuth flows
# Manually test login flows with each provider
```

## 🔄 Rollback Plan

If issues arise, restore from backup:
```bash
# Restore all files from backup
cp -r domain_update_backup_20250720_102604/* .

# Or use git
git checkout -- .

# Update .env back to old domain
# Restart services
docker-compose -f docker-compose.platform.yml restart
```

## 📝 Notes

- DNS propagation can take up to 48 hours
- Keep old domain active during transition
- Consider setting up redirects from old to new domain
- Monitor error logs during transition
- Update any hardcoded references in:
  - Mobile apps
  - Desktop applications
  - Browser extensions
  - API clients

## Status

Current domain configuration in code: **quantumlayerplatform.com** ✅