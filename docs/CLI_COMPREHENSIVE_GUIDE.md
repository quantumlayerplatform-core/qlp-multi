# QuantumLayer CLI - Comprehensive Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Installation & Setup](#installation--setup)
3. [Core Commands](#core-commands)
4. [Interactive Mode](#interactive-mode)
5. [Advanced Features](#advanced-features)
6. [Configuration](#configuration)
7. [Real-time Features](#real-time-features)
8. [Integration Workflows](#integration-workflows)
9. [Marketing CLI](#marketing-cli)
10. [Tips & Best Practices](#tips--best-practices)
11. [Troubleshooting](#troubleshooting)
12. [Command Reference](#command-reference)

## Introduction

The QuantumLayer CLI (`qlp`) is a powerful command-line interface that brings AI-powered code generation directly to your terminal. It's designed for developers who want to leverage the full capabilities of the Quantum Layer Platform without leaving their development environment.

### Key Features

- **Natural Language Code Generation**: Describe what you want, get production-ready code
- **Interactive Mode**: Build projects through conversation
- **Visual Input**: Generate code from diagrams and mockups
- **Watch Mode**: Auto-complete TODO comments
- **GitHub Integration**: Direct repository creation and pushing
- **Real-time Progress**: Live updates during generation
- **Cost Tracking**: Know costs before and after generation
- **Multi-language Support**: All major programming languages

## Installation & Setup

### Requirements

- Python 3.8+ or Node.js 14+
- Git (for GitHub features)
- Docker (optional, for local deployment)

### Installation Methods

#### Via pip (Python)
```bash
pip install quantumlayer

# Or for development
git clone https://github.com/quantumlayer/qlp-cli
cd qlp-cli
pip install -e .
```

#### Via npm (Node.js)
```bash
npm install -g @quantumlayer/cli

# Or using yarn
yarn global add @quantumlayer/cli
```

#### Via Homebrew (macOS)
```bash
brew tap quantumlayer/tap
brew install qlp
```

### Initial Setup

```bash
# Initialize configuration
qlp config --init

# The CLI will prompt you for:
# - API endpoint (default: https://api.quantumlayer.ai)
# - API key (get from https://quantumlayer.ai/dashboard)
# - Default language preference
# - Default output directory
# - GitHub token (optional)
```

### Configuration File

The CLI creates a configuration file at `~/.qlp/config.json`:

```json
{
  "api": {
    "endpoint": "https://api.quantumlayer.ai",
    "key": "qlp_sk_...",
    "timeout": 300
  },
  "defaults": {
    "language": "auto",
    "output": "./generated",
    "deploy": null
  },
  "github": {
    "token": "ghp_...",
    "default_visibility": "public"
  },
  "ui": {
    "theme": "auto",
    "show_cost": true,
    "show_progress": true,
    "emoji": true
  }
}
```

## Core Commands

### 1. Generate Command

The primary command for code generation.

#### Basic Usage
```bash
qlp generate "create a REST API for task management"
```

#### With Options
```bash
qlp generate "e-commerce platform with microservices" \
  --language python \
  --output ./my-project \
  --deploy aws \
  --github my-ecommerce \
  --show-reasoning
```

#### Available Options

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--language` | `-l` | Programming language | `python`, `javascript`, `go`, `auto` |
| `--output` | `-o` | Output directory | `./backend`, `~/projects/api` |
| `--deploy` | `-d` | Deploy to cloud | `aws`, `azure`, `gcp`, `local` |
| `--github` | `-g` | Push to GitHub | `repo-name` or `owner/repo` |
| `--timeout` | `-t` | Generation timeout (minutes) | `10`, `30` |
| `--dry-run` | | Preview without generating | |
| `--show-reasoning` | `-r` | Display AI reasoning | |
| `--preview` | `-p` | Live code preview | |
| `--live` | `-L` | Show all activity | |
| `--no-tests` | | Skip test generation | |
| `--no-docs` | | Skip documentation | |
| `--framework` | `-f` | Specify framework | `fastapi`, `express`, `django` |

#### Examples

**Simple API**
```bash
qlp generate "REST API for user authentication with JWT"
```

**Complex System**
```bash
qlp generate "microservices architecture for online banking" \
  --language java \
  --deploy kubernetes \
  --github fintech/banking-platform \
  --show-reasoning
```

**With Framework**
```bash
qlp generate "blog platform" \
  --language python \
  --framework django \
  --output ./django-blog
```

### 2. Interactive Mode

Build projects through natural conversation.

```bash
qlp interactive
```

#### Example Session
```
$ qlp interactive

🤖 Welcome to QuantumLayer Interactive Mode!
   I'll help you build your project step by step.

You: I need a real-time chat application
QL: Great! Let me help you build a real-time chat application. 
    What technology stack would you prefer?
    
    1. Node.js + Socket.io (recommended for real-time)
    2. Python + WebSockets
    3. Go + WebSockets
    4. Let me choose based on requirements

You: 1

QL: Excellent choice! Node.js with Socket.io is perfect for real-time chat.
    What features should the chat include?
    
    Common features:
    - User authentication
    - Private messages
    - Group channels
    - File sharing
    - Message history
    - Typing indicators
    - Online status

You: All of them, plus emoji reactions and message editing

QL: Comprehensive feature set! Let me ask a few more questions:

    1. Database preference?
       - PostgreSQL (recommended)
       - MongoDB
       - MySQL
    
You: PostgreSQL

QL: 2. Frontend framework?
       - React (recommended)
       - Vue.js
       - Vanilla JavaScript
       
You: React

QL: 3. Should I include:
       - Docker configuration? (Y/n)
       - CI/CD pipeline? (Y/n)
       - Kubernetes manifests? (Y/n)
       
You: Y, Y, N

QL: Perfect! I have all the information I need. Here's what I'll build:

    📋 Project Summary:
    - Real-time chat application
    - Backend: Node.js + Socket.io + Express
    - Frontend: React + Socket.io-client
    - Database: PostgreSQL
    - Features: Auth, DMs, channels, file sharing, history, 
                typing indicators, online status, emoji reactions,
                message editing
    - Extras: Docker, CI/CD (GitHub Actions)
    
    Type 'generate' to start building, or ask me to modify anything.

You: generate

🚀 Starting generation...
[Progress bar and live updates]
```

#### Interactive Commands

| Command | Description |
|---------|-------------|
| `generate` | Start building with current specifications |
| `modify` | Change previously answered options |
| `reset` | Start over |
| `save` | Save conversation for later |
| `load` | Load saved conversation |
| `help` | Show available commands |

### 3. From Image

Generate code from architecture diagrams or UI mockups.

```bash
qlp from-image diagram.png
```

#### Supported Image Types
- Architecture diagrams
- UI mockups
- Flowcharts
- Entity relationship diagrams
- Wireframes
- Whiteboard sketches

#### Options
```bash
qlp from-image mockup.png \
  --type frontend \
  --framework react \
  --output ./frontend \
  --style tailwind
```

#### Example
```bash
# From architecture diagram
qlp from-image microservices-architecture.png \
  --output ./backend \
  --language go

# From UI mockup
qlp from-image dashboard-mockup.png \
  --type frontend \
  --framework vue \
  --with-backend
```

### 4. Watch Mode

Automatically completes TODO comments in your code.

```bash
qlp watch
```

#### TODO Format
```javascript
// TODO: QL: implement user authentication with JWT and refresh tokens

// TODO: QL: add rate limiting to this endpoint (100 requests per minute)

/* TODO: QL: create a caching layer using Redis with 5 minute TTL */
```

#### Watch Options
```bash
qlp watch \
  --directory ./src \
  --recursive \
  --ignore "node_modules,dist" \
  --file-types "js,ts,py,go"
```

#### Features
- Real-time file monitoring
- Intelligent context awareness
- Preserves code style
- Git-aware (won't modify ignored files)
- Supports all major languages

### 5. Status Command

Check workflow status and progress.

```bash
qlp status workflow-abc-123
```

#### Output Example
```
Workflow: workflow-abc-123
Status: IN_PROGRESS
Started: 2 minutes ago
Progress: 65%

Current Activity: Generating API endpoints
├─ Analysis: ✓ Complete
├─ Design: ✓ Complete
├─ Implementation: ● In progress (65%)
├─ Testing: ○ Pending
└─ Documentation: ○ Pending

Estimated time remaining: 45 seconds
```

#### Options
```bash
# Detailed view
qlp status workflow-abc-123 --detailed

# JSON output
qlp status workflow-abc-123 --json

# Watch mode (auto-refresh)
qlp status workflow-abc-123 --watch
```

## Interactive Mode

### Advanced Interactive Features

#### 1. Context Building
The interactive mode builds rich context:
- Previous answers influence future questions
- Learns your preferences over time
- Suggests based on best practices

#### 2. Modification Flow
```
You: modify
QL: What would you like to change?
    1. Technology stack
    2. Features
    3. Database
    4. Deployment options
    
You: 2
QL: Current features: [lists features]
    Would you like to add or remove features?
```

#### 3. Templates
```
You: use template
QL: Available templates:
    1. SaaS Starter - Multi-tenant SaaS with billing
    2. E-commerce - Full e-commerce platform
    3. API Gateway - Microservices with gateway
    4. Mobile Backend - REST API for mobile apps
    
You: 1
QL: Loading SaaS Starter template...
    Let me customize it for your needs.
```

## Advanced Features

### 1. Cost Tracking

The CLI shows cost estimates before generation:

```bash
$ qlp generate "complex microservices system" --show-cost

💰 Cost Estimate:
   - Token usage: ~25,000 tokens
   - Estimated cost: $0.75 - $1.25
   - Time estimate: 45-60 seconds
   
   Proceed? (Y/n)
```

After generation:
```
✅ Generation Complete!
   - Actual tokens: 23,847
   - Actual cost: $0.89
   - Time taken: 52 seconds
```

### 2. Live Progress

With `--live` flag, see detailed progress:

```bash
$ qlp generate "e-commerce platform" --live

🚀 Starting generation...

[■■■■■□□□□□] 50% - Creating product service
├─ Analysis: ✓ Complete (2.1s)
├─ Design: ✓ Complete (3.5s)
├─ Implementation: ● In progress
│  ├─ Models: ✓ Complete
│  ├─ API endpoints: ● Generating...
│  ├─ Business logic: ○ Pending
│  └─ Database: ○ Pending
├─ Testing: ○ Pending
└─ Documentation: ○ Pending

💭 AI Reasoning: Implementing CQRS pattern for inventory management
                 to handle high read/write loads...
```

### 3. Preview Mode

See code as it's generated with `--preview`:

```bash
$ qlp generate "REST API" --preview

[Preview Window]
┌─ product_service.py ────────────────────────┐
│ from fastapi import FastAPI, HTTPException  │
│ from pydantic import BaseModel              │
│ from typing import List, Optional           │
│                                            │
│ app = FastAPI(title="Product Service")     │
│                                            │
│ class Product(BaseModel):                  │
│     id: str                               │
│     name: str                             │
│     price: float                          │
│     inventory: int                        │
└────────────────────────────────────────────┘
[Generating... 42% complete]
```

### 4. GitHub Integration

Direct GitHub repository creation and pushing:

```bash
# Create new repo and push
qlp generate "task management API" \
  --github my-task-api \
  --private

# Push to existing repo
qlp generate "frontend for API" \
  --github username/existing-repo \
  --branch feature/new-frontend
```

The CLI will:
1. Create repository if it doesn't exist
2. Initialize with README and .gitignore
3. Set up GitHub Actions CI/CD
4. Push all generated code
5. Provide repository URL

### 5. Deployment Integration

Deploy directly after generation:

```bash
# Deploy to AWS
qlp generate "serverless API" \
  --deploy aws \
  --aws-profile production \
  --aws-region us-east-1

# Deploy to Kubernetes
qlp generate "microservices" \
  --deploy kubernetes \
  --k8s-context production \
  --namespace my-app
```

## Configuration

### Environment Variables

```bash
# API Configuration
export QLP_API_URL=https://api.quantumlayer.ai
export QLP_API_KEY=qlp_sk_...

# Defaults
export QLP_DEFAULT_LANGUAGE=python
export QLP_DEFAULT_OUTPUT=./generated
export QLP_DEFAULT_FRAMEWORK=fastapi

# GitHub
export QLP_GITHUB_TOKEN=ghp_...
export QLP_GITHUB_DEFAULT_VISIBILITY=private

# UI Preferences
export QLP_NO_EMOJI=false
export QLP_NO_COLOR=false
export QLP_QUIET=false
```

### Configuration Commands

```bash
# View current config
qlp config list

# Set individual values
qlp config set api.endpoint https://custom.api.endpoint
qlp config set defaults.language go
qlp config set ui.emoji false

# Reset to defaults
qlp config reset

# Edit config file directly
qlp config edit
```

### Profiles

Manage multiple configurations:

```bash
# Create new profile
qlp config profile create work

# Switch profile
qlp config profile use work

# List profiles
qlp config profile list

# Delete profile
qlp config profile delete personal
```

## Real-time Features

### 1. Progress Streaming

```bash
# WebSocket connection for real-time updates
qlp generate "complex system" --stream ws

# Server-sent events
qlp generate "api" --stream sse
```

### 2. Collaborative Mode

```bash
# Start collaborative session
qlp collab start --session my-team-project

# Join session
qlp collab join --session my-team-project --code ABC123

# Share progress with team
qlp generate "api" --collab my-team-project
```

### 3. Live Logs

```bash
# Tail generation logs
qlp logs workflow-abc-123 --follow

# Filter logs
qlp logs workflow-abc-123 --level error --service orchestrator
```

## Integration Workflows

### 1. CI/CD Integration

#### GitHub Actions
```yaml
name: Generate Missing Implementation
on:
  issue_comment:
    types: [created]

jobs:
  generate:
    if: contains(github.event.comment.body, '/qlp generate')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install QLp CLI
        run: npm install -g @quantumlayer/cli
      
      - name: Generate Code
        run: |
          PROMPT="${{ github.event.comment.body }}"
          PROMPT=${PROMPT#"/qlp generate "}
          qlp generate "$PROMPT" --output ./generated
        env:
          QLP_API_KEY: ${{ secrets.QLP_API_KEY }}
      
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v4
        with:
          title: "Generated: ${{ github.event.comment.body }}"
          branch: qlp/generated-${{ github.run_id }}
```

### 2. VS Code Integration

```bash
# Install VS Code extension
code --install-extension quantumlayer.qlp-vscode

# Use from command palette
# Cmd/Ctrl + Shift + P -> "QLp: Generate from selection"
```

### 3. Git Hooks

```bash
# .git/hooks/pre-commit
#!/bin/bash
# Auto-complete TODOs before commit

if git diff --cached --name-only | grep -E '\.(js|ts|py|go)$'; then
  qlp watch --once --staged
fi
```

## Marketing CLI

Separate CLI for marketing automation:

### Installation
```bash
pip install qlp-marketing
# or
npm install -g @quantumlayer/marketing-cli
```

### Basic Commands

```bash
# Create campaign
qlp-marketing create \
  --objective "launch_awareness" \
  --product "My SaaS Product" \
  --audience "developers,startups" \
  --channels "twitter,linkedin,email" \
  --duration 30d

# Generate content
qlp-marketing generate \
  --type "twitter_thread" \
  --topic "10x developer productivity with AI" \
  --tone "educational" \
  --include-media

# Schedule posts
qlp-marketing schedule \
  --campaign campaign-123 \
  --optimize-timing \
  --timezone "America/New_York"

# View analytics
qlp-marketing analytics campaign-123 \
  --metrics "engagement,reach,conversions" \
  --compare-periods \
  --export pdf

# A/B testing
qlp-marketing ab-test \
  --campaign campaign-123 \
  --element "email_subject" \
  --variants 3 \
  --duration 7d
```

### Advanced Marketing Commands

```bash
# Persona-specific content
qlp-marketing generate \
  --persona "enterprise_cto" \
  --pain-points "scalability,security" \
  --format "linkedin_article"

# Competitor analysis
qlp-marketing analyze \
  --competitors "competitor1.com,competitor2.com" \
  --channels "all" \
  --export competitive-analysis.pdf

# ROI tracking
qlp-marketing roi \
  --campaign campaign-123 \
  --include-attribution \
  --time-period 30d
```

## Tips & Best Practices

### 1. Effective Prompts

**Good Prompts:**
- "Create a REST API for task management with user authentication, PostgreSQL database, and real-time updates"
- "Build a microservices architecture for e-commerce with product, order, and payment services"

**Better Prompts:**
- Include specific requirements
- Mention preferred technologies
- Specify constraints
- Include non-functional requirements

### 2. Performance Optimization

```bash
# Use caching for similar requests
qlp generate "api endpoint for users" --cache

# Batch multiple generations
qlp batch generate commands.txt --parallel 4

# Use lighter models for simple tasks
qlp generate "utility function" --model fast
```

### 3. Project Organization

```bash
# Generate into organized structure
qlp generate "microservice" \
  --output ./services/user-service \
  --maintain-structure

# Use workspaces
qlp workspace create my-project
qlp workspace use my-project
qlp generate "api" # Automatically uses workspace settings
```

### 4. Debugging

```bash
# Verbose output
qlp generate "api" -vvv

# Debug mode
qlp generate "api" --debug

# Dry run to see what would be generated
qlp generate "api" --dry-run
```

## Troubleshooting

### Common Issues

#### 1. Authentication Errors
```bash
Error: Invalid API key

Solution:
qlp config set api.key YOUR_NEW_KEY
```

#### 2. Timeout Issues
```bash
Error: Generation timed out

Solution:
qlp generate "complex system" --timeout 30
```

#### 3. Network Issues
```bash
Error: Cannot connect to API

Solution:
# Check API status
qlp status --check-api

# Use alternative endpoint
qlp config set api.endpoint https://backup.api.endpoint
```

#### 4. GitHub Issues
```bash
Error: GitHub push failed

Solution:
# Re-authenticate
qlp auth github

# Check token permissions
qlp debug github-permissions
```

### Debug Commands

```bash
# Check CLI version
qlp --version

# Run diagnostics
qlp doctor

# View debug logs
qlp debug logs

# Test API connection
qlp debug test-connection

# Clear cache
qlp cache clear
```

## Command Reference

### Global Options

| Option | Description |
|--------|-------------|
| `--help`, `-h` | Show help |
| `--version`, `-v` | Show version |
| `--config`, `-c` | Config file path |
| `--profile`, `-p` | Use specific profile |
| `--quiet`, `-q` | Suppress output |
| `--verbose`, `-vvv` | Verbose output |
| `--no-color` | Disable colors |
| `--json` | JSON output |

### All Commands

| Command | Description |
|---------|-------------|
| `generate` | Generate code from description |
| `interactive` | Interactive project builder |
| `from-image` | Generate from image |
| `watch` | Watch for TODO comments |
| `status` | Check workflow status |
| `config` | Manage configuration |
| `auth` | Manage authentication |
| `workspace` | Manage workspaces |
| `batch` | Batch operations |
| `export` | Export projects |
| `validate` | Validate generated code |
| `test` | Run tests on generated code |
| `deploy` | Deploy generated code |
| `rollback` | Rollback deployment |
| `logs` | View generation logs |
| `stats` | View usage statistics |
| `upgrade` | Upgrade CLI |
| `doctor` | Run diagnostics |
| `help` | Show help |

## Conclusion

The QuantumLayer CLI transforms how developers interact with AI-powered code generation. With its intuitive commands, rich features, and seamless integrations, it brings the power of the Quantum Layer Platform directly to your terminal.

Whether you're building a simple API or a complex microservices architecture, the CLI provides the tools and flexibility to generate production-ready code with just a few commands.