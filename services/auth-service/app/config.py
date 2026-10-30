import os

from sqlalchemy.engine import URL


def database_url():
    """Read runtime configuration; URL.create safely handles special characters."""
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    required = ("MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError("Missing database configuration: " + ", ".join(missing))

    return URL.create(
        "mysql+pymysql",
        username=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        host=os.environ.get("DATABASE_HOST", "mysql"),
        port=int(os.environ.get("DATABASE_PORT", "3306")),
        database=os.environ["MYSQL_DATABASE"],
    )
