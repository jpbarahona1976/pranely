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
from app.api.residues import router as residues_router
from app.api.transporters import router as transporters_router
from app.api.v1 import auth_router as v1_auth_router
from app.api.v1 import orgs_router as v1_orgs_router
from app.api.v1 import billing_router as v1_billing_router
from app.api.v1 import waste_router as v1_waste_router
from app.core.database import close_db, init_db
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    setup_logging(level="INFO", json_output=True)
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="PRANELY API",
    description="SaaS B2B para gestión de residuos industriales",
    version="1.12.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenant isolation middleware (must be added first to inject context)
app.add_middleware(TenantMiddleware)

# Audit middleware (after tenant for org/user context)
app.add_middleware(AuditMiddleware)

# Include routers
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(v1_auth_router, prefix="/api/v1")
app.include_router(v1_orgs_router, prefix="/api/v1")
app.include_router(v1_billing_router, prefix="/api/v1")
app.include_router(v1_waste_router, prefix="/api/v1")
app.include_router(employers_router, prefix="/api")
app.include_router(transporters_router, prefix="/api")
app.include_router(residues_router, prefix="/api")
app.include_router(links_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "PRANELY API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}