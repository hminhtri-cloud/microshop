import json
import os
from http.client import HTTPException as HTTPClientError
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Identity:
    id: int
    role: str


def get_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Identity:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_url = (
        os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
        .rstrip("/")
        + "/auth/me"
    )

    request = Request(
        auth_url,
        headers={
            "Authorization": "Bearer " + credentials.credentials,
        },
    )

    try:
        with urlopen(request, timeout=3) as response:
            user = json.load(response)

    except HTTPError as error:
        if error.code in (401, 403):
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired access token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None

        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable",
        ) from None

    except (OSError, HTTPClientError, ValueError):
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable",
        ) from None

    if (
        not isinstance(user, dict)
        or type(user.get("id")) is not int
        or user["id"] <= 0
        or user.get("role") not in ("customer", "seller", "admin")
    ):
        raise HTTPException(
            status_code=503,
            detail="Invalid authentication response",
        )

    return Identity(
        id=user["id"],
        role=user["role"],
    )


def require_buyer(
    identity: Identity = Depends(get_identity),
) -> Identity:
    if identity.role not in ("customer", "seller"):
        raise HTTPException(
            status_code=403,
            detail="Buyer permission required",
        )

    return identity


def require_role(role: str):
    def check(identity: Identity = Depends(get_identity)) -> Identity:
        if identity.role != role:
            raise HTTPException(403, "Insufficient permissions")
        return identity
    return check
