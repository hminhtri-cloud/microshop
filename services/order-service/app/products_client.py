import json
import os
from decimal import Decimal
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class ProductSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int = Field(gt=0)
    seller_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=120)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    quantity: int = Field(ge=0)
    status: Literal["active"]

    @field_validator("price", mode="before")
    @classmethod
    def validate_price_format(cls, value):
        # Product Service hiện trả giá dưới dạng chuỗi thập phân.
        # Không dùng float do browser hoặc API khác tự gửi.
        if not isinstance(value, str):
            raise ValueError("Product price must be a decimal string")

        return value


def fetch_product(product_id: int) -> ProductSnapshot:
    if product_id <= 0:
        raise ValueError("product_id must be positive")

    base_url = os.getenv(
        "PRODUCT_SERVICE_URL",
        "http://product-service:8000",
    ).rstrip("/")

    request = Request(f"{base_url}/products/{product_id}")

    try:
        with urlopen(request, timeout=3) as response:
            data = json.load(response)

    except HTTPError as error:
        if error.code == 404:
            raise HTTPException(
                status_code=409,
                detail=f"Product {product_id} is no longer available",
            ) from None

        raise HTTPException(
            status_code=503,
            detail="Product service unavailable",
        ) from None

    except (URLError, TimeoutError, ValueError):
        raise HTTPException(
            status_code=503,
            detail="Product service unavailable",
        ) from None

    try:
        product = ProductSnapshot.model_validate(data)
    except ValidationError:
        raise HTTPException(
            status_code=503,
            detail="Invalid product service response",
        ) from None

    if product.id != product_id:
        raise HTTPException(
            status_code=503,
            detail="Product service returned the wrong product",
        )

    return product