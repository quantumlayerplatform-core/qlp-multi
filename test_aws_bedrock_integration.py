#!/usr/bin/env python3
"""
Test AWS Bedrock Integration
Comprehensive test suite for AWS Bedrock provider integration
"""

import asyncio
import os
import sys
import json
import time
from typing import Dict, Any, List
from datetime import datetime

# Add src to path
sys.path.insert(0, '/Users/satish/qlp-projects/qlp-dev/src')

from src.common.config import settings
from src.agents.azure_llm_client import llm_client, LLMProvider, get_model_for_tier
from src.agents.aws_bedrock_client import bedrock_client, BedrockModelRegistry


class AWSBedrockTester:
    """Comprehensive AWS Bedrock integration tester"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "configuration": {},
            "provider_availability": {},
            "model_tests": {},
            "tier_mapping": {},
            "performance": {},
            "health_checks": {},
            "failover_tests": {},
            "errors": []
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def record_error(self, test_name: str, error: str):
        """Record test errors"""
        self.results["errors"].append({
            "test": test_name,
            "error": str(error),
            "timestamp": datetime.now().isoformat()
        })
    
    def test_configuration(self) -> Dict[str, Any]:
        """Test AWS configuration validation"""
        self.log("Testing AWS Bedrock configuration...")
        
        config_result = {
            "aws_config_valid": False,
            "has_credentials": False,
            "valid_region": False,
            "models_configured": {},
            "settings_validation": {}
        }
        
        try:
            # Check AWS configuration
            aws_validation = settings.validate_aws_config()
            config_result["settings_validation"] = aws_validation
            config_result["aws_config_valid"] = aws_validation["is_valid"]
            
            # Check credentials
            config_result["has_credentials"] = bool(
                settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY
            )
            
            # Check region
            config_result["valid_region"] = settings.AWS_REGION in [
                "us-east-1", "us-west-2", "eu-west-1", "eu-central-1",
                "ap-southeast-1", "ap-northeast-1"
            ]
            
            # Check model configuration
            for tier in ["T0", "T1", "T2", "T3"]:
                model_attr = f"AWS_{tier}_MODEL"
                model_id = getattr(settings, model_attr, None)
                config_result["models_configured"][tier] = {
                    "model_id": model_id,
                    "in_registry": BedrockModelRegistry.get_model(model_id) is not None if model_id else False
                }
            
            self.log(f"Configuration valid: {config_result['aws_config_valid']}")
            
        except Exception as e:
            self.record_error("configuration", e)
            config_result["error"] = str(e)
        
        self.results["configuration"] = config_result
        return config_result
    
    def test_provider_availability(self) -> Dict[str, Any]:
        """Test provider availability and initialization"""
        self.log("Testing provider availability...")
        
        availability_result = {
            "providers": {},
            "bedrock_available": False,
            "fallback_providers": []
        }
        
        try:
            # Check all providers
            available_providers = llm_client.get_available_providers()
            for provider in ["openai", "azure_openai", "anthropic", "groq", "aws_bedrock"]:
                is_available = provider in available_providers
                availability_result["providers"][provider] = is_available
                
                if is_available and provider != "aws_bedrock":
                    availability_result["fallback_providers"].append(provider)
            
            # Specific Bedrock check
            availability_result["bedrock_available"] = llm_client.is_provider_available(LLMProvider.AWS_BEDROCK)
            
            self.log(f"Available providers: {available_providers}")
            self.log(f"AWS Bedrock available: {availability_result['bedrock_available']}")
            
        except Exception as e:
            self.record_error("provider_availability", e)
            availability_result["error"] = str(e)
        
        self.results["provider_availability"] = availability_result
        return availability_result
    
    async def test_bedrock_models(self) -> Dict[str, Any]:
        """Test individual Bedrock models"""
        self.log("Testing Bedrock models...")
        
        models_result = {
            "tested_models": {},
            "successful_models": [],
            "failed_models": [],
            "performance": {}
        }
        
        if not llm_client.is_provider_available(LLMProvider.AWS_BEDROCK):
            models_result["error"] = "AWS Bedrock not available"
            self.results["model_tests"] = models_result
            return models_result
        
        # Test models for each tier
        test_models = [
            settings.AWS_T0_MODEL,
            settings.AWS_T1_MODEL,
            settings.AWS_T2_MODEL,
            settings.AWS_T3_MODEL
        ]
        
        for model_id in test_models:
            if not model_id:
                continue
                
            self.log(f"Testing model: {model_id}")
            
            try:
                start_time = time.time()
                
                # Simple test message
                response = await llm_client.chat_completion(
                    messages=[{"role": "user", "content": "Hello! Please respond with 'AWS Bedrock working correctly'."}],
                    model=model_id,
                    provider=LLMProvider.AWS_BEDROCK,
                    max_tokens=50,
                    temperature=0.1
                )
                
                latency = time.time() - start_time
                
                models_result["tested_models"][model_id] = {
                    "success": True,
                    "response": response["content"][:100],  # First 100 chars
                    "latency": latency,
                    "tokens": response.get("usage", {}),
                    "cost": response.get("cost", {})
                }
                
                models_result["successful_models"].append(model_id)
                models_result["performance"][model_id] = latency
                
                self.log(f"✅ {model_id}: {latency:.2f}s")
                
            except Exception as e:
                self.record_error(f"model_test_{model_id}", e)
                models_result["tested_models"][model_id] = {
                    "success": False,
                    "error": str(e)
                }
                models_result["failed_models"].append(model_id)
                self.log(f"❌ {model_id}: {str(e)}")
        
        self.results["model_tests"] = models_result
        return models_result
    
    def test_tier_mapping(self) -> Dict[str, Any]:
        """Test tier to model mapping"""
        self.log("Testing tier mapping...")
        
        tier_result = {
            "tier_mappings": {},
            "provider_preferences": {},
            "bedrock_prioritized": {}
        }
        
        try:
            for tier in ["T0", "T1", "T2", "T3"]:
                model, provider = get_model_for_tier(tier)
                tier_result["tier_mappings"][tier] = {
                    "model": model,
                    "provider": provider.value
                }
                
                # Check if Bedrock is prioritized for code generation tiers
                is_bedrock = provider == LLMProvider.AWS_BEDROCK
                tier_result["bedrock_prioritized"][tier] = is_bedrock
                
                self.log(f"Tier {tier}: {model} ({provider.value})")
            
            # Check provider preferences from config
            tier_result["provider_preferences"] = {
                "T0": settings.LLM_T0_PROVIDER,
                "T1": settings.LLM_T1_PROVIDER,
                "T2": settings.LLM_T2_PROVIDER,
                "T3": settings.LLM_T3_PROVIDER
            }
            
        except Exception as e:
            self.record_error("tier_mapping", e)
            tier_result["error"] = str(e)
        
        self.results["tier_mapping"] = tier_result
        return tier_result
    
    async def test_provider_detection(self) -> Dict[str, Any]:
        """Test automatic provider detection"""
        self.log("Testing provider detection...")
        
        detection_result = {
            "claude_models": {},
            "gpt_models": {},
            "bedrock_models": {}
        }
        
        try:
            # Test Claude model detection
            claude_models = [
                "claude-3-haiku-20240307",
                "claude-3-sonnet-20240229",
                "claude-3-5-sonnet-20240620",
                "claude-3-opus-20240229"
            ]
            
            for model in claude_models:
                detected = llm_client._detect_provider(model)
                detection_result["claude_models"][model] = detected.value
                expected = LLMProvider.AWS_BEDROCK if llm_client.is_provider_available(LLMProvider.AWS_BEDROCK) else LLMProvider.ANTHROPIC
                self.log(f"Claude {model}: {detected.value} (expected: {expected.value})")
            
            # Test GPT model detection
            gpt_models = ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"]
            for model in gpt_models:
                detected = llm_client._detect_provider(model)
                detection_result["gpt_models"][model] = detected.value
                self.log(f"GPT {model}: {detected.value}")
            
            # Test Bedrock-specific models
            bedrock_models = [
                "anthropic.claude-3-haiku-20240307-v1:0",
                "amazon.titan-text-premier-v1:0"
            ]
            
            for model in bedrock_models:
                detected = llm_client._detect_provider(model)
                detection_result["bedrock_models"][model] = detected.value
                self.log(f"Bedrock {model}: {detected.value}")
            
        except Exception as e:
            self.record_error("provider_detection", e)
            detection_result["error"] = str(e)
        
        self.results["provider_detection"] = detection_result
        return detection_result
    
    async def test_health_checks(self) -> Dict[str, Any]:
        """Test health monitoring"""
        self.log("Testing health checks...")
        
        health_result = {
            "bedrock_health": {},
            "llm_client_metrics": {},
            "circuit_breaker": {}
        }
        
        try:
            if llm_client.is_provider_available(LLMProvider.AWS_BEDROCK):
                # Direct Bedrock health check
                bedrock_health = await bedrock_client.health_check()
                health_result["bedrock_health"] = {
                    "healthy": bedrock_health,
                    "status": bedrock_client.get_health_status()
                }
                
                self.log(f"Bedrock health: {'✅ Healthy' if bedrock_health else '❌ Unhealthy'}")
            
            # LLM client metrics
            metrics = llm_client.get_metrics()
            health_result["llm_client_metrics"] = metrics
            
            self.log(f"LLM Client metrics: {metrics['total_requests']} requests, {metrics['error_rate']:.2%} error rate")
            
        except Exception as e:
            self.record_error("health_checks", e)
            health_result["error"] = str(e)
        
        self.results["health_checks"] = health_result
        return health_result
    
    async def test_failover_scenario(self) -> Dict[str, Any]:
        """Test failover between providers"""
        self.log("Testing failover scenarios...")
        
        failover_result = {
            "primary_test": {},
            "fallback_test": {},
            "failover_success": False
        }
        
        try:
            # Test primary provider (should be Bedrock if configured)
            test_message = [{"role": "user", "content": "Test primary provider"}]
            
            try:
                response = await llm_client.chat_completion(
                    messages=test_message,
                    model="claude-3-haiku-20240307",  # Should route to Bedrock if available
                    max_tokens=50
                )
                
                failover_result["primary_test"] = {
                    "success": True,
                    "provider": response.get("provider"),
                    "model": response.get("model")
                }
                
                self.log(f"Primary provider test: ✅ {response.get('provider')}")
                
            except Exception as e:
                failover_result["primary_test"] = {
                    "success": False,
                    "error": str(e)
                }
                self.log(f"Primary provider test: ❌ {str(e)}")
            
            # Test explicit fallback
            if llm_client.is_provider_available(LLMProvider.OPENAI):
                try:
                    response = await llm_client.chat_completion(
                        messages=test_message,
                        model="gpt-3.5-turbo",
                        provider=LLMProvider.OPENAI,
                        max_tokens=50
                    )
                    
                    failover_result["fallback_test"] = {
                        "success": True,
                        "provider": response.get("provider"),
                        "model": response.get("model")
                    }
                    
                    failover_result["failover_success"] = True
                    self.log("Fallback provider test: ✅ OpenAI")
                    
                except Exception as e:
                    failover_result["fallback_test"] = {
                        "success": False,
                        "error": str(e)
                    }
                    self.log(f"Fallback provider test: ❌ {str(e)}")
            
        except Exception as e:
            self.record_error("failover_scenario", e)
            failover_result["error"] = str(e)
        
        self.results["failover_tests"] = failover_result
        return failover_result
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and generate comprehensive report"""
        self.log("🚀 Starting comprehensive AWS Bedrock integration test...")
        self.log("=" * 60)
        
        start_time = time.time()
        
        # Run all tests
        self.test_configuration()
        self.test_provider_availability()
        await self.test_bedrock_models()
        self.test_tier_mapping()
        await self.test_provider_detection()
        await self.test_health_checks()
        await self.test_failover_scenario()
        
        total_time = time.time() - start_time
        
        # Generate summary
        summary = self.generate_summary(total_time)
        self.results["summary"] = summary
        
        self.log("=" * 60)
        self.log("📊 Test Summary:")
        self.log(f"Total execution time: {total_time:.2f}s")
        self.log(f"Configuration valid: {summary['config_valid']}")
        self.log(f"Bedrock available: {summary['bedrock_available']}")
        self.log(f"Models tested: {summary['models_tested']}")
        self.log(f"Successful models: {summary['successful_models']}")
        self.log(f"Errors encountered: {summary['total_errors']}")
        
        if summary['bedrock_available'] and summary['successful_models'] > 0:
            self.log("🎉 AWS Bedrock integration is working correctly!")
        else:
            self.log("⚠️  AWS Bedrock integration needs attention")
        
        return self.results
    
    def generate_summary(self, total_time: float) -> Dict[str, Any]:
        """Generate test summary"""
        return {
            "total_time": total_time,
            "config_valid": self.results.get("configuration", {}).get("aws_config_valid", False),
            "bedrock_available": self.results.get("provider_availability", {}).get("bedrock_available", False),
            "models_tested": len(self.results.get("model_tests", {}).get("tested_models", {})),
            "successful_models": len(self.results.get("model_tests", {}).get("successful_models", [])),
            "failed_models": len(self.results.get("model_tests", {}).get("failed_models", [])),
            "total_errors": len(self.results.get("errors", [])),
            "health_status": "healthy" if self.results.get("health_checks", {}).get("bedrock_health", {}).get("healthy", False) else "unhealthy"
        }
    
    def save_results(self, filename: str = "bedrock_test_results.json"):
        """Save test results to file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            self.log(f"Results saved to {filename}")
        except Exception as e:
            self.log(f"Failed to save results: {e}", "ERROR")


async def main():
    """Run the comprehensive test suite"""
    tester = AWSBedrockTester()
    
    # Check if AWS credentials are configured
    if not (settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY):
        print("⚠️  AWS credentials not configured!")
        print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file")
        print("See .env.bedrock.example for configuration template")
        return
    
    try:
        results = await tester.run_comprehensive_test()
        tester.save_results()
        
        print("\n" + "=" * 60)
        print("🔗 Integration Test Complete!")
        print("Results saved to bedrock_test_results.json")
        
        # Return exit code based on success
        if results["summary"]["bedrock_available"] and results["summary"]["successful_models"] > 0:
            return 0
        else:
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return 130
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)