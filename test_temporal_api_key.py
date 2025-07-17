#!/usr/bin/env python3
"""
Test Temporal API key format and connection
"""
import os
import jwt
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('.env.cloud')

api_key = os.getenv('TEMPORAL_CLOUD_API_KEY')

print("🔍 Analyzing Temporal API Key...")
print(f"Key length: {len(api_key) if api_key else 0}")

if api_key:
    # Temporal API keys are JWTs
    try:
        # Decode without verification to see the payload
        decoded = jwt.decode(api_key, options={"verify_signature": False})
        print("\n📋 API Key Claims:")
        print(json.dumps(decoded, indent=2))
        
        # Check expiration
        if 'exp' in decoded:
            exp_time = datetime.fromtimestamp(decoded['exp'])
            now = datetime.now()
            print(f"\n⏰ Expiration: {exp_time}")
            print(f"   Current time: {now}")
            if exp_time < now:
                print("   ❌ API KEY IS EXPIRED!")
            else:
                print(f"   ✅ Valid for {(exp_time - now).days} more days")
                
        # Check account and key info
        if 'account_id' in decoded:
            print(f"\n🏢 Account ID: {decoded['account_id']}")
        if 'key_id' in decoded:
            print(f"🔑 Key ID: {decoded['key_id']}")
            
    except Exception as e:
        print(f"❌ Error decoding API key: {e}")
        
print("\n📝 Expected format:")
print("   - JWT token with proper claims")
print("   - Not expired")
print("   - Correct account_id")

print("\n💡 To get a new API key:")
print("   1. Go to https://cloud.temporal.io")
print("   2. Navigate to your namespace settings")
print("   3. Generate a new API key")
print("   4. Update TEMPORAL_CLOUD_API_KEY in .env.cloud")