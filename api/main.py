"""
ORION Architekt-AT FastAPI Main Application
Production-ready API with all Austrian building regulations endpoints
"""

import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import Base, engine
from api.middleware import LoggingMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from api.middleware.auth import router as auth_router
from api.models import User
from api.routers import (
    ai_recommendations,
    bim_integration,
    bundesland,
    calculations,
    collaboration,
    compliance,
    elsa_validation,
    hitl_bridge,
    reports,
    tendering,
    validation,
)
from orion_logging import get_logger, setup_default_logging

# Setup logging
setup_default_logging()
logger = get_logger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("🚀 ORION Architekt-AT API starting up...")
    logger.info("✅ Database initialized")
    logger.info("✅ All routers loaded")
    logger.info("🌐 API ready at http://0.0.0.0:8000")
    logger.info("📚 Documentation at http://0.0.0.0:8000/docs")
    yield
    logger.info("🛑 ORION Architekt-AT API shutting down...")


# Initialize FastAPI app
app = FastAPI(
    lifespan=lifespan,
    title="ORION Architekt-AT API",
    description="""
    🏗️ **Comprehensive Austrian Building Regulations API**

    Complete OIB-RL compliance, ÖNORM standards, and building calculations for all 9 Austrian Bundesländer.

    ## Features

    * 🎯 **30+ Calculation Functions** - U-Wert, Stellplätze, Barrierefreiheit, Fluchtwege, etc.
    * 📋 **OIB-RL 1-6 Complete** - Full compliance checking
    * 🗺️ **9 Bundesländer** - Wien, Tirol, Salzburg, etc.
    * 🔍 **Knowledge Base Validation** - RIS Austria, OIB, ÖNORM, hora.gv.at
    * 🤖 **AI-Powered Recommendations** - UNIQUE: ML-based optimization
    * 🏗️ **BIM Integration** - UNIQUE: IFC file processing
    * 👥 **Real-time Collaboration** - UNIQUE: Multi-user project work
    * 📊 **Advanced Analytics** - Performance metrics and insights
    * 📝 **ÖNORM A 2063 Tendering** - UNIQUE: Professional Austrian tendering system

    ## Authentication

    Most endpoints require JWT authentication. Get your token from `/auth/token`.

    ## Rate Limits

    * Anonymous: 100 requests/hour
    * Authenticated: 1000 requests/hour
    * Premium: Unlimited
    """,
    version="3.0.0",
    contact={
        "name": "ORION Architekt-AT Team",
        "url": "https://github.com/Alvoradozerouno/ORION-Architekt-AT",
        "email": "support@orion-architekt.at",
    },
    license_info={"name": "MIT License", "url": "https://opensource.org/licenses/MIT"},
    openapi_tags=[
        {
            "name": "calculations",
            "description": "Building calculations (U-Wert, Stellplätze, etc.)",
        },
        {"name": "compliance", "description": "OIB-RL & ÖNORM compliance checks"},
        {"name": "validation", "description": "Knowledge base validation"},
        {"name": "bundesland", "description": "Bundesland-specific regulations"},
        {"name": "reports", "description": "Generate comprehensive reports"},
        {"name": "tendering", "description": "📝 ÖNORM A 2063 Tendering & Bid Management (UNIQUE)"},
        {"name": "ai", "description": "🤖 AI-powered recommendations (UNIQUE)"},
        {"name": "bim", "description": "🏗️ BIM integration (UNIQUE)"},
        {"name": "collaboration", "description": "👥 Real-time collaboration (UNIQUE)"},
        {"name": "auth", "description": "Authentication & authorization"},
        {"name": "health", "description": "Health & monitoring"},
    ],
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Include routers
app.include_router(calculations.router, prefix="/api/v1/calculations", tags=["calculations"])
app.include_router(compliance.router, prefix="/api/v1/compliance", tags=["compliance"])
app.include_router(validation.router, prefix="/api/v1/validation", tags=["validation"])
app.include_router(bundesland.router, prefix="/api/v1/bundesland", tags=["bundesland"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(tendering.router, tags=["tendering"])  # Uses own prefix
app.include_router(ai_recommendations.router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(bim_integration.router, prefix="/api/v1/bim", tags=["bim"])
app.include_router(collaboration.router, prefix="/api/v1/collaboration", tags=["collaboration"])
app.include_router(elsa_validation.router, tags=["elsa"])
app.include_router(hitl_bridge.router, tags=["hitl"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])


# Health check endpoints
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "version": "3.0.0", "timestamp": time.time()}


@app.get("/health/ready", tags=["health"])
async def readiness_check():
    """Readiness check for kubernetes/docker"""
    from sqlalchemy import text

    from api.database import get_db

    db_gen = get_db()
    db = next(db_gen)
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected", "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


@app.get("/health/live", tags=["health"])
async def liveness_check():
    """Liveness check for kubernetes/docker"""
    return {"status": "alive", "timestamp": time.time()}


# Root endpoint
@app.get("/", tags=["health"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "ORION Architekt-AT API",
        "version": "3.0.0",
        "description": "Austrian Building Regulations API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "unique_features": [
            "AI-Powered Building Optimization",
            "BIM Integration (IFC Processing)",
            "Real-time Multi-user Collaboration",
            "Complete OIB-RL 1-6 Coverage",
            "All 9 Austrian Bundesländer",
            "Knowledge Base Validation",
        ],
    }


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="ORION Architekt-AT API",
        version="3.0.0",
        description=app.description,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code, content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500, content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
