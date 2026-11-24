import asyncio
import logging
import os
from time import perf_counter
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.checkout import reconcile_once
from app.database import Base, engine
from app.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS
from app.routes import router

logger = logging.getLogger(__name__)


async def reconciliation_loop():
    while True:
        try:
            await asyncio.to_thread(reconcile_once)
        except SQLAlchemyError:
            logger.warning("Reconciliation database unavailable")
        except Exception as error:
            # Keep recovery running even if a dependency returns an unexpected
            # transport error. Log type only, never credentials/request data.
            logger.error("Reconciliation deferred: error_type=%s", type(error).__name__)
        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("INTERNAL_SERVICE_TOKEN"):
        raise RuntimeError("INTERNAL_SERVICE_TOKEN is required")
    # New local DB only; existing schema changes must use versioned migration.
    Base.metadata.create_all(bind=engine)
    worker = asyncio.create_task(reconciliation_loop())
    try:
        yield
    finally:
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass
        engine.dispose()


app = FastAPI(title="MicroShop Order Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)
app.mount("/metrics", make_asgi_app())


@app.middleware("http")
async def request_id(request: Request, call_next):
    # The metrics endpoint is scraped internally. Excluding it prevents every
    # scrape from becoming application traffic and keeps the series useful.
    if request.url.path == "/metrics":
        return await call_next(request)

    request.state.request_id = str(uuid4())
    started_at = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request.state.request_id
        return response
    finally:
        route = request.scope.get("route")
        route_template = getattr(route, "path", "unmatched")
        labels = (request.method, route_template, str(status_code))
        HTTP_REQUESTS.labels(*labels).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(*labels).observe(perf_counter() - started_at)


@app.exception_handler(HTTPException)
async def http_error(request: Request, error: HTTPException):
    codes = {401: "AUTHENTICATION_REQUIRED", 403: "FORBIDDEN", 404: "ORDER_NOT_FOUND",
             409: "INVALID_STATUS_TRANSITION", 422: "VALIDATION_ERROR", 503: "ORDER_DEPENDENCY_UNAVAILABLE"}
    body = error.detail if isinstance(error.detail, dict) else {
        "code": codes.get(error.status_code, "HTTP_ERROR"), "message": str(error.detail)}
    return JSONResponse({**body, "request_id": request.state.request_id}, status_code=error.status_code, headers=error.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    return JSONResponse({"code": "VALIDATION_ERROR", "message": "Invalid request data",
                         "details": [{"field": ".".join(map(str, item["loc"])), "message": item["msg"]}
                                     for item in error.errors()], "request_id": request.state.request_id}, status_code=422)


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError):
    logger.warning("Order database error: request_id=%s", request.state.request_id)
    return JSONResponse({"code": "ORDER_RECONCILIATION_REQUIRED",
                         "message": "Database unavailable; retry writes with the same key",
                         "request_id": request.state.request_id}, status_code=503)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/ready")
def ready():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready"}
