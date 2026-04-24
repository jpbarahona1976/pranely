"""API v1 package - Stable API endpoints for Auth, Orgs, Billing, and Waste."""
from app.api.v1.auth.router import router as auth_router
from app.api.v1.orgs.router import router as orgs_router
from app.api.v1.billing.router import router as billing_router
from app.api.v1.waste import router as waste_router

__all__ = ["auth_router", "orgs_router", "billing_router", "waste_router"]