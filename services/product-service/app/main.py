from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import Base, engine
from app import models  # Register tables before local bootstrap.
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Local bootstrap only; schema changes later require versioned migrations.
    Base.metadata.create_all(bind=engine)
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(title="MicroShop Product Service", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/ready")
def ready():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(503, "Database unavailable") from None
    return {"status": "ready"}
