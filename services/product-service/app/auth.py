import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Identity:
    id: int
    role: str


def get_identity(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Identity:
    if credentials is None:
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    url = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000").rstrip("/") + "/auth/me"
    request = Request(url, headers={"Authorization": "Bearer " + credentials.credentials})
    try:
        with urlopen(request, timeout=3) as response:
            body = json.load(response)
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise HTTPException(401, "Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"}) from None
        raise HTTPException(503, "Authentication service unavailable") from None
    except (URLError, TimeoutError, ValueError):
        raise HTTPException(503, "Authentication service unavailable") from None
    if not isinstance(body, dict) or type(body.get("id")) is not int or body.get("id") <= 0 or body.get("role") not in ("customer", "seller", "admin"):
        raise HTTPException(503, "Invalid authentication response")
    return Identity(id=body["id"], role=body["role"])


def require_role(role: str):
    def check(identity: Identity = Depends(get_identity)):
        if identity.role != role:
            raise HTTPException(403, "Insufficient permissions")
        return identity
    return check
