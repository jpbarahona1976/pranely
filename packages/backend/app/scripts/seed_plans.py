#!/usr/bin/env python
"""
Seed default billing plans for PRANELY.

Usage:
    poetry run python app/scripts/seed_plans.py

Plans seeded:
    - free: Free tier (100 docs/month)
    - pro: Pro tier ($299/month, 2500 docs)
    - enterprise: Enterprise tier ($999/month, 10000 docs)
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from app.core.database import engine
from app.models import BillingPlan, BillingPlanCode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


DEFAULT_PLANS = [
    {
        "code": BillingPlanCode.FREE,
        "name": "Free",
        "description": "Free tier for testing and small projects",
        "price_usd_cents": 0,
        "doc_limit": 100,
        "doc_limit_period": "monthly",
        "features_json": {
            "waste_movements": True,
            "audit_trails": True,
            "basic_support": True,
        },
        "is_active": True,
    },
    {
        "code": BillingPlanCode.PRO,
        "name": "Pro",
        "description": "Professional tier for growing businesses",
        "price_usd_cents": 29900,  # $299.00
        "doc_limit": 2500,
        "doc_limit_period": "monthly",
        "features_json": {
            "waste_movements": True,
            "audit_trails": True,
            "ai_extraction": True,
            "priority_support": True,
            "advanced_reports": True,
        },
        "is_active": True,
    },
    {
        "code": BillingPlanCode.ENTERPRISE,
        "name": "Enterprise",
        "description": "Enterprise tier for large organizations",
        "price_usd_cents": 99900,  # $999.00
        "doc_limit": 10000,
        "doc_limit_period": "monthly",
        "features_json": {
            "waste_movements": True,
            "audit_trails": True,
            "ai_extraction": True,
            "priority_support": True,
            "advanced_reports": True,
            "sso_integration": True,
            "custom_integrations": True,
            "dedicated_account_manager": True,
        },
        "is_active": True,
    },
]


async def seed_plans() -> int:
    """Seed default billing plans. Returns number of plans seeded."""
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async with AsyncSession(engine) as session:
        seeded_count = 0
        
        for plan_data in DEFAULT_PLANS:
            # Check if plan already exists
            code = plan_data["code"]
            result = await session.execute(
                select(BillingPlan).where(BillingPlan.code == code)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.info(f"Plan {code.value} already exists, skipping")
                continue
            
            # Create new plan
            plan = BillingPlan(**plan_data)
            session.add(plan)
            seeded_count += 1
            logger.info(f"Seeding plan: {code.value}")
        
        await session.commit()
        return seeded_count


async def main() -> int:
    """Main entry point."""
    logger.info("Starting billing plans seed...")
    
    try:
        count = await seed_plans()
        
        if count > 0:
            logger.info(f"✅ Successfully seeded {count} billing plans")
        else:
            logger.info("✅ All billing plans already exist, nothing to seed")
        
        return count
    except Exception as e:
        logger.error(f"❌ Failed to seed billing plans: {e}")
        raise


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(0 if exit_code is not None else 1)