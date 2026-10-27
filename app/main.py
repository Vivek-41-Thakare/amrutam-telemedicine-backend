import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, make_asgi_app
from redis import Redis
from sqlalchemy import text

from app.api.routes import router
from app.core.config import settings
from app.core.database import engine

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("amrutam")


REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Production-oriented telemedicine backend starter. "
        "Review README and security notes before production use."
    ),
    docs_url="/docs",
    openapi_url="/openapi.json",
)


app.mount("/metrics", make_asgi_app())


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Idempotency-Key",
        "X-Request-ID",
    ],
)


@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()

    response = await call_next(request)

    duration_seconds = time.perf_counter() - start
    duration_ms = round(duration_seconds * 1000, 2)

    response.headers["X-Request-ID"] = request_id

    # Keep metric labels bounded; avoid dynamic IDs and arbitrary URL paths.
    path = request.url.path
    if path.startswith(settings.api_v1_prefix):
        path = "/api/v1/{endpoint}"

    REQUEST_COUNT.labels(
        method=request.method,
        path=path,
        status_code=str(response.status_code),
    ).inc()

    REQUEST_DURATION.labels(
        method=request.method,
        path=path,
    ).observe(duration_seconds)

    logger.info(
        {
            "event": "http_request",
            "request_id": request_id,
            "method": request.method,
            "path": path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
    )

    return response


@app.get("/health/live", tags=["health"])
def liveness():
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
def readiness():
    checks = {}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"

    try:
        redis_client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
        )
        redis_client.ping()
        redis_client.close()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    status_code = (
        200 if all(value == "ok" for value in checks.values()) else 503
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if status_code == 200 else "not_ready",
            "checks": checks,
        },
    )


app.include_router(router, prefix=settings.api_v1_prefix)
