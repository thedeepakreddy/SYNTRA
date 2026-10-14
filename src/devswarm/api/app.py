"""FastAPI application factory and middleware configuration."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from devswarm.api.routes import checkpoints, events, health, sessions, workspace
from devswarm.core.config import get_settings
from devswarm.core.logging import setup_logging
from devswarm.storage.database import get_db_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    settings = get_settings()
    setup_logging(level=settings.log_level)

    # Initialize persistence schema
    db = get_db_manager()
    await db.init_tables()

    yield

    # Clean shutdown
    await db.close()


def create_app() -> FastAPI:
    """Construct and configure the production FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="DevSwarm API",
        description="Production Autonomous Multi-Agent Software Engineering Platform API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(sessions.router)
    app.include_router(checkpoints.router)
    app.include_router(workspace.router)
    app.include_router(events.router)

    return app


app = create_app()
