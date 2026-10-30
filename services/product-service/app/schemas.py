from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class ProductFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=2000)
    category: str = Field(min_length=2, max_length=60)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    quantity: int = Field(ge=0)
    image_url: HttpUrl | None = Field(default=None, max_length=500)

    @field_validator("price", mode="before")
    @classmethod
    def disallow_float_price(cls, value):
        if isinstance(value, float):
            raise ValueError("Send price as a decimal string, e.g. '120000.00'")
        return value


class ProductCreate(ProductFields):
    pass


class ProductUpdate(ProductFields):
    pass


class VisibilityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["active", "hidden"]


class ModerationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["active", "blocked"]


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seller_id: int
    name: str
    description: str
    category: str
    price: Decimal
    quantity: int
    image_url: str | None
    status: Literal["active", "hidden", "blocked"]
    created_at: datetime
    updated_at: datetime


class ProductPage(BaseModel):
    items: list[ProductResponse]
    total: int
    offset: int
    limit: int
