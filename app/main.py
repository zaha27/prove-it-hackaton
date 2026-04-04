"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.dependencies import (
    get_price_service,
    get_sentiment_service,
    get_change_service,
    get_mcp_service,
)
from app.price.router import router as price_router
from app.sentiment.router import router as sentiment_router
from app.change.router import router as change_router
from app.mcp.router import router as mcp_router
from app.macro.router import router as macro_router

app = FastAPI(
    title="Commodity Intelligence API",
    description="Production-ready FastAPI backend for real-time commodity price data, sentiment analysis, and 24-hour change calculation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(price_router, prefix="/api/v1/price", tags=["price"])
app.include_router(sentiment_router, prefix="/api/v1/sentiment", tags=["sentiment"])
app.include_router(change_router, prefix="/api/v1/change", tags=["change"])
app.include_router(mcp_router, prefix="/api/v1/mcp", tags=["mcp"])
app.include_router(macro_router, prefix="/macro", tags=["macro"])


@app.get("/", tags=["root"])
async def root():
    """Root endpoint returning API information."""
    return {
        "message": "Commodity Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "price": "/api/v1/price",
            "sentiment": "/api/v1/sentiment",
            "change": "/api/v1/change",
            "mcp": "/api/v1/mcp",
            "macro": "/macro",
        },
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Dependency injection setup
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    # Services are initialized via dependency injection
    pass


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    pass
