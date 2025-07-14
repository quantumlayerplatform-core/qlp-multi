# AWS Bedrock Integration Guide

## Overview

The QuantumLayer Platform now includes production-grade AWS Bedrock integration, providing access to Claude models through AWS infrastructure. This integration offers enterprise-level reliability, regional optimization, and seamless failover capabilities.

## Key Features

### 🚀 Production-Grade Implementation
- **Enterprise Reliability**: Circuit breakers, health monitoring, and adaptive retry logic
- **Cost Tracking**: Real-time cost monitoring and optimization
- **Regional Failover**: Automatic region switching for optimal performance
- **Comprehensive Metrics**: Detailed performance and usage analytics

### 🤖 Model Support
- **Claude 3 Haiku** (T0): Fast & cost-effective for simple tasks
- **Claude 3 Sonnet** (T1): Balanced performance for medium complexity
- **Claude 3.5 Sonnet** (T2): Best for code generation and complex tasks
- **Claude 3 Opus** (T3): Most capable for complex reasoning

### 🔄 Multi-Provider Architecture
- Seamless failover between AWS Bedrock, Azure OpenAI, OpenAI, Anthropic, and Groq
- Intelligent provider selection based on model and task requirements
- Ensemble validation for critical tasks (when enabled)

## Quick Start

### 1. Prerequisites

```bash
# Install AWS SDK
source .venv/bin/activate
pip install boto3 botocore
```

### 2. Configure AWS Credentials

Copy the example configuration:
```bash
cp .env.bedrock.example .env
```

Update `.env` with your AWS credentials:
```env
# AWS Credentials
AWS_ACCESS_KEY_ID=your-access-key-here
AWS_SECRET_ACCESS_KEY=your-secret-key-here
AWS_REGION=us-east-1

# Model Configuration (recommended defaults)
AWS_T0_MODEL=anthropic.claude-3-haiku-20240307-v1:0
AWS_T1_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
AWS_T2_MODEL=anthropic.claude-3-5-sonnet-20240620-v1:0
AWS_T3_MODEL=anthropic.claude-3-opus-20240229-v1:0

# Provider Preferences (use AWS Bedrock)
LLM_T0_PROVIDER=aws_bedrock
LLM_T1_PROVIDER=aws_bedrock
LLM_T2_PROVIDER=aws_bedrock
LLM_T3_PROVIDER=aws_bedrock
```

### 3. Verify Setup

Run the comprehensive test:
```bash
python test_aws_bedrock_integration.py
```

Or use the interactive setup:
```bash
python setup_aws_bedrock.py
```

## Configuration Options

### Basic Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS Access Key | Required |
| `AWS_SECRET_ACCESS_KEY` | AWS Secret Key | Required |
| `AWS_REGION` | AWS Region | us-east-1 |

### Advanced Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_BEDROCK_RETRY_ATTEMPTS` | Number of retry attempts | 3 |
| `AWS_BEDROCK_TIMEOUT` | Request timeout (seconds) | 60 |
| `AWS_BEDROCK_MAX_CONCURRENT` | Max concurrent requests | 10 |
| `AWS_BEDROCK_ENABLE_LOGGING` | Enable detailed logging | true |

### Health Monitoring
| Variable | Description | Default |
|----------|-------------|---------|
| `PROVIDER_HEALTH_CHECK_INTERVAL` | Health check interval (seconds) | 60 |
| `PROVIDER_CIRCUIT_BREAKER_THRESHOLD` | Failures before circuit opens | 5 |
| `PROVIDER_CIRCUIT_BREAKER_TIMEOUT` | Circuit reset timeout (seconds) | 300 |

### Multi-Provider Options
| Variable | Description | Default |
|----------|-------------|---------|
| `ENSEMBLE_ENABLED` | Enable ensemble validation | false |
| `ENSEMBLE_MIN_CONSENSUS` | Minimum consensus score | 0.7 |
| `ENSEMBLE_PROVIDERS` | Providers for ensemble | ["aws_bedrock", "azure_openai"] |

## Usage Examples

### Basic Usage

The integration is seamless - just use the platform normally:

```bash
# Generate code using AWS Bedrock
qlp generate "create a python web scraper"

# The system will automatically use AWS Bedrock if configured
```

### Programmatic Usage

```python
from src.agents.azure_llm_client import llm_client, LLMProvider

# Automatic provider detection (prefers Bedrock for Claude)
response = await llm_client.chat_completion(
    messages=[{"role": "user", "content": "Hello"}],
    model="claude-3-haiku-20240307"  # Auto-routes to Bedrock
)

# Explicit provider selection
response = await llm_client.chat_completion(
    messages=[{"role": "user", "content": "Hello"}],
    model="anthropic.claude-3-5-sonnet-20240620-v1:0",
    provider=LLMProvider.AWS_BEDROCK
)
```

## Architecture

### Provider Selection Logic

1. **Model Detection**: System detects model type from name
2. **Provider Preference**: Checks configuration for preferred provider
3. **Availability Check**: Verifies provider is available and healthy
4. **Fallback**: Automatically falls back to alternative providers if needed

### Tier Mapping Strategy

- **T0 (Simple)**: Claude Haiku - Fast responses for basic tasks
- **T1 (Medium)**: Claude Sonnet - Balanced for most operations
- **T2 (Complex)**: Claude 3.5 Sonnet - Optimized for code generation
- **T3 (Meta)**: Claude Opus - Complex reasoning and architecture

## Monitoring & Debugging

### Health Status

Check provider health:
```python
# Get health status
health = bedrock_client.get_health_status()
print(f"Circuit breaker: {health['circuit_breaker_open']}")
print(f"Success rate: {health['metrics']['success_rate']:.2%}")
```

### Metrics

Monitor performance:
```python
# Get LLM client metrics
metrics = llm_client.get_metrics()
print(f"Total requests: {metrics['total_requests']}")
print(f"Average latency: {metrics['average_latency']:.2f}s")
print(f"Error rate: {metrics['error_rate']:.2%}")
```

### Logging

Enable detailed logging in `.env`:
```env
AWS_BEDROCK_ENABLE_LOGGING=true
LOG_LEVEL=DEBUG
```

View logs for provider selection:
```
2024-07-14 10:15:23 [info] AWS Bedrock client initialized
2024-07-14 10:15:24 [info] Bedrock completion successful model=claude-3-5-sonnet latency=1.234s
```

## Cost Optimization

### Cost Tracking

The platform automatically tracks costs:
- Per-request cost calculation
- Provider-based cost aggregation
- Real-time cost monitoring

### Optimization Strategies

1. **Tier-Appropriate Models**: Use T0 for simple tasks, T3 only when needed
2. **Regional Optimization**: Configure `PREFERRED_REGIONS` for lowest latency
3. **Caching**: Vector memory caches similar requests
4. **Batch Processing**: Group similar requests for efficiency

## Troubleshooting

### Common Issues

1. **"AWS credentials not configured"**
   - Ensure `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set in `.env`
   - Check credentials have Bedrock permissions

2. **"Model not found"**
   - Verify model ID is correct (check BedrockModelRegistry)
   - Ensure your AWS account has access to the model

3. **"Circuit breaker open"**
   - Too many failures detected
   - Check AWS service health
   - Wait for circuit reset or restart service

4. **High latency**
   - Consider using a closer AWS region
   - Enable regional optimization
   - Check concurrent request limits

### Debug Commands

```bash
# Test configuration
python test_aws_bedrock_integration.py

# Check provider availability
python -c "from src.agents.azure_llm_client import llm_client; print(llm_client.get_available_providers())"

# Verify model routing
python -c "from src.agents.azure_llm_client import get_model_for_tier; print(get_model_for_tier('T2'))"
```

## Security Best Practices

1. **Credential Management**
   - Never commit AWS credentials to version control
   - Use IAM roles in production (EC2/ECS/Lambda)
   - Rotate credentials regularly

2. **Access Control**
   - Use least-privilege IAM policies
   - Restrict Bedrock model access as needed
   - Enable AWS CloudTrail for audit logging

3. **Network Security**
   - Use VPC endpoints for private connectivity
   - Configure `AWS_BEDROCK_ENDPOINT` for custom endpoints
   - Enable TLS/SSL for all communications

## Production Deployment

### Recommended Settings

```env
# Production configuration
ENVIRONMENT=production
AWS_BEDROCK_ENABLE_LOGGING=true
ENSEMBLE_ENABLED=true
REGIONAL_OPTIMIZATION_ENABLED=true
PROVIDER_HEALTH_CHECK_INTERVAL=30
PROVIDER_CIRCUIT_BREAKER_THRESHOLD=3
```

### Scaling Considerations

- Adjust `AWS_BEDROCK_MAX_CONCURRENT` based on load
- Monitor rate limits and adjust retry logic
- Use multiple regions for geographic distribution
- Implement request queuing for burst traffic

## Support

For issues or questions:
1. Check test results: `bedrock_test_results.json`
2. Review logs for error details
3. Verify AWS service status
4. Check IAM permissions for Bedrock access

## Next Steps

1. **Test the integration**: Run `test_aws_bedrock_integration.py`
2. **Monitor costs**: Check AWS Cost Explorer for Bedrock usage
3. **Optimize performance**: Tune settings based on workload
4. **Enable monitoring**: Set up CloudWatch dashboards
5. **Plan for scale**: Consider multi-region deployment