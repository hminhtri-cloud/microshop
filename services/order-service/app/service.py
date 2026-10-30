from dataclasses import dataclass
from decimal import Decimal

from fastapi import HTTPException

from app.auth import Identity
from app.products_client import ProductSnapshot, fetch_product
from app.schemas import OrderCreate


MAX_AMOUNT = Decimal("999999999999.99")


@dataclass(frozen=True)
class QuotedItem:
    product_id: int
    product_name: str
    seller_id: int
    unit_price: Decimal
    quantity: int
    subtotal: Decimal


@dataclass(frozen=True)
class QuotedSellerOrder:
    seller_id: int
    items: tuple[QuotedItem, ...]
    subtotal: Decimal


@dataclass(frozen=True)
class OrderQuote:
    customer_id: int
    seller_orders: tuple[QuotedSellerOrder, ...]
    total_amount: Decimal


def quote_item(product: ProductSnapshot, quantity: int) -> QuotedItem:
    if product.quantity < quantity:
        raise HTTPException(
            status_code=409,
            detail=f"Product {product.id} has insufficient stock",
        )

    subtotal = product.price * quantity

    if subtotal > MAX_AMOUNT:
        raise HTTPException(
            status_code=422,
            detail="Item subtotal exceeds supported amount",
        )

    return QuotedItem(
        product_id=product.id,
        product_name=product.name,
        seller_id=product.seller_id,
        unit_price=product.price,
        quantity=quantity,
        subtotal=subtotal,
    )


def build_order_quote(data: OrderCreate, buyer: Identity) -> OrderQuote:
    if buyer.role not in ("customer", "seller"):
        raise HTTPException(
            status_code=403,
            detail="Buyer permission required",
        )

    # key = seller_id; value = các sản phẩm khách mua từ seller đó
    items_by_seller: dict[int, list[QuotedItem]] = {}

    for requested_item in data.items:
        # Đọc dữ liệu thật từ Product Service, không đọc giá từ browser.
        product = fetch_product(requested_item.product_id)

        quoted_item = quote_item(
            product=product,
            quantity=requested_item.quantity,
        )

        items_by_seller.setdefault(
            product.seller_id, []
        ).append(quoted_item)

    seller_orders: list[QuotedSellerOrder] = []

    for seller_id, items in items_by_seller.items():
        subtotal = sum(
            (item.subtotal for item in items),
            Decimal("0.00"),
        )

        if subtotal > MAX_AMOUNT:
            raise HTTPException(
                status_code=422,
                detail="Seller subtotal exceeds supported amount",
            )

        seller_orders.append(
            QuotedSellerOrder(
                seller_id=seller_id,
                items=tuple(items),
                subtotal=subtotal,
            )
        )

    total_amount = sum(
        (group.subtotal for group in seller_orders),
        Decimal("0.00"),
    )

    if total_amount > MAX_AMOUNT:
        raise HTTPException(
            status_code=422,
            detail="Order total exceeds supported amount",
        )

    return OrderQuote(
        customer_id=buyer.id,
        seller_orders=tuple(seller_orders),
        total_amount=total_amount,
    )