"""Aggregation of all API v1 routers for SYNTRA Control Plane."""

from fastapi import APIRouter

from syntra.api.v1.routes import (
    agents,
    approvals,
    audit,
    benchmarks,
    missions,
    models,
    projects,
    system,
    tasks,
)

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(system.router)
v1_router.include_router(projects.router)
v1_router.include_router(missions.router)
v1_router.include_router(tasks.router)
v1_router.include_router(approvals.router)
v1_router.include_router(agents.router)
v1_router.include_router(models.router)
v1_router.include_router(benchmarks.router)
v1_router.include_router(audit.router)
