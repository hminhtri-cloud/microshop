from pydantic import BaseModel, ConfigDict, Field, model_validator


class OrderItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=99)


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