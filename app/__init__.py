from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.binance import router as binance_router

def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application
    """
    app = FastAPI(
        title="Binance C2C API",
        description="FastAPI application to fetch top USDT/TZS ads from Binance C2C market",
        version="1.0.0"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(binance_router, prefix="/api", tags=["binance"])
    
    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint to check if API is running"""
        return {"message": "Welcome to Binance C2C API"}
    
    return app
