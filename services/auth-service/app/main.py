from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import engine, Base
from app.routes.auth import router as auth_router
from app.routes.sellers import router as seller_router
from app.security import jwt_settings

# Import models để SQLAlchemy biết các table
from app import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    jwt_settings()
    # Local bootstrap only; versioned migrations will replace this later.
    Base.metadata.create_all(bind=engine)
    try:
        yield
    finally:
        engine.dispose()

app = FastAPI(
    title = "microservice-auth-service",
    description = "This is a microservice for authentication and authorization.",
    version = "1.0.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(seller_router)

@app.get("/")
def read_root():
    return {
        "service": "auth-service",
        "status": "running"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/ready")
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ready"}
