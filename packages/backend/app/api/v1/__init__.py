"""API v1 package - Stable API endpoints for Auth, Orgs, Billing, Waste, and Command Center."""
from app.api.v1.auth.router import router as auth_router
from app.api.v1.orgs.router import router as orgs_router
from app.api.v1.billing.router import router as billing_router
from app.api.v1.waste import router as waste_router
from app.api.v1.waste_review import router as waste_review_router
from app.api.v1.command.router import router as command_router
# FASE 2 FIX 4: Command operators CRUD
from app.api.v1.command_operators import router as command_operators_router
# FASE 2 FIX 5: Invite with secure hash
from app.api.v1.invite import router as invite_router

__all__ = [
    "auth_router", "orgs_router", "billing_router", 
    "waste_router", "waste_review_router", 
    "command_router", "command_operators_router", "invite_router"
]
