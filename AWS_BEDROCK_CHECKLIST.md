# AWS Bedrock Setup Checklist

## Pre-Setup Requirements

- [ ] AWS Account with billing enabled
- [ ] Credit card on file (Bedrock requires payment method)
- [ ] Admin access to AWS Console

## Step 1: Enable Bedrock Models (AWS Console)

1. [ ] Log in to [AWS Console](https://console.aws.amazon.com)
2. [ ] Navigate to **Amazon Bedrock**
3. [ ] Select region: **US East (N. Virginia)** us-east-1
4. [ ] Click **Model access** → **Manage model access**
5. [ ] Request access to:
   - [ ] Claude 3 Haiku
   - [ ] Claude 3 Sonnet  
   - [ ] Claude 3.5 Sonnet
   - [ ] Claude 3 Opus
6. [ ] Wait for approval (usually instant)
7. [ ] Verify all models show "Access granted"

## Step 2: Create IAM User

1. [ ] Go to **IAM** → **Users** → **Create user**
2. [ ] Username: `qlp-bedrock-user`
3. [ ] Select **Programmatic access**
4. [ ] Create custom policy with Bedrock permissions
5. [ ] Attach policy to user
6. [ ] Download credentials CSV

## Step 3: Configure QuantumLayer

1. [ ] Run configuration wizard:
   ```bash
   source .venv/bin/activate
   python configure_aws_bedrock.py
   ```

2. [ ] Enter AWS credentials when prompted
3. [ ] Select your preferred region
4. [ ] Wait for configuration to complete

## Step 4: Verify Setup

1. [ ] Run integration test:
   ```bash
   python test_aws_bedrock_integration.py
   ```

2. [ ] Check for green checkmarks:
   - [ ] Configuration valid
   - [ ] Bedrock available
   - [ ] Models accessible
   - [ ] Test completions working

## Step 5: Cost Management

1. [ ] Set up AWS Budget alert ($100/month recommended)
2. [ ] Enable Cost Explorer for Bedrock
3. [ ] Review pricing:
   - Haiku: $0.25/$1.25 per 1M tokens
   - Sonnet: $3/$15 per 1M tokens  
   - Opus: $15/$75 per 1M tokens

## Step 6: Start Using

1. [ ] Restart platform:
   ```bash
   ./stop_all.sh
   ./start_all.sh
   ```

2. [ ] Test with CLI:
   ```bash
   qlp generate "create a fibonacci function in python"
   ```

3. [ ] Monitor logs for AWS Bedrock usage:
   ```bash
   docker logs qlp-agent-factory -f | grep -i bedrock
   ```

## Troubleshooting

If you encounter issues:

1. [ ] Check AWS credentials are correct
2. [ ] Verify model access is granted in console
3. [ ] Ensure IAM user has correct permissions
4. [ ] Check AWS service status
5. [ ] Review logs: `tail -f logs/agent_factory.log`

## Success Indicators

✅ "AWS Bedrock client initialized" in logs
✅ Models show as available in test
✅ Test completions return responses
✅ Cost tracking shows Bedrock usage

## Need Help?

- Review: `docs/AWS_BEDROCK_SETUP_GUIDE.md`
- Check test results: `bedrock_test_results.json`
- AWS Support: https://console.aws.amazon.com/support/