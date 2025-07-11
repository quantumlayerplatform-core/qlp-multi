# GitHub Integration Guide

This guide explains how to push QLCapsules directly to GitHub repositories.

## Overview

The GitHub integration allows you to:
- Push generated capsules to new GitHub repositories
- Auto-create repository with proper structure
- Include CI/CD workflows (GitHub Actions)
- Set up deployment configurations
- Create private or public repositories

## Prerequisites

### 1. GitHub Personal Access Token

You need a GitHub Personal Access Token with `repo` scope:

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a name (e.g., "QLP Integration")
4. Select the `repo` scope (Full control of private repositories)
5. Click "Generate token"
6. Copy the token immediately (you won't see it again!)

### 2. Set Token as Environment Variable

```bash
export GITHUB_TOKEN=ghp_your_token_here
```

Or add to your `.env` file:
```
GITHUB_TOKEN=ghp_your_token_here
```

## Usage Methods

### Method 1: Command Line Tool

```bash
# List available capsules
python download_capsule_docker.py list

# Push a capsule to GitHub
python push_to_github.py <capsule-id>

# Push with custom options
python push_to_github.py <capsule-id> --name my-custom-repo --private
```

### Method 2: REST API

```bash
# Check if token is valid
curl http://localhost:8000/api/github/check-token?token=$GITHUB_TOKEN

# Push capsule to GitHub
curl -X POST http://localhost:8000/api/github/push \
  -H "Content-Type: application/json" \
  -d '{
    "capsule_id": "6b86c9c4-95da-48fc-9c86-ac57f51aa0c6",
    "github_token": "'$GITHUB_TOKEN'",
    "repo_name": "my-awesome-api",
    "private": false
  }'
```

### Method 3: Python Script

```python
import asyncio
from src.orchestrator.github_integration import GitHubIntegration
from src.common.models import QLCapsule

async def push_my_capsule():
    github = GitHubIntegration(token="your-token")
    
    # Get capsule from database
    capsule = await get_capsule("capsule-id")
    
    # Push to GitHub
    result = await github.push_capsule(
        capsule,
        repo_name="my-project",
        private=False
    )
    
    print(f"Repository created: {result['repository_url']}")

asyncio.run(push_my_capsule())
```

## What Gets Pushed

When you push a capsule to GitHub, the following files are created:

### 1. **Source Code**
All files from `capsule.source_code` are created in their original structure:
```
src/main.py
src/models.py
src/utils.py
```

### 2. **Tests**
All test files from `capsule.tests`:
```
tests/test_main.py
tests/test_models.py
tests/conftest.py
```

### 3. **Documentation**
- `README.md` - From capsule documentation
- `qlp-manifest.json` - Capsule manifest
- `qlp-metadata.json` - Generation metadata
- `qlp-validation.json` - Validation report
- `qlp-deployment.json` - Deployment configuration

### 4. **Configuration Files**
- `.gitignore` - Language-specific ignores
- `.github/workflows/ci.yml` - GitHub Actions workflow

### 5. **GitHub Actions Workflow**

For Python projects:
```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    - name: Run tests
      run: pytest tests/ -v --cov=src
```

## Advanced Features

### Push and Deploy

Push to GitHub and set up automatic deployment:

```bash
curl -X POST http://localhost:8000/api/github/push-and-deploy \
  -H "Content-Type: application/json" \
  -d '{
    "capsule_id": "capsule-id",
    "github_token": "'$GITHUB_TOKEN'",
    "private": false
  }' \
  -G --data-urlencode "deploy_to=github-pages"
```

Deployment options:
- `github-pages` - Static site hosting
- `vercel` - Vercel deployment
- `netlify` - Netlify deployment

### Custom Repository Names

By default, repository names are generated from the capsule manifest. You can override:

```python
result = await github.push_capsule(
    capsule,
    repo_name="my-custom-name",  # Will create: github.com/username/my-custom-name
    private=True
)
```

## Example Workflow

1. **Generate a capsule:**
```bash
curl -X POST http://localhost:8000/generate/capsule \
  -H "Content-Type: application/json" \
  -d '{
    "description": "REST API for blog management with authentication",
    "requirements": "Use FastAPI, PostgreSQL, JWT auth, include tests"
  }'
```

2. **Get the capsule ID from response**

3. **Push to GitHub:**
```bash
python push_to_github.py <capsule-id>
```

4. **Clone and run:**
```bash
git clone https://github.com/yourusername/blog-management-api
cd blog-management-api
pip install -r requirements.txt
pytest
python main.py
```

## Error Handling

### Common Errors

1. **"Repository already exists"**
   - The tool will automatically use the existing repository
   - Or specify a different name with `--name`

2. **"Bad credentials"**
   - Your token is invalid or expired
   - Generate a new token

3. **"Resource not accessible by integration"**
   - Token doesn't have required permissions
   - Make sure `repo` scope is selected

### Rate Limits

GitHub API has rate limits:
- Authenticated: 5,000 requests/hour
- The integration uses ~10-20 requests per push

## Best Practices

1. **Use Private Repos for Sensitive Code**
   ```bash
   python push_to_github.py <capsule-id> --private
   ```

2. **Review Before Pushing**
   ```bash
   # First download and review
   python download_capsule_docker.py download <capsule-id> --directory
   
   # Then push if satisfied
   python push_to_github.py <capsule-id>
   ```

3. **Add Secrets After Push**
   - Don't include API keys in capsules
   - Add them as GitHub Secrets after repository creation

4. **Enable Branch Protection**
   - After push, enable branch protection rules
   - Require PR reviews for main branch

## Integration with CI/CD

The pushed repositories are ready for:

1. **GitHub Actions** - Workflow included
2. **Vercel** - Add vercel.json for instant deployment
3. **Netlify** - Connect via Netlify dashboard
4. **Heroku** - Add Procfile and deploy
5. **AWS/Azure** - Use respective CI/CD tools

## Roadmap

Future enhancements planned:
- [ ] Create PRs instead of direct push
- [ ] Support for existing repositories
- [ ] Automatic dependency updates
- [ ] Security scanning integration
- [ ] License selection
- [ ] Team collaboration features

## Troubleshooting

### Check Token Validity
```bash
python test_github_push.py
```

### View API Logs
```bash
docker logs qlp-orchestrator -f
```

### Test Connectivity
```bash
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

---

Now your QLP-generated code can go from idea to GitHub repository in seconds! 🚀