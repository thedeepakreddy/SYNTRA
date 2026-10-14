"""FastAPI application factory and middleware configuration."""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from syntra.api.routes import checkpoints, events, health, sessions, workspace
from syntra.core.config import get_settings
from syntra.core.logging import correlation_id_ctx, setup_logging
from syntra.storage.database import get_db_manager


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that injects and propagates X-Correlation-ID headers across requests."""

    async def dispatch(self, request: Request, call_next):
        corr_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        token = correlation_id_ctx.set(corr_id)
        try:
            response: Response = await call_next(request)
            response.headers["X-Correlation-ID"] = corr_id
            return response
        finally:
            correlation_id_ctx.reset(token)


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
        title="SYNTRA API",
        description="SYNTRA: Synchronized Intelligence for Autonomous Engineering — One Vision. Multiple AI Agents. Autonomous Engineering.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Middleware registration
    app.add_middleware(CorrelationIdMiddleware)
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
