"""FastAPI application factory for PRANELY."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.employers import router as employers_router
from app.api.employer_transporter_links import router as links_router
from app.api.health import router as health_router
from app.api.middleware.audit import AuditMiddleware
from app.api.middleware.tenant import TenantMiddleware
from app.api.middleware.rate_limit import RateLimitMiddleware  # FASE 8C.2: Rate limiting
from app.observability.middleware import MetricsMiddleware  # FASE 9B: Metrics middleware
from app.api.residues import router as residues_router
from app.api.transporters import router as transporters_router
from app.api.bridge import router as bridge_router
from app.api.v1 import auth_router as v1_auth_router
from app.api.v1 import orgs_router as v1_orgs_router
from app.api.v1 import billing_router as v1_billing_router
from app.api.v1 import waste_router as v1_waste_router
from app.api.v1 import command_router as v1_command_router
from app.api.v1 import waste_review_router as v1_waste_review_router  # FASE 2.1 FIX 2
from app.api.v1 import command_operators_router as v1_command_operators_router  # FASE 2.1 FIX 2
from app.api.v1 import invite_router as v1_invite_router  # FASE 2.1 FIX 2
from app.core.database import close_db, init_db
from app.core.logging import setup_logging
from app.observability.metrics import router as metrics_router  # FASE 9B: Prometheus metrics
from app.observability.metrics import setup_metrics  # FASE 9B


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    setup_logging(level="INFO", json_output=True)
    
    # FASE 9B: Setup Prometheus metrics
    from app.core.config import get_settings
    settings = get_settings()
    setup_metrics(environment=settings.ENV)
    
    # FASE 8C.2 FIX: Validate configuration in production
    from app.core.config import validate_settings, ConfigurationError
    try:
        validate_settings()
    except ConfigurationError as e:
        # Fail fast in production if config is invalid
        import logging
        logging.critical(f"Configuration error: {e}")
        raise RuntimeError(f"Application cannot start: {e}")
    
    # FASE 8C.2 FIX: Initialize rate limiting
    from app.api.middleware.rate_limit import setup_rate_limiting
    rate_limiter = await setup_rate_limiting()
    
    await init_db()
    # Start bridge cleanup task (async)
    from app.api.bridge import start_cleanup_task
    await start_cleanup_task()
    yield
    # Shutdown
    from app.api.bridge import stop_cleanup_task
    stop_cleanup_task()
    await rate_limiter.close()
    await close_db()


app = FastAPI(
    title="PRANELY API",
    description="SaaS B2B para gestión de residuos industriales",
    version="1.13.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# MIDDLEWARE ORDER (CRITICAL - ASGI LIFO execution)
# =============================================================================
# IMPORTANT: Starlette/FastAPI executes middlewares in LIFO order
# (Last-In-First-Out). The LAST middleware added is the FIRST to execute.
#
# DESIRED EXECUTION ORDER:
#   1. TenantMiddleware  → Injects x-org-id, org_id, user_id into scope
#   2. RateLimitMiddleware → Uses org_id for rate limiting
#   3. AuditMiddleware   → Uses org_id for audit logging
#   4. MetricsMiddleware → Captures x-org-id from scope for Prometheus
#
# Therefore, we MUST add them in REVERSE order:
#   app.add_middleware(MetricsMiddleware)  → Executes 4th (captures correct org_id)
#   app.add_middleware(AuditMiddleware)   → Executes 3rd
#   app.add_middleware(RateLimitMiddleware)→ Executes 2nd
#   app.add_middleware(TenantMiddleware)  → Executes 1st (injects x-org-id first)
# =============================================================================

# FASE 9B: MetricsMiddleware - ADD FIRST (executes LAST)
# Captures x-org-id AFTER TenantMiddleware injects it
app.add_middleware(MetricsMiddleware)

# Audit middleware - ADD SECOND (executes 3rd)
app.add_middleware(AuditMiddleware)

# FASE 8C.2: Rate limiting middleware - ADD THIRD (executes 2nd)
app.add_middleware(RateLimitMiddleware)

# Tenant isolation middleware - ADD LAST (executes FIRST)
# Injects x-org-id, org_id, user_id into request.scope before other middlewares
app.add_middleware(TenantMiddleware)

# Include routers
app.include_router(health_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")  # FASE 9B: Prometheus metrics endpoint
app.include_router(auth_router, prefix="/api")
app.include_router(v1_auth_router, prefix="/api/v1")
app.include_router(v1_orgs_router, prefix="/api/v1")
app.include_router(v1_billing_router, prefix="/api/v1")
app.include_router(v1_waste_router, prefix="/api/v1")
app.include_router(v1_command_router, prefix="/api/v1")
app.include_router(v1_waste_review_router, prefix="/api/v1")  # FASE 2.1 FIX 2
app.include_router(v1_command_operators_router, prefix="/api/v1")  # FASE 2.1 FIX 2
app.include_router(v1_invite_router, prefix="/api/v1")  # FASE 2.1 FIX 2
app.include_router(employers_router, prefix="/api")
app.include_router(transporters_router, prefix="/api")
app.include_router(residues_router, prefix="/api")
app.include_router(links_router, prefix="/api")
app.include_router(bridge_router)  # prefix="/bridge" ya en router


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "PRANELY API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
