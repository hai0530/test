from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import auth, tags, todos
from app.core.config import settings
from app.core.observability import RequestLoggingMiddleware, configure_logging
from app.core.redis import redis_client
from app.db.session import engine

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await redis_client.initialize()
    yield
    # Shutdown
    await redis_client.close()
    await engine.dispose()


app = FastAPI(
    title="Fabbi Todo API",
    description="JWT Authentication + CRUD Todo List API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(todos.router, prefix="/api/v1/todos", tags=["Todos"])
app.include_router(tags.router, prefix="/api/v1/tags", tags=["Tags"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Backward-compatible liveness endpoint."""

    return {"status": "healthy"}


@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """Liveness probe: the process is running and can serve HTTP."""

    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Readiness probe that verifies PostgreSQL and Redis connectivity."""

    checks: dict[str, str] = {}
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    checks["redis"] = "ok" if await redis_client.ping() else "error"
    ready = all(value == "ok" for value in checks.values())
    payload = {"status": "ready" if ready else "not_ready", "checks": checks}
    if not ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload
        )
    return payload
