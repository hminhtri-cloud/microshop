import json
import os
from decimal import Decimal
from http.client import HTTPException as HTTPClientError
from typing import Literal
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator


class ReservedItem(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=99)
    name: str = Field(min_length=1, max_length=120)
    seller_id: int = Field(gt=0)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    @field_validator("price", mode="before")
    @classmethod
    def decimal_string(cls, value):
        if not isinstance(value, str):
            raise ValueError("Price must be a decimal string")
        return value


class Receipt(BaseModel):
    id: int = Field(gt=0)
    status: Literal["reserved", "confirmed", "released"]
    items: list[ReservedItem] = Field(min_length=1, max_length=50)


def stock_request(path: str, body: dict) -> Receipt:
    token = os.getenv("INTERNAL_SERVICE_TOKEN", "")
    if not token:
        raise HTTPException(503, "Internal authentication is not configured")
    base = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8000").rstrip("/")
    request = Request(base + "/internal/stock" + path, data=json.dumps(body).encode(),
                      headers={"Content-Type": "application/json", "X-Service-Token": token})
    try:
        with urlopen(request, timeout=10) as response:
            result = Receipt.model_validate(json.load(response))
    except HTTPError as error:
        if error.code == 409:
            try:
                detail = json.load(error).get("detail")
                if isinstance(detail, dict) and isinstance(detail.get("code"), str):
                    raise HTTPException(409, detail) from None
            except (ValueError, AttributeError):
                pass
        raise HTTPException(503, {"code": "ORDER_RECONCILIATION_REQUIRED",
                                  "message": "Inventory result uncertain; retry with the same key"}) from None
    except (OSError, HTTPClientError, ValueError):
        raise HTTPException(503, {"code": "ORDER_RECONCILIATION_REQUIRED",
                                  "message": "Inventory result uncertain; retry with the same key"}) from None
    return result


def reserve(customer_id: int, key: str, items: list[dict]) -> Receipt:
    result = stock_request("/reservations", {"buyer_id": customer_id, "request_key": key, "items": items})
    expected = {item["product_id"]: item["quantity"] for item in items}
    actual = {item.product_id: item.quantity for item in result.items}
    if expected != actual or len(result.items) != len(items) or result.status != "reserved":
        raise HTTPException(503, "Invalid reservation response; reconciliation required")
    return result


def finalize(customer_id: int, key: str, action: str):
    result = stock_request(f"/reservations/{customer_id}/{key}/{action}", {})
    if result.status != {"confirm": "confirmed", "release": "released"}[action]:
        raise HTTPException(503, "Invalid inventory transition response")
