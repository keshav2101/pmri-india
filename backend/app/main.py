"""main.py — FastAPI Application Entrypoint for PMRI India (Unified Market)."""
from __future__ import annotations
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.database import create_async_engine, Base, get_db

from app.routers.auth import router as auth_router
from app.routers.orgs import router as orgs_router
from app.routers.portfolios import router as portfolios_router
from app.routers.market import router as market_router
from app.routers.rules import router as rules_router
from app.routers.quotes import router as quotes_router
from app.routers.policies import router as policies_router
from app.routers.settlements import router as settlements_router
from app.routers.ledger import router as ledger_router

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("pmri")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure DB tables exist
    logger.info(f"Attempting to connect to database at: {settings.database_url.split('@')[-1] if '@' in settings.database_url else 'unknown'}")
    try:
        engine = create_async_engine(settings.database_url, echo=False)
        async with engine.begin() as conn:
            import app.models  # load all ORM models
            logger.info("Creating all tables if not exist...")
            await conn.run_sync(Base.metadata.create_all)
        
        # Run inline migrations for new columns added after initial deploy
        async with engine.begin() as conn:
            # Add portfolios.status column if it doesn't exist (migration for existing DBs)
            logger.info("Running inline migrations...")
            await conn.execute(
                __import__('sqlalchemy').text(
                    "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'"
                )
            )
        logger.info("Database schema synchronized.")
    except Exception as e:
        logger.error(f"CRITICAL: Database connection or migration failed: {e}")
        # Allow app to start even if DB fails, so healthcheck can pass and we can read logs

    
    # Load ML Model
    try:
        from app.services.ml_service import ml_service
        ml_service._ensure_loaded()
        logger.info("ML model and pricing artifacts loaded successfully.")
    except Exception as e:
        logger.error("Failed to load ML artifacts: %s", e)
        
    yield
    await engine.dispose()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="PMRI Global API",
    description="Portfolio Market Risk Insurance supporting NSE and NASDAQ equities.",
    version="1.0.0",
    lifespan=lifespan,
)

# Register Routers
app.include_router(auth_router)
app.include_router(orgs_router)
app.include_router(portfolios_router)
app.include_router(market_router)
app.include_router(rules_router)
app.include_router(quotes_router)
app.include_router(policies_router)
app.include_router(settlements_router)
app.include_router(ledger_router)


# CORS — allow all origins for demo deployment
# In production, restrict this to specific frontend domains
_cors_origins = ["*"]
logger.info(f"CORS allow_origins: {_cors_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,  # must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "app": "pmri-global", "demo_mode": settings.demo_mode}
