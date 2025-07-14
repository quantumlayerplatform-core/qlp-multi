# Enable AWS Bedrock Models - Quick Guide

## ⚡ Quick Steps to Enable Claude Models

You have AWS credentials configured, but need to enable model access in the AWS Console.

### 1. Open AWS Bedrock Console

Go to: https://us-west-2.console.aws.amazon.com/bedrock/home?region=us-west-2#/modelaccess

(This link opens Bedrock Model Access in us-west-2 region)

### 2. Request Model Access

Click **"Manage model access"** and enable these models:

#### Latest Available Models (from your account):
- ✅ **Claude 3.5 Haiku** - `anthropic.claude-3-5-haiku-20241022-v1:0` (NEW - Fast & Cheap)
- ✅ **Claude 3.5 Sonnet** - `anthropic.claude-3-5-sonnet-20241022-v2:0` (Latest version)
- ✅ **Claude 3.7 Sonnet** - `anthropic.claude-3-7-sonnet-20250219-v1:0` (NEWEST!)
- ✅ **Claude Opus 4** - `anthropic.claude-opus-4-20250514-v1:0` (Most powerful)
- ✅ **Claude Sonnet 4** - `anthropic.claude-sonnet-4-20250514-v1:0` (Balanced)

#### Current Config Models (also enable these):
- ✅ Claude 3 Haiku - `anthropic.claude-3-haiku-20240307-v1:0`
- ✅ Claude 3 Sonnet - `anthropic.claude-3-sonnet-20240229-v1:0`
- ✅ Claude 3.5 Sonnet - `anthropic.claude-3-5-sonnet-20240620-v1:0`
- ✅ Claude 3 Opus - `anthropic.claude-3-opus-20240229-v1:0`

### 3. Submit Request

1. Check the boxes for all Claude models
2. Click **"Request model access"**
3. Fill out the use case form (if required)
4. Submit the request

### 4. Wait for Approval

- Most Claude models are **instantly approved**
- You'll see "Access granted" status immediately
- Some models may require manual review (rare)

### 5. Verify Access

Once approved, run:

```bash
aws bedrock list-foundation-models --region us-west-2 --query "modelSummaries[?modelArn!=null].[modelId, modelArn]" --output table | grep claude
```

## 🚀 Quick Test After Enabling

```bash
# Test with the simple script
python test_bedrock_simple.py

# Or full integration test
python test_aws_bedrock_integration.py
```

## 💡 Pro Tip: Use Latest Models

Once enabled, update your `.env` to use the latest models for better performance:

```env
# Latest and Greatest Models
AWS_T0_MODEL=anthropic.claude-3-5-haiku-20241022-v1:0  # NEW: Faster than old Haiku!
AWS_T1_MODEL=anthropic.claude-3-7-sonnet-20250219-v1:0  # NEWEST: Claude 3.7!
AWS_T2_MODEL=anthropic.claude-sonnet-4-20250514-v1:0    # Claude 4 Sonnet!
AWS_T3_MODEL=anthropic.claude-opus-4-20250514-v1:0      # Claude 4 Opus!
```

## 📊 New Model Pricing (Approximate)

- **Claude 3.5 Haiku**: $0.25/$1.25 per 1M tokens (cheapest)
- **Claude 3.7 Sonnet**: $3/$15 per 1M tokens
- **Claude 4 Sonnet**: $3/$15 per 1M tokens
- **Claude 4 Opus**: $15/$75 per 1M tokens (most capable)

## Need Help?

If models don't appear or access is denied:
1. Check you're in the right region (us-west-2)
2. Ensure your AWS account has billing enabled
3. Try a different region if needed
4. Contact AWS Support if issues persist