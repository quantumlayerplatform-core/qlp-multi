#!/usr/bin/env python3
"""
Update to Latest Claude Models
Updates .env to use the newest Claude models available in your AWS account
"""

import os
import re
from datetime import datetime

def update_env_with_latest_models():
    """Update .env file with latest Claude models"""
    
    print("🚀 Updating to Latest Claude Models")
    print("=" * 60)
    
    # Model mappings - old to new
    model_updates = {
        # Current -> Latest available in your account
        "AWS_T0_MODEL": {
            "old": "anthropic.claude-3-haiku-20240307-v1:0",
            "new": "anthropic.claude-3-5-haiku-20241022-v1:0",
            "name": "Claude 3.5 Haiku (Faster!)"
        },
        "AWS_T1_MODEL": {
            "old": "anthropic.claude-3-sonnet-20240229-v1:0", 
            "new": "anthropic.claude-3-7-sonnet-20250219-v1:0",
            "name": "Claude 3.7 Sonnet (Newest!)"
        },
        "AWS_T2_MODEL": {
            "old": "anthropic.claude-3-5-sonnet-20240620-v1:0",
            "new": "anthropic.claude-sonnet-4-20250514-v1:0",
            "name": "Claude 4 Sonnet"
        },
        "AWS_T3_MODEL": {
            "old": "anthropic.claude-3-opus-20240229-v1:0",
            "new": "anthropic.claude-opus-4-20250514-v1:0", 
            "name": "Claude 4 Opus (Most Powerful!)"
        }
    }
    
    # Backup current .env
    backup_file = f".env.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open('.env', 'r') as f:
        content = f.read()
    
    with open(backup_file, 'w') as f:
        f.write(content)
    print(f"✅ Backed up current config to: {backup_file}")
    
    # Update models
    print("\n📝 Updating models:")
    updated_content = content
    updates_made = 0
    
    for key, model_info in model_updates.items():
        pattern = f"{key}={re.escape(model_info['old'])}"
        replacement = f"{key}={model_info['new']}"
        
        if re.search(pattern, updated_content):
            updated_content = re.sub(pattern, replacement, updated_content)
            print(f"  ✅ {key}: {model_info['name']}")
            print(f"     {model_info['old']} → {model_info['new']}")
            updates_made += 1
        else:
            # Try to find any value for this key
            pattern = f"{key}=.*"
            if re.search(pattern, updated_content):
                updated_content = re.sub(pattern, replacement, updated_content)
                print(f"  ✅ {key}: Updated to {model_info['name']}")
                updates_made += 1
    
    if updates_made > 0:
        # Write updated content
        with open('.env', 'w') as f:
            f.write(updated_content)
        print(f"\n✅ Updated {updates_made} models to latest versions!")
    else:
        print("\n⚠️  No updates needed - models may already be latest")
    
    # Show configuration summary
    print("\n📊 New Model Configuration:")
    print("  T0 (Fast): Claude 3.5 Haiku - Best for simple tasks")
    print("  T1 (Balanced): Claude 3.7 Sonnet - Great for most tasks") 
    print("  T2 (Code): Claude 4 Sonnet - Excellent for code generation")
    print("  T3 (Complex): Claude 4 Opus - Most capable for complex reasoning")
    
    print("\n⚠️  IMPORTANT: You must enable these models in AWS Bedrock console!")
    print("  Go to: https://us-west-2.console.aws.amazon.com/bedrock/home?region=us-west-2#/modelaccess")
    print("  See enable_bedrock_models.md for details")
    
    return updates_made

def show_model_comparison():
    """Show comparison of old vs new models"""
    print("\n📈 Model Improvements:")
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│ Old Model                → New Model              │ Benefits │")
    print("├─────────────────────────────────────────────────────────────┤")
    print("│ Claude 3 Haiku          → Claude 3.5 Haiku       │ 2x faster│")
    print("│ Claude 3 Sonnet         → Claude 3.7 Sonnet      │ Smarter  │")
    print("│ Claude 3.5 Sonnet       → Claude 4 Sonnet        │ Better   │")
    print("│ Claude 3 Opus           → Claude 4 Opus          │ Powerful │")
    print("└─────────────────────────────────────────────────────────────┘")

def main():
    """Main update process"""
    
    # Check if .env exists
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Run configure_aws_bedrock.py first")
        return 1
    
    # Update models
    updates = update_env_with_latest_models()
    
    # Show comparison
    show_model_comparison()
    
    print("\n🎯 Next Steps:")
    print("1. Enable the new models in AWS Bedrock console")
    print("2. Restart the platform: ./stop_all.sh && ./start_all.sh")
    print("3. Test with: python test_bedrock_simple.py")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())