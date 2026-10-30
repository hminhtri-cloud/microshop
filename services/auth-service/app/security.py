import os
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

ALGORITHM = "HS256"
ISSUER = "microshop-auth"
AUDIENCE = "microshop"
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Used to avoid skipping the hash verification for unknown email addresses.
DUMMY_HASH = password_context.hash("dummy-password-not-a-user")


def jwt_settings():
    secret = os.environ.get("JWT_SECRET", "")
    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 bytes")
    minutes = int(os.environ.get("JWT_EXPIRE_MINUTES", "30"))
    if minutes <= 0:
        raise RuntimeError("JWT_EXPIRE_MINUTES must be positive")
    return secret, minutes


def create_access_token(user_id: int):
    secret, minutes = jwt_settings()
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
        "iss": ISSUER,
        "aud": AUDIENCE,
    }
    return jwt.encode(claims, secret, algorithm=ALGORITHM), minutes * 60


def decode_access_token(token: str):
    secret, _ = jwt_settings()
    return jwt.decode(
        token,
        secret,
        algorithms=[ALGORITHM],
        audience=AUDIENCE,
        issuer=ISSUER,
        options={"require_exp": True, "require_sub": True, "require_iat": True},
    )
