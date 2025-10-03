"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from newsauto.api.routes import (
    analytics,
    auth,
    content,
    editions,
    health,
    newsletters,
    subscribers,
    tracking,
    unsubscribe,
    verification,
)
from newsauto.core.config import get_settings
from newsauto.core.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Newsauto API...")
    init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down Newsauto API...")


# Create FastAPI app
app = FastAPI(
    title="Newsauto API",
    description="Automated newsletter platform with LLM integration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])

app.include_router(
    auth.router, prefix=f"{settings.api_prefix}/auth", tags=["authentication"]
)

app.include_router(
    newsletters.router,
    prefix=f"{settings.api_prefix}/newsletters",
    tags=["newsletters"],
)

app.include_router(
    subscribers.router,
    prefix=f"{settings.api_prefix}/subscribers",
    tags=["subscribers"],
)

app.include_router(
    content.router, prefix=f"{settings.api_prefix}/content", tags=["content"]
)

app.include_router(
    editions.router, prefix=f"{settings.api_prefix}/editions", tags=["editions"]
)

app.include_router(
    analytics.router, prefix=f"{settings.api_prefix}/analytics", tags=["analytics"]
)

# Public routes (no API prefix)
app.include_router(tracking.router, tags=["tracking"])
app.include_router(unsubscribe.router, tags=["unsubscribe"])
app.include_router(verification.router, tags=["verification"])

# Mount static files (if web directory exists)
try:
    app.mount("/static", StaticFiles(directory="web/static"), name="static")
except RuntimeError:
    logger.warning("Static files directory not found")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Newsauto API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.exception_handler(404)
async def not_found(request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404, content={"error": "Not found", "path": str(request.url)}
    )


@app.exception_handler(500)
async def internal_error(request, exc):
    """Handle 500 errors."""
    logger.error(f"Internal error: {exc}")
    return JSONResponse(status_code=500, content={"error": "Internal server error"})
