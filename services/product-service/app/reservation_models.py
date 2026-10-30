from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"

    id: Mapped[int] = mapped_column(primary_key=True)

    # ID đã được Auth Service xác thực, không lấy tùy ý từ browser.
    buyer_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Một mã riêng cho một lần khách đặt hàng.
    request_key: Mapped[str] = mapped_column(String(64), nullable=False)

    # Dấu vân tay của danh sách product_id + quantity.
    # Giúp phát hiện cùng key nhưng gửi nội dung khác.
    request_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )

    # reserved / confirmed / released
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="reserved"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "buyer_id",
            "request_key",
            name="uq_inventory_reservation_buyer_request",
        ),
    )


class InventoryReservationItem(Base):
    __tablename__ = "inventory_reservation_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    reservation_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_reservations.id"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Chụp lại dữ liệu lúc giữ kho để khi retry trả cùng kết quả.
    product_name_snapshot: Mapped[str] = mapped_column(
        String(120), nullable=False
    )
    seller_id_snapshot: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    unit_price_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "reservation_id",
            "product_id",
            name="uq_reservation_product",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_reservation_item_quantity_positive",
        ),
    )