"""
FastAPI application instance with lifespan management.

This module creates the FastAPI application with proper configuration,
middleware, and lifespan management for database and logging setup.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.exceptions.handler import register_exception_handlers
from api.lifespan import lifespan
from api.middleware import ContextMiddleware, LoggingMiddleware, RequestIDMiddleware
from api.models.errors import HTTPException
from api.settings import get_settings

# Load settings
settings = get_settings()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,  # Attach lifespan context manager
        responses={
            500: {"model": HTTPException, "description": "Internal Server Error"},
            404: {"model": HTTPException, "description": "Resource Not Found"},
            400: {"model": HTTPException, "description": "Bad Request"},
            409: {"model": HTTPException, "description": "Conflict"},
            403: {"model": HTTPException, "description": "Forbidden"},
            422: {"model": HTTPException, "description": "Unprocessable Entity"},
        },
    )
    register_exception_handlers(app)
    # Configure CORS middleware
    if settings.SERVER.CORS_ENABLED:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.SERVER.CORS_ORIGINS,
            allow_credentials=settings.SERVER.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.SERVER.CORS_ALLOW_METHODS,
            allow_headers=settings.SERVER.CORS_ALLOW_HEADERS,
        )
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ContextMiddleware)
    app.add_middleware(RequestIDMiddleware)
    # Add request logging middleware

    # Include routers here
    # app.include_router(user_router, prefix="/api/v1")

    return app


# Create the application instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/{id}")
async def health_check(id: int):
    """Health check endpoint."""
    from api.database import get_db_pool

    try:
        db_pool = get_db_pool()
        pool_stats = await db_pool.get_pool_stats()

        return {
            "status": "healthy",
            "database": {
                "connected": pool_stats["initialized"],
                "pool_size": pool_stats.get("size", 0),
                "pool_free": pool_stats.get("free", 0),
            },
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
