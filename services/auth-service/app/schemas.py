from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

class UserRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(
        min_length=3,
        max_length=50
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=72
    )

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return value


class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class SellerApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    shop_name: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=10, max_length=1000)


class SellerReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    action: Literal["approve", "reject", "suspend"]
    note: str = Field(min_length=3, max_length=500)


class SellerApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    shop_name: str
    description: str
    status: Literal["pending", "approved", "rejected", "suspended"]
    review_note: str | None
    reviewed_by: int | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SellerApplicationPage(BaseModel):
    items: list[SellerApplicationResponse]
    total: int
    offset: int
    limit: int
