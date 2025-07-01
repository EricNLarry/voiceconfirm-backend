from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.db.database import connect_to_mongo, close_mongo_connection
from app.api.auth.routes import router as auth_router
from app.api.orders.routes import router as orders_router
from app.api.calls.routes import router as calls_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting VoiceConfirm API...")
    await connect_to_mongo()
    logger.info("VoiceConfirm API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down VoiceConfirm API...")
    await close_mongo_connection()
    logger.info("VoiceConfirm API shut down successfully")

# Create FastAPI app
app = FastAPI(
    title="VoiceConfirm API",
    description="AI-powered voice order confirmation SaaS platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins + ["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "VoiceConfirm API",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to VoiceConfirm API",
        "docs": "/docs",
        "health": "/health"
    }

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(orders_router, prefix="/api/orders", tags=["Orders"])
app.include_router(calls_router, prefix="/api/calls", tags=["Calls"])

# Import and include integrations router
from app.api.integrations.routes import router as integrations_router
app.include_router(integrations_router, prefix="/api/integrations", tags=["Integrations"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

