import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def database_url():
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    required = ("MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError("Missing database configuration: " + ", ".join(missing))
    return URL.create(
        "mysql+pymysql", username=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"], host=os.getenv("DATABASE_HOST", "mysql"),
        port=int(os.getenv("DATABASE_PORT", "3306")), database=os.environ["MYSQL_DATABASE"],
    )


engine = create_engine(database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db():
    with SessionLocal() as session:
        yield session
