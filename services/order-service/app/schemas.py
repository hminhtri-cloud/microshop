from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator


class OrderItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(gt=0, strict=True)
    quantity: int = Field(ge=1, le=99, strict=True)


class ShippingInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    receiver_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=9, max_length=15)
    address: str = Field(min_length=10, max_length=500)
    note: str | None = Field(default=None, max_length=500)


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[OrderItemRequest] = Field(min_length=1, max_length=50)
    shipping: ShippingInfo

    @model_validator(mode="after")
    def reject_duplicate_products(self):
        product_ids = [item.product_id for item in self.items]

        if len(product_ids) != len(set(product_ids)):
            raise ValueError(
                "Each product may appear only once in an order"
            )

        return self


class MockPayment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: Literal["success", "failure"]


class SellerStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["confirmed", "shipping", "completed"]


class ItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    product_name_snapshot: str
    unit_price_snapshot: Decimal
    quantity: int
    subtotal: Decimal


class SellerOrderResponse(BaseModel):
    id: int
    order_id: int
    seller_id: int
    status: str
    subtotal: Decimal
    items: list[ItemResponse]


class OrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    total_amount: Decimal
    payment_status: str
    status: str
    created_at: datetime
    error_code: str | None = None

    @field_serializer("created_at")
    def utc_timestamp(self, value: datetime):
        return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


class OrderDetail(OrderSummary):
    shipping: ShippingInfo
    seller_orders: list[SellerOrderResponse]


class SellerOrderDetail(SellerOrderResponse):
    payment_status: str
    order_status: str
    shipping: ShippingInfo


class OrderPage(BaseModel):
    items: list[OrderSummary]
    total: int
    offset: int
    limit: int


class SellerOrderPage(BaseModel):
    items: list[SellerOrderDetail]
    total: int
    offset: int
    limit: int
