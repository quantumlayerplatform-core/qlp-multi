#!/usr/bin/env python3
"""
AWS Bedrock Configuration Assistant
Helps configure and verify AWS Bedrock setup for QuantumLayer Platform
"""

import os
import sys
import json
import subprocess
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class BedrockConfigurator:
    """AWS Bedrock configuration assistant"""
    
    def __init__(self):
        self.config = {}
        self.aws_cli_available = self.check_aws_cli()
        
    def check_aws_cli(self) -> bool:
        """Check if AWS CLI is available"""
        try:
            result = subprocess.run(['aws', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ AWS CLI found:", result.stdout.strip())
                return True
        except FileNotFoundError:
            pass
        print("⚠️  AWS CLI not found (optional, but recommended)")
        return False
    
    def check_aws_credentials(self) -> Tuple[bool, Dict]:
        """Check if AWS credentials are configured"""
        if not self.aws_cli_available:
            return False, {"message": "AWS CLI not available"}
        
        try:
            result = subprocess.run(
                ['aws', 'sts', 'get-caller-identity'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                identity = json.loads(result.stdout)
                print("✅ AWS credentials configured")
                print(f"   Account: {identity['Account']}")
                print(f"   User ARN: {identity['Arn']}")
                return True, identity
            else:
                print("❌ AWS credentials not configured")
                return False, {"error": result.stderr}
                
        except Exception as e:
            return False, {"error": str(e)}
    
    def list_bedrock_models(self, region: str = "us-east-1") -> List[Dict]:
        """List available Bedrock models"""
        if not self.aws_cli_available:
            return []
        
        try:
            result = subprocess.run(
                ['aws', 'bedrock', 'list-foundation-models', '--region', region,
                 '--query', "modelSummaries[?contains(modelId, 'claude')].[modelId, modelName]"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                models = json.loads(result.stdout)
                print(f"\n📋 Available Claude models in {region}:")
                for model in models:
                    print(f"   - {model[0]}")
                return models
            else:
                print(f"⚠️  Could not list models: {result.stderr}")
                return []
                
        except Exception as e:
            print(f"⚠️  Error listing models: {e}")
            return []
    
    def test_model_access(self, model_id: str, region: str = "us-east-1") -> bool:
        """Test if we can invoke a specific model"""
        if not self.aws_cli_available:
            return False
        
        print(f"\n🧪 Testing access to {model_id}...")
        
        test_body = {
            "messages": [{"role": "user", "content": "Hello"}],
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 10
        }
        
        try:
            result = subprocess.run(
                ['aws', 'bedrock-runtime', 'invoke-model',
                 '--model-id', model_id,
                 '--body', json.dumps(test_body),
                 '--region', region,
                 'test_output.json'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"   ✅ Successfully accessed {model_id}")
                # Clean up test file
                if os.path.exists('test_output.json'):
                    os.remove('test_output.json')
                return True
            else:
                print(f"   ❌ Failed to access {model_id}")
                print(f"   Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error testing model: {e}")
            return False
    
    def configure_env_file(self):
        """Configure .env file with AWS Bedrock settings"""
        print("\n🔧 Configuring .env file...")
        
        # Read existing .env
        env_lines = []
        env_dict = {}
        
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    env_lines.append(line)
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_dict[key] = value
        
        # Get AWS credentials
        print("\n📝 Enter AWS credentials:")
        access_key = input("AWS Access Key ID: ").strip()
        secret_key = input("AWS Secret Access Key: ").strip()
        
        if not access_key or not secret_key:
            print("❌ AWS credentials are required")
            return False
        
        # Get region preference
        print("\n🌍 Select AWS Region:")
        regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
        for i, region in enumerate(regions, 1):
            print(f"   {i}. {region}")
        
        region_choice = input("Choose region (1-4) [1]: ").strip() or "1"
        try:
            region = regions[int(region_choice) - 1]
        except:
            region = "us-east-1"
        
        # AWS Bedrock configuration
        aws_config = {
            "AWS_ACCESS_KEY_ID": access_key,
            "AWS_SECRET_ACCESS_KEY": secret_key,
            "AWS_REGION": region,
            "AWS_T0_MODEL": "anthropic.claude-3-haiku-20240307-v1:0",
            "AWS_T1_MODEL": "anthropic.claude-3-sonnet-20240229-v1:0",
            "AWS_T2_MODEL": "anthropic.claude-3-5-sonnet-20240620-v1:0",
            "AWS_T3_MODEL": "anthropic.claude-3-opus-20240229-v1:0",
            "LLM_T0_PROVIDER": "aws_bedrock",
            "LLM_T1_PROVIDER": "aws_bedrock",
            "LLM_T2_PROVIDER": "aws_bedrock",
            "LLM_T3_PROVIDER": "aws_bedrock",
            "AWS_BEDROCK_RETRY_ATTEMPTS": "3",
            "AWS_BEDROCK_TIMEOUT": "60",
            "AWS_BEDROCK_MAX_CONCURRENT": "10",
            "AWS_BEDROCK_ENABLE_LOGGING": "true",
            "PROVIDER_HEALTH_CHECK_INTERVAL": "60",
            "PROVIDER_CIRCUIT_BREAKER_THRESHOLD": "5",
            "PROVIDER_CIRCUIT_BREAKER_TIMEOUT": "300",
            "ENSEMBLE_ENABLED": "false",
            "REGIONAL_OPTIMIZATION_ENABLED": "true",
            "PREFERRED_REGIONS": f'["{region}"]'
        }
        
        # Update env_dict with new values
        env_dict.update(aws_config)
        
        # Write back to .env
        with open('.env', 'w') as f:
            # Write existing non-AWS lines
            for line in env_lines:
                if not any(line.strip().startswith(key + '=') for key in aws_config.keys()):
                    f.write(line)
            
            # Add AWS Bedrock configuration
            f.write("\n# AWS Bedrock Configuration\n")
            for key, value in aws_config.items():
                f.write(f"{key}={value}\n")
        
        print("✅ Configuration saved to .env")
        return True
    
    def run_integration_test(self):
        """Run the integration test"""
        print("\n🧪 Running integration test...")
        
        try:
            result = subprocess.run(
                ['python', 'test_bedrock_simple.py'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            print(result.stdout)
            if result.stderr:
                print("Errors:", result.stderr)
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("⚠️  Test timed out")
            return False
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
    
    def show_cost_estimates(self):
        """Show cost estimates for different usage patterns"""
        print("\n💰 AWS Bedrock Cost Estimates")
        print("=" * 50)
        
        models = {
            "Claude 3 Haiku (T0)": {"input": 0.00025, "output": 0.00125},
            "Claude 3 Sonnet (T1)": {"input": 0.003, "output": 0.015},
            "Claude 3.5 Sonnet (T2)": {"input": 0.003, "output": 0.015},
            "Claude 3 Opus (T3)": {"input": 0.015, "output": 0.075}
        }
        
        usage_patterns = [
            {"name": "Light (100 requests/day)", "requests": 100, "avg_input": 500, "avg_output": 1000},
            {"name": "Medium (1000 requests/day)", "requests": 1000, "avg_input": 500, "avg_output": 1000},
            {"name": "Heavy (10000 requests/day)", "requests": 10000, "avg_input": 500, "avg_output": 1000}
        ]
        
        for pattern in usage_patterns:
            print(f"\n{pattern['name']}:")
            for model_name, costs in models.items():
                daily_input_tokens = pattern['requests'] * pattern['avg_input']
                daily_output_tokens = pattern['requests'] * pattern['avg_output']
                
                daily_cost = (
                    (daily_input_tokens / 1000) * costs['input'] +
                    (daily_output_tokens / 1000) * costs['output']
                )
                monthly_cost = daily_cost * 30
                
                print(f"  {model_name}: ${daily_cost:.2f}/day, ${monthly_cost:.2f}/month")
    
    def run_configuration_wizard(self):
        """Run the complete configuration wizard"""
        print("🚀 AWS Bedrock Configuration Wizard")
        print("=" * 60)
        
        # Step 1: Check AWS CLI
        print("\n1️⃣  Checking prerequisites...")
        
        # Step 2: Check existing credentials
        print("\n2️⃣  Checking AWS credentials...")
        creds_ok, creds_info = self.check_aws_credentials()
        
        # Step 3: List available models (if credentials exist)
        if creds_ok and self.aws_cli_available:
            print("\n3️⃣  Checking Bedrock models...")
            models = self.list_bedrock_models()
            
            # Test model access
            if models:
                test_model = "anthropic.claude-3-haiku-20240307-v1:0"
                self.test_model_access(test_model)
        
        # Step 4: Configure .env
        print("\n4️⃣  Configuring platform...")
        if self.configure_env_file():
            
            # Step 5: Run integration test
            print("\n5️⃣  Testing integration...")
            if self.run_integration_test():
                print("\n✅ AWS Bedrock configuration complete!")
            else:
                print("\n⚠️  Integration test failed. Check your configuration.")
        
        # Step 6: Show cost estimates
        self.show_cost_estimates()
        
        # Next steps
        print("\n📋 Next Steps:")
        print("1. If you haven't already, enable Claude models in AWS Bedrock console")
        print("2. Start the platform: ./start_all.sh")
        print("3. Test with: qlp generate \"create a hello world program\"")
        print("4. Monitor costs in AWS Cost Explorer")
        print("\n📚 See docs/AWS_BEDROCK_SETUP_GUIDE.md for detailed instructions")


def main():
    """Main entry point"""
    configurator = BedrockConfigurator()
    
    try:
        configurator.run_configuration_wizard()
        return 0
    except KeyboardInterrupt:
        print("\n\n⏹️  Configuration cancelled")
        return 130
    except Exception as e:
        print(f"\n💥 Configuration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())