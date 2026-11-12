from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import checkout
from app.auth import Identity, require_buyer, require_role
from app.database import get_db
from app.models import Order, SellerOrder
from app.schemas import (MockPayment, OrderCreate, OrderDetail, OrderPage,
                         SellerOrderDetail, SellerOrderPage, SellerStatusUpdate)

router = APIRouter()


def request_key(idempotency_key: str = Header()):
    try:
        value = UUID(idempotency_key)
        if value.version != 4:
            raise ValueError()
        return str(value)
    except ValueError:
        raise HTTPException(422, "Idempotency-Key must be a UUID v4") from None


@router.post("/orders", response_model=OrderDetail, status_code=201)
def create_order(data: OrderCreate, response: Response, key: str = Depends(request_key),
                 buyer: Identity = Depends(require_buyer), db: Session = Depends(get_db)):
    order_id, created = checkout.create_intent(db, data, buyer.id, key)
    checkout.advance(db, order_id)
    order = db.get(Order, order_id)
    if order.status == "rejected":
        checkout.conflict(order.error_code or "PRODUCT_UNAVAILABLE", "Checkout was rejected; use a new key after correcting the cart")
    response.status_code = 201 if created else 200
    return checkout.detail(db, order_id)


@router.get("/orders", response_model=OrderPage)
def my_orders(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
              buyer: Identity = Depends(require_buyer), db: Session = Depends(get_db)):
    return checkout.order_page(db, [Order.customer_id == buyer.id], offset, limit)


@router.get("/orders/{order_id}", response_model=OrderDetail)
def get_order(order_id: int, buyer: Identity = Depends(require_buyer), db: Session = Depends(get_db)):
    checkout.order_for_update(db, order_id, buyer.id)
    return checkout.detail(db, order_id)


@router.post("/orders/{order_id}/cancel", response_model=OrderDetail)
def cancel_order(order_id: int, buyer: Identity = Depends(require_buyer), db: Session = Depends(get_db)):
    checkout.request_action(db, order_id, buyer.id, "cancel")
    return checkout.detail(db, order_id)


@router.post("/orders/{order_id}/mock-payment", response_model=OrderDetail)
def mock_payment(order_id: int, data: MockPayment, buyer: Identity = Depends(require_buyer),
                 db: Session = Depends(get_db)):
    checkout.request_action(db, order_id, buyer.id, data.outcome)
    return checkout.detail(db, order_id)


def find_part(db: Session, part_id: int, seller_id: int):
    part = db.scalar(select(SellerOrder).where(SellerOrder.id == part_id, SellerOrder.seller_id == seller_id))
    if part is None:
        raise HTTPException(404, "Seller order not found")
    return part


@router.get("/seller/orders", response_model=SellerOrderPage)
def seller_orders(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
                  seller: Identity = Depends(require_role("seller")), db: Session = Depends(get_db)):
    filters = [SellerOrder.seller_id == seller.id]
    parts = db.scalars(select(SellerOrder).where(*filters).order_by(SellerOrder.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [checkout.seller_detail(db, part) for part in parts],
            "total": db.scalar(select(func.count()).select_from(SellerOrder).where(*filters)) or 0,
            "offset": offset, "limit": limit}


@router.get("/seller/orders/{part_id}", response_model=SellerOrderDetail)
def get_seller_order(part_id: int, seller: Identity = Depends(require_role("seller")), db: Session = Depends(get_db)):
    return checkout.seller_detail(db, find_part(db, part_id, seller.id))


@router.patch("/seller/orders/{part_id}/status", response_model=SellerOrderDetail)
def update_seller_order(part_id: int, data: SellerStatusUpdate,
                        seller: Identity = Depends(require_role("seller")), db: Session = Depends(get_db)):
    order_id = find_part(db, part_id, seller.id).order_id
    db.rollback()
    # Same lock ordering as checkout/payment and other sellers of this order.
    order = checkout.order_for_update(db, order_id)
    part = find_part(db, part_id, seller.id)
    if order.payment_status != "paid":
        checkout.conflict("INVALID_STATUS_TRANSITION", "Payment is required before fulfillment")
    if part.status != data.status:
        next_status = {"pending": "confirmed", "confirmed": "shipping", "shipping": "completed"}
        if next_status.get(part.status) != data.status:
            checkout.conflict("INVALID_STATUS_TRANSITION", "Invalid seller order transition")
        part.status = data.status
        db.flush()
        statuses = db.scalars(select(SellerOrder.status).where(SellerOrder.order_id == order_id)).all()
        if all(status == "completed" for status in statuses):
            order.status = "completed"
        elif any(status in ("shipping", "completed") for status in statuses):
            order.status = "shipping"
        elif all(status == "confirmed" for status in statuses):
            order.status = "confirmed"
        db.commit()
    return checkout.seller_detail(db, part)


@router.get("/admin/orders", response_model=OrderPage)
def admin_orders(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
                 admin: Identity = Depends(require_role("admin")), db: Session = Depends(get_db)):
    return checkout.order_page(db, [], offset, limit)


@router.get("/admin/orders/{order_id}", response_model=OrderDetail)
def admin_order(order_id: int, admin: Identity = Depends(require_role("admin")), db: Session = Depends(get_db)):
    checkout.order_for_update(db, order_id)
    return checkout.detail(db, order_id)
