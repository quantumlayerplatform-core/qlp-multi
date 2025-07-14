# AWS Bedrock Setup Guide for QuantumLayer Platform

## Prerequisites

Before setting up AWS Bedrock, ensure you have:

1. **AWS Account** with billing enabled
2. **IAM User** with appropriate permissions
3. **AWS CLI** installed (optional but recommended)

## Step 1: Enable AWS Bedrock Models

### 1.1 Access AWS Console

1. Log in to [AWS Console](https://console.aws.amazon.com)
2. Navigate to **Amazon Bedrock** service
3. Select your preferred region (us-east-1 recommended)

### 1.2 Request Model Access

In the Bedrock console:

1. Click **Model access** in the left sidebar
2. Click **Manage model access**
3. Select the following Anthropic models:
   - ✅ Claude 3 Haiku
   - ✅ Claude 3 Sonnet
   - ✅ Claude 3.5 Sonnet
   - ✅ Claude 3 Opus

4. Click **Request model access**
5. Wait for approval (usually instant for Claude models)

## Step 2: Create IAM User for Bedrock

### 2.1 Create IAM Policy

Create a custom IAM policy with the following JSON:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockInvokeModel",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-*",
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-*",
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-*",
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-opus-*"
            ]
        },
        {
            "Sid": "BedrockListAndDescribe",
            "Effect": "Allow",
            "Action": [
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel"
            ],
            "Resource": "*"
        }
    ]
}
```

### 2.2 Create IAM User

1. Go to **IAM** → **Users** → **Create user**
2. Username: `qlp-bedrock-user`
3. Select **Programmatic access**
4. Attach the policy created above
5. Create user and save credentials

## Step 3: Configure QuantumLayer Platform

### 3.1 Add AWS Credentials to .env

Add the following to your `.env` file:

```env
# AWS Bedrock Configuration
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_HERE
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY_HERE
AWS_REGION=us-east-1

# AWS Bedrock Model Configuration
AWS_T0_MODEL=anthropic.claude-3-haiku-20240307-v1:0
AWS_T1_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
AWS_T2_MODEL=anthropic.claude-3-5-sonnet-20240620-v1:0
AWS_T3_MODEL=anthropic.claude-3-opus-20240229-v1:0

# Provider Preferences (use AWS Bedrock)
LLM_T0_PROVIDER=aws_bedrock
LLM_T1_PROVIDER=aws_bedrock
LLM_T2_PROVIDER=aws_bedrock
LLM_T3_PROVIDER=aws_bedrock

# Advanced Settings
AWS_BEDROCK_RETRY_ATTEMPTS=3
AWS_BEDROCK_TIMEOUT=60
AWS_BEDROCK_MAX_CONCURRENT=10
AWS_BEDROCK_ENABLE_LOGGING=true

# Health Monitoring
PROVIDER_HEALTH_CHECK_INTERVAL=60
PROVIDER_CIRCUIT_BREAKER_THRESHOLD=5
PROVIDER_CIRCUIT_BREAKER_TIMEOUT=300

# Multi-Provider Configuration
ENSEMBLE_ENABLED=false
REGIONAL_OPTIMIZATION_ENABLED=true
PREFERRED_REGIONS=["us-east-1", "us-west-2"]
```

### 3.2 Install Dependencies

```bash
source .venv/bin/activate
pip install boto3 botocore
```

### 3.3 Test Configuration

Run the test script:

```bash
python test_aws_bedrock_integration.py
```

## Step 4: Verify Model Access

### 4.1 Check Model Availability

Use AWS CLI to verify model access:

```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query "modelSummaries[?contains(modelId, 'claude')].[modelId, modelName]" \
  --output table
```

### 4.2 Test Model Invocation

```bash
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-3-haiku-20240307-v1:0 \
  --body '{"messages":[{"role":"user","content":"Hello"}],"anthropic_version":"bedrock-2023-05-31","max_tokens":50}' \
  --region us-east-1 \
  output.json
```

## Step 5: Cost Management

### 5.1 Set Up Budget Alerts

1. Go to **AWS Budgets**
2. Create a new budget for Bedrock
3. Set monthly limit (e.g., $100)
4. Configure email alerts at 80% and 100%

### 5.2 Monitor Usage

- Check **AWS Cost Explorer** → Filter by Bedrock
- Review model-specific costs
- Monitor token usage patterns

### 5.3 Cost Optimization Tips

1. **Use appropriate tiers**:
   - T0 (Haiku): $0.25/$1.25 per 1M tokens
   - T1/T2 (Sonnet): $3/$15 per 1M tokens
   - T3 (Opus): $15/$75 per 1M tokens

2. **Enable caching** in Vector Memory
3. **Batch similar requests**
4. **Set max_tokens appropriately**

## Troubleshooting

### Common Issues

1. **"AccessDeniedException"**
   - Check IAM permissions
   - Verify model access is granted
   - Ensure correct region

2. **"ModelNotFound"**
   - Verify model ID is correct
   - Check region availability
   - Ensure model access is approved

3. **"ThrottlingException"**
   - Implement exponential backoff
   - Check rate limits for your account
   - Consider requesting limit increase

### Debug Commands

```bash
# Test AWS credentials
aws sts get-caller-identity

# List available models
aws bedrock list-foundation-models --region us-east-1

# Check IAM permissions
aws iam get-user
aws iam list-attached-user-policies --user-name qlp-bedrock-user

# Test Bedrock access
python test_bedrock_simple.py
```

## Security Best Practices

1. **Use IAM roles in production** instead of access keys
2. **Enable MFA** for AWS account
3. **Rotate credentials** every 90 days
4. **Use AWS Secrets Manager** for production
5. **Enable CloudTrail** for audit logging
6. **Configure VPC endpoints** for private access

## Next Steps

1. ✅ Enable models in AWS Console
2. ✅ Create IAM user with permissions
3. ✅ Configure .env file
4. ✅ Test integration
5. 🔄 Monitor costs and usage
6. 🔄 Optimize for production

## Support Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Anthropic on Bedrock](https://docs.anthropic.com/claude/docs/claude-on-amazon-bedrock)
- [AWS Pricing Calculator](https://calculator.aws/#/addService/Bedrock)
- [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)