from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, JSON, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    # ID do Auth Service quản lý
    customer_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    request_key: Mapped[str] = mapped_column(String(64), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    request_body: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Durable intent exists before making any inventory request.
    error_code: Mapped[str | None] = mapped_column(String(64))

    receiver_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(15), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )

    # Chưa thanh toán thật; sau này dùng cho thanh toán mô phỏng
    payment_status: Mapped[str] = mapped_column(
        String(20), default="unpaid", nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), default="creating", nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("customer_id", "request_key", name="uq_order_customer_request"),
        CheckConstraint("total_amount >= 0", name="ck_orders_total_nonnegative"),
    )


class SellerOrder(Base):
    __tablename__ = "seller_orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Liên kết với đơn tổng trong chính order_db
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), index=True, nullable=False
    )

    # ID do Auth Service quản lý
    seller_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )

    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="ck_seller_orders_subtotal_nonnegative"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    seller_order_id: Mapped[int] = mapped_column(
        ForeignKey("seller_orders.id"), index=True, nullable=False
    )

    # ID do Product Service quản lý
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Dữ liệu được CHỤP LẠI tại thời điểm đặt hàng
    product_name_snapshot: Mapped[str] = mapped_column(
        String(120), nullable=False
    )

    unit_price_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price_snapshot >= 0", name="ck_order_items_price_nonnegative"),
        CheckConstraint("subtotal >= 0", name="ck_order_items_subtotal_nonnegative"),
    )
