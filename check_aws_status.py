#!/usr/bin/env python3
"""
Check AWS Bedrock Status
Quick script to check current AWS configuration status
"""

import os
import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def check_env_file():
    """Check if AWS credentials are in .env"""
    print("📋 Checking .env configuration...")
    
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        return False
    
    required_vars = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'AWS_REGION'
    ]
    
    found_vars = {}
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                if key in required_vars:
                    found_vars[key] = bool(value and value != 'your-aws-access-key-here')
    
    all_configured = all(found_vars.get(var, False) for var in required_vars)
    
    for var in required_vars:
        status = "✅" if found_vars.get(var, False) else "❌"
        print(f"  {status} {var}: {'Configured' if found_vars.get(var, False) else 'Not configured'}")
    
    return all_configured

def check_boto3():
    """Check if boto3 is installed"""
    print("\n📦 Checking Python dependencies...")
    try:
        import boto3
        import botocore
        print("  ✅ boto3 installed")
        print("  ✅ botocore installed")
        return True
    except ImportError as e:
        print(f"  ❌ Missing dependency: {e}")
        return False

def check_aws_cli():
    """Check AWS CLI status"""
    print("\n🔧 Checking AWS CLI...")
    try:
        result = subprocess.run(['aws', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ AWS CLI installed: {result.stdout.strip()}")
            
            # Check credentials
            result = subprocess.run(['aws', 'sts', 'get-caller-identity'], capture_output=True, text=True)
            if result.returncode == 0:
                print("  ✅ AWS credentials configured in CLI")
            else:
                print("  ⚠️  AWS CLI credentials not configured")
            return True
    except FileNotFoundError:
        print("  ⚠️  AWS CLI not installed (optional)")
    return False

def check_platform_integration():
    """Check if platform can use AWS Bedrock"""
    print("\n🔌 Checking platform integration...")
    
    try:
        from src.agents.azure_llm_client import llm_client, LLMProvider
        from src.common.config import settings
        
        # Check if Bedrock is available
        providers = llm_client.get_available_providers()
        bedrock_available = 'aws_bedrock' in providers
        
        print(f"  Available providers: {providers}")
        print(f"  {'✅' if bedrock_available else '❌'} AWS Bedrock {'available' if bedrock_available else 'not available'}")
        
        if bedrock_available:
            # Check tier mapping
            from src.agents.azure_llm_client import get_model_for_tier
            print("\n  Tier mappings:")
            for tier in ['T0', 'T1', 'T2', 'T3']:
                model, provider = get_model_for_tier(tier)
                is_bedrock = provider == LLMProvider.AWS_BEDROCK
                icon = "🔵" if is_bedrock else "⚪"
                print(f"    {icon} {tier}: {model} ({provider.value})")
        
        return bedrock_available
        
    except Exception as e:
        print(f"  ❌ Error checking integration: {e}")
        return False

def show_next_steps(env_configured, boto3_installed, platform_ready):
    """Show what needs to be done next"""
    print("\n" + "="*60)
    print("📋 Next Steps:")
    
    step = 1
    
    if not boto3_installed:
        print(f"\n{step}. Install Python dependencies:")
        print("   source .venv/bin/activate")
        print("   pip install boto3 botocore")
        step += 1
    
    if not env_configured:
        print(f"\n{step}. Configure AWS credentials:")
        print("   python configure_aws_bedrock.py")
        print("   OR")
        print("   python setup_aws_bedrock.py")
        step += 1
    
    if env_configured and boto3_installed and not platform_ready:
        print(f"\n{step}. Restart the platform:")
        print("   ./stop_all.sh")
        print("   ./start_all.sh")
        step += 1
    
    if platform_ready:
        print(f"\n✅ AWS Bedrock is configured and ready!")
        print("\nTest it with:")
        print("   qlp generate \"create a python hello world\"")
        print("\nMonitor usage:")
        print("   python test_bedrock_simple.py")
    
    print("\n📚 For detailed instructions, see:")
    print("   - AWS_BEDROCK_CHECKLIST.md")
    print("   - docs/AWS_BEDROCK_SETUP_GUIDE.md")

def main():
    """Main status check"""
    print("🔍 AWS Bedrock Configuration Status")
    print("="*60)
    
    # Run checks
    env_configured = check_env_file()
    boto3_installed = check_boto3()
    aws_cli_status = check_aws_cli()
    platform_ready = check_platform_integration() if (env_configured and boto3_installed) else False
    
    # Summary
    print("\n📊 Summary:")
    print(f"  {'✅' if env_configured else '❌'} Environment configured")
    print(f"  {'✅' if boto3_installed else '❌'} Dependencies installed")
    print(f"  {'✅' if platform_ready else '❌'} Platform integration ready")
    
    # Show next steps
    show_next_steps(env_configured, boto3_installed, platform_ready)
    
    return 0 if platform_ready else 1

if __name__ == "__main__":
    sys.exit(main())