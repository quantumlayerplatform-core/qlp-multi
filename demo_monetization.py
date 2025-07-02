#!/usr/bin/env python3
"""Demo script to showcase monetization features"""

import asyncio
import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.auth.service import AuthService
from src.billing.service import BillingService
from src.billing.models import (
    Base, Organization, User, SubscriptionTier, 
    ActionType, UserRole
)
from src.common.database import Base as CommonBase

# Demo database URL (using async SQLite for demo)
DATABASE_URL = "sqlite+aiosqlite:///demo_monetization.db"


async def setup_database():
    """Create database tables"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    # Drop and recreate all tables for a clean demo
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(CommonBase.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(CommonBase.metadata.create_all)
    
    return engine


async def demo_user_registration(session: AsyncSession):
    """Demo: User registration and organization creation"""
    print("\n" + "="*60)
    print("🚀 DEMO: User Registration & Organization Setup")
    print("="*60)
    
    auth_service = AuthService(session)
    
    # Register first user (becomes organization owner)
    print("\n1️⃣ Registering new user...")
    user1, org = await auth_service.register_user(
        email="john@startup.com",
        password="secure123",
        full_name="John Doe",
        organization_name="Awesome Startup Inc"
    )
    
    print(f"✅ User created: {user1.email}")
    print(f"✅ Organization created: {org.name}")
    print(f"   - ID: {org.id}")
    print(f"   - Subscription: {org.subscription_tier.value} (FREE)")
    print(f"   - User role: {user1.role.value}")
    
    # Create JWT token
    token = auth_service.create_token(user1)
    print(f"\n🔑 JWT Token (first 50 chars): {token[:50]}...")
    
    # Create API key
    api_key_obj, api_key = await auth_service.create_api_key(
        user_id=user1.id,
        name="Production API Key",
        scopes=["read", "write"]
    )
    print(f"\n🔐 API Key created: {api_key}")
    print(f"   - Name: {api_key_obj.name}")
    print(f"   - Scopes: {api_key_obj.scopes}")
    
    return user1, org, token, api_key


async def demo_usage_tracking(session: AsyncSession, user: User, org: Organization):
    """Demo: Track usage and show billing"""
    print("\n" + "="*60)
    print("📊 DEMO: Usage Tracking & Billing")
    print("="*60)
    
    billing_service = BillingService(session)
    
    # Simulate some usage
    print("\n1️⃣ Simulating code generation usage...")
    
    actions = [
        ("T0", "Simple function generation", 1500, 250),
        ("T1", "API endpoint generation", 3500, 450),
        ("T2", "Complex algorithm", 8000, 1200),
        ("T0", "Helper function", 1200, 180),
        ("T3", "Full microservice", 25000, 3500),
    ]
    
    for i, (tier, description, tokens, compute_ms) in enumerate(actions, 1):
        usage = await billing_service.track_usage(
            organization_id=org.id,
            user_id=user.id,
            action_type=ActionType.CODE_GENERATION,
            resource_type=tier,
            resource_id=f"capsule_{i}",
            tokens_used=tokens,
            compute_time_ms=compute_ms,
            metadata={"description": description}
        )
        
        print(f"   ✓ {description}")
        print(f"     - Model: {tier}, Tokens: {tokens:,}, Time: {compute_ms}ms")
        print(f"     - Cost: ${float(usage.cost):.4f}")
    
    # Track some API calls
    print("\n2️⃣ Tracking API usage...")
    for i in range(50):
        await billing_service.track_usage(
            organization_id=org.id,
            user_id=user.id,
            action_type=ActionType.API_CALL,
            metadata={"endpoint": f"/api/v1/endpoint{i}"}
        )
    print("   ✓ 50 API calls tracked")
    
    await session.commit()
    
    # Show usage summary
    print("\n3️⃣ Usage Summary for Current Month:")
    summary = await billing_service.get_usage_summary(org.id)
    
    print(f"\n   Period: {summary['period']['start']} to {summary['period']['end']}")
    print(f"\n   By Action Type:")
    for action, stats in summary['by_action'].items():
        print(f"   - {action}:")
        print(f"     • Count: {stats['count']}")
        print(f"     • Cost: ${stats['cost']:.4f}")
        print(f"     • Tokens: {stats['tokens']:,}")
    
    print(f"\n   TOTAL COST: ${summary['totals']['cost']:.4f}")
    
    # Check quota
    print("\n4️⃣ Checking Quotas (Free Tier = 10 generations/month):")
    allowed, reason = await billing_service.check_quota(org.id, ActionType.CODE_GENERATION)
    print(f"   - Can generate more code? {allowed}")
    if not allowed:
        print(f"   - Reason: {reason}")
    
    # Estimate monthly bill
    print("\n5️⃣ Estimated Monthly Bill:")
    estimate = await billing_service.estimate_monthly_bill(org.id)
    print(f"   - Subscription Tier: {estimate['subscription_tier']}")
    print(f"   - Base Cost: ${estimate['base_cost']}")
    print(f"   - Usage Cost: ${estimate['usage_cost']:.2f}")
    print(f"   - Total Estimated: ${estimate['total_estimated']:.2f}")


async def demo_subscription_upgrade(session: AsyncSession, org: Organization):
    """Demo: Upgrade subscription"""
    print("\n" + "="*60)
    print("⬆️  DEMO: Subscription Upgrade")
    print("="*60)
    
    print(f"\n1️⃣ Current subscription: {org.subscription_tier.value}")
    
    # Simulate upgrade
    print("\n2️⃣ Upgrading to Professional tier...")
    org.subscription_tier = SubscriptionTier.PROFESSIONAL
    await session.commit()
    
    print(f"✅ Upgraded to: {org.subscription_tier.value}")
    print(f"   - Monthly cost: $499")
    print(f"   - Included: 1,000 generations")
    print(f"   - Overage rate: $0.75/generation")
    
    # Now check quota again
    billing_service = BillingService(session)
    allowed, reason = await billing_service.check_quota(org.id, ActionType.CODE_GENERATION)
    print(f"\n3️⃣ Can generate more code now? {allowed}")


async def demo_multi_tenancy(session: AsyncSession):
    """Demo: Multi-tenant isolation"""
    print("\n" + "="*60)
    print("🏢 DEMO: Multi-Tenant Data Isolation")
    print("="*60)
    
    auth_service = AuthService(session)
    
    # Create two different organizations
    print("\n1️⃣ Creating two separate organizations...")
    
    # Org 1
    user_a, org_a = await auth_service.register_user(
        email="alice@company-a.com",
        password="secure123",
        full_name="Alice Smith",
        organization_name="Company A"
    )
    
    # Org 2
    user_b, org_b = await auth_service.register_user(
        email="bob@company-b.com",
        password="secure123",
        full_name="Bob Jones",
        organization_name="Company B"
    )
    
    print(f"✅ Organization A: {org_a.name} (ID: {org_a.id})")
    print(f"✅ Organization B: {org_b.name} (ID: {org_b.id})")
    
    # Track usage for each
    billing_service = BillingService(session)
    
    print("\n2️⃣ Tracking usage for each organization...")
    
    # Company A usage
    for i in range(3):
        await billing_service.track_usage(
            organization_id=org_a.id,
            user_id=user_a.id,
            action_type=ActionType.CODE_GENERATION,
            resource_type="T1"
        )
    
    # Company B usage
    for i in range(7):
        await billing_service.track_usage(
            organization_id=org_b.id,
            user_id=user_b.id,
            action_type=ActionType.CODE_GENERATION,
            resource_type="T2"
        )
    
    await session.commit()
    
    # Show isolated summaries
    print("\n3️⃣ Usage summaries (isolated by organization):")
    
    summary_a = await billing_service.get_usage_summary(org_a.id)
    summary_b = await billing_service.get_usage_summary(org_b.id)
    
    print(f"\n   Company A:")
    print(f"   - Generations: {summary_a['by_action'].get('code_generation', {}).get('count', 0)}")
    print(f"   - Total cost: ${summary_a['totals']['cost']:.4f}")
    
    print(f"\n   Company B:")
    print(f"   - Generations: {summary_b['by_action'].get('code_generation', {}).get('count', 0)}")
    print(f"   - Total cost: ${summary_b['totals']['cost']:.4f}")
    
    print("\n✅ Data is completely isolated between organizations!")


async def demo_api_simulation():
    """Simulate API endpoints that would be in the real app"""
    print("\n" + "="*60)
    print("🌐 DEMO: API Endpoints (What the UI would call)")
    print("="*60)
    
    endpoints = {
        "Authentication": [
            "POST /auth/register - Register new user/organization",
            "POST /auth/login - Login and get JWT token",
            "POST /auth/api-keys - Create API key",
        ],
        "Billing": [
            "GET /billing/subscription - Get current subscription",
            "POST /billing/upgrade - Upgrade subscription",
            "GET /billing/usage - Get usage summary",
            "GET /billing/invoices - Get invoice history",
        ],
        "Code Generation (with billing)": [
            "POST /generate/capsule - Generate code (tracks usage)",
            "GET /capsule/{id} - Get capsule (tracks API call)",
            "POST /validate - Validate code (tracks usage)",
        ],
        "Admin": [
            "GET /admin/organizations - List all organizations",
            "GET /admin/metrics - Platform metrics",
            "GET /admin/revenue - Revenue analytics",
        ]
    }
    
    print("\nAvailable API Endpoints:")
    for category, endpoints_list in endpoints.items():
        print(f"\n📁 {category}:")
        for endpoint in endpoints_list:
            print(f"   • {endpoint}")


async def main():
    """Run the complete demo"""
    print("\n🎯 QUANTUM LAYER PLATFORM - MONETIZATION DEMO")
    print("=" * 60)
    
    # Setup database
    engine = await setup_database()
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Run demos
        user, org, token, api_key = await demo_user_registration(session)
        await demo_usage_tracking(session, user, org)
        await demo_subscription_upgrade(session, org)
        await demo_multi_tenancy(session)
        await demo_api_simulation()
    
    print("\n" + "="*60)
    print("✅ Demo completed! This shows how the monetization system works.")
    print("\n💡 Next Steps:")
    print("   1. Build Web UI for user registration/login")
    print("   2. Create billing dashboard")
    print("   3. Integrate Stripe for payments")
    print("   4. Deploy and start onboarding customers!")
    
    # Cleanup
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())