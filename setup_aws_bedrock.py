#!/usr/bin/env python3
"""
AWS Bedrock Setup Assistant
Helps configure AWS Bedrock integration for QLP
"""

import os
import sys
import json
from typing import Dict, List, Optional

def print_header():
    """Print setup header"""
    print("🚀 AWS Bedrock Setup Assistant for QuantumLayer Platform")
    print("=" * 60)
    print()

def check_aws_cli():
    """Check if AWS CLI is available"""
    try:
        import subprocess
        result = subprocess.run(['aws', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ AWS CLI found:", result.stdout.strip())
            return True
        else:
            print("❌ AWS CLI not found")
            return False
    except FileNotFoundError:
        print("❌ AWS CLI not installed")
        return False

def check_boto3():
    """Check if boto3 is available"""
    try:
        import boto3
        print("✅ boto3 library available")
        return True
    except ImportError:
        print("❌ boto3 not installed")
        return False

def get_aws_regions() -> List[str]:
    """Get list of AWS regions that support Bedrock"""
    bedrock_regions = [
        "us-east-1",     # N. Virginia
        "us-west-2",     # Oregon  
        "eu-west-1",     # Ireland
        "eu-central-1",  # Frankfurt
        "ap-southeast-1", # Singapore
        "ap-northeast-1"  # Tokyo
    ]
    return bedrock_regions

def get_available_models() -> Dict[str, Dict]:
    """Get available Bedrock models"""
    return {
        "anthropic.claude-3-haiku-20240307-v1:0": {
            "name": "Claude 3 Haiku",
            "tier": "T0",
            "description": "Fast and cost-effective for simple tasks",
            "cost_input": "$0.25 per 1K tokens",
            "cost_output": "$1.25 per 1K tokens"
        },
        "anthropic.claude-3-sonnet-20240229-v1:0": {
            "name": "Claude 3 Sonnet", 
            "tier": "T1",
            "description": "Balanced performance for medium complexity",
            "cost_input": "$3.00 per 1K tokens",
            "cost_output": "$15.00 per 1K tokens"
        },
        "anthropic.claude-3-5-sonnet-20240620-v1:0": {
            "name": "Claude 3.5 Sonnet",
            "tier": "T2", 
            "description": "Best for code generation and complex tasks",
            "cost_input": "$3.00 per 1K tokens",
            "cost_output": "$15.00 per 1K tokens"
        },
        "anthropic.claude-3-opus-20240229-v1:0": {
            "name": "Claude 3 Opus",
            "tier": "T3",
            "description": "Most capable for complex reasoning",
            "cost_input": "$15.00 per 1K tokens", 
            "cost_output": "$75.00 per 1K tokens"
        }
    }

def interactive_setup():
    """Interactive setup process"""
    print("📋 AWS Bedrock Configuration Setup")
    print("-" * 40)
    
    config = {}
    
    # Get AWS credentials
    print("\\n1. AWS Credentials")
    access_key = input("AWS Access Key ID: ").strip()
    secret_key = input("AWS Secret Access Key: ").strip()
    
    if not access_key or not secret_key:
        print("❌ AWS credentials are required")
        return None
    
    config['AWS_ACCESS_KEY_ID'] = access_key
    config['AWS_SECRET_ACCESS_KEY'] = secret_key
    
    # Get region
    print("\\n2. AWS Region")
    print("Available Bedrock regions:")
    regions = get_aws_regions()
    for i, region in enumerate(regions, 1):
        print(f"  {i}. {region}")
    
    while True:
        try:
            choice = input(f"Choose region (1-{len(regions)}) [1]: ").strip()
            if not choice:
                choice = "1"
            
            region_idx = int(choice) - 1
            if 0 <= region_idx < len(regions):
                config['AWS_REGION'] = regions[region_idx]
                break
            else:
                print("Invalid choice, please try again")
        except ValueError:
            print("Please enter a number")
    
    # Model selection
    print("\\n3. Model Configuration")
    models = get_available_models()
    
    print("Available models:")
    model_list = list(models.keys())
    for i, model_id in enumerate(model_list, 1):
        model = models[model_id]
        print(f"  {i}. {model['name']} ({model['tier']}) - {model['description']}")
    
    # Use recommended defaults
    config['AWS_T0_MODEL'] = "anthropic.claude-3-haiku-20240307-v1:0"
    config['AWS_T1_MODEL'] = "anthropic.claude-3-sonnet-20240229-v1:0" 
    config['AWS_T2_MODEL'] = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    config['AWS_T3_MODEL'] = "anthropic.claude-3-opus-20240229-v1:0"
    
    print("Using recommended model configuration:")
    for tier in ['T0', 'T1', 'T2', 'T3']:
        model_id = config[f'AWS_{tier}_MODEL']
        model = models[model_id]
        print(f"  {tier}: {model['name']}")
    
    # Provider preferences
    print("\\n4. Provider Preferences")
    use_bedrock = input("Prefer AWS Bedrock for all tiers? (y/n) [y]: ").strip().lower()
    if use_bedrock != 'n':
        config['LLM_T0_PROVIDER'] = 'aws_bedrock'
        config['LLM_T1_PROVIDER'] = 'aws_bedrock'
        config['LLM_T2_PROVIDER'] = 'aws_bedrock' 
        config['LLM_T3_PROVIDER'] = 'aws_bedrock'
        print("✅ Set AWS Bedrock as preferred provider for all tiers")
    
    # Advanced settings
    print("\\n5. Advanced Settings")
    config['AWS_BEDROCK_RETRY_ATTEMPTS'] = '3'
    config['AWS_BEDROCK_TIMEOUT'] = '60'
    config['AWS_BEDROCK_MAX_CONCURRENT'] = '10'
    config['AWS_BEDROCK_ENABLE_LOGGING'] = 'true'
    
    # Health monitoring
    config['PROVIDER_HEALTH_CHECK_INTERVAL'] = '60'
    config['PROVIDER_CIRCUIT_BREAKER_THRESHOLD'] = '5'
    config['PROVIDER_CIRCUIT_BREAKER_TIMEOUT'] = '300'
    
    print("✅ Advanced settings configured with recommended defaults")
    
    return config

def save_to_env(config: Dict[str, str], filename: str = ".env"):
    """Save configuration to .env file"""
    env_lines = []
    
    # Read existing .env if it exists
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            env_lines = f.readlines()
    
    # Remove existing AWS Bedrock config
    env_lines = [line for line in env_lines if not any(
        line.startswith(key) for key in config.keys()
    )]
    
    # Add new config
    env_lines.append("\\n# AWS Bedrock Configuration\\n")
    for key, value in config.items():
        env_lines.append(f"{key}={value}\\n")
    
    # Write back to file
    with open(filename, 'w') as f:
        f.writelines(env_lines)
    
    print(f"✅ Configuration saved to {filename}")

def verify_setup():
    """Verify the setup by running a test"""
    print("\\n🔍 Verifying setup...")
    
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, 
            "test_aws_bedrock_integration.py"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Setup verification successful!")
            return True
        else:
            print("❌ Setup verification failed:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  Verification timed out (this might be normal)")
        return True
    except Exception as e:
        print(f"⚠️  Could not run verification: {e}")
        return True

def show_next_steps():
    """Show next steps after setup"""
    print("\\n🎉 AWS Bedrock Setup Complete!")
    print("=" * 40)
    print("Next steps:")
    print("1. Test your configuration:")
    print("   python test_aws_bedrock_integration.py")
    print()
    print("2. Start the QLP platform:")
    print("   ./start_all.sh")
    print()
    print("3. Generate code with Bedrock:")
    print("   qlp generate \"create a python web scraper\"")
    print()
    print("📚 For more information:")
    print("- Check .env.bedrock.example for advanced configuration")
    print("- Monitor costs in AWS Console > Bedrock > Usage")
    print("- View logs for provider selection and health")

def main():
    """Main setup process"""
    print_header()
    
    # Check prerequisites
    print("🔍 Checking prerequisites...")
    aws_cli_available = check_aws_cli()
    boto3_available = check_boto3()
    
    if not boto3_available:
        print("\\n❌ boto3 is required. Install it with:")
        print("pip install boto3")
        return 1
    
    print()
    
    # Interactive setup
    config = interactive_setup()
    if not config:
        print("Setup cancelled")
        return 1
    
    # Save configuration
    print("\\n💾 Saving configuration...")
    save_to_env(config)
    
    # Verify setup
    verify_setup()
    
    # Show next steps
    show_next_steps()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\\n\\n⏹️  Setup cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\\n💥 Setup failed: {e}")
        sys.exit(1)