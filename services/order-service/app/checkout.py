"""Durable checkout saga. Local row locks serialize worker, retries and payment.

An intent is committed BEFORE reserving inventory. On timeout/crash, the same
intent/key is replayed, never compensated blindly after an ambiguous DB commit.
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app import stock_client
from app.database import SessionLocal
from app.models import Order, OrderItem, SellerOrder
from app.schemas import OrderCreate


logger = logging.getLogger(__name__)
IN_FLIGHT = ("creating", "confirming", "cancelling", "failing")
UNPAID_TTL = timedelta(minutes=30)


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def expired(order: Order):
    return order.payment_status == "unpaid" and order.created_at + UNPAID_TTL <= utc_now()


def conflict(code: str, message: str):
    raise HTTPException(409, {"code": code, "message": message})


def order_for_update(db: Session, order_id: int, customer_id: int | None = None):
    query = select(Order).where(Order.id == order_id)
    if customer_id is not None:
        query = query.where(Order.customer_id == customer_id)
    order = db.scalar(query.with_for_update())
    if order is None:
        raise HTTPException(404, {"code": "ORDER_NOT_FOUND", "message": "Order not found"})
    return order


def create_intent(db: Session, data: OrderCreate, customer_id: int, key: str):
    body = data.model_dump(mode="json")
    body["items"].sort(key=lambda item: item["product_id"])
    fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    order = Order(customer_id=customer_id, request_key=key, request_fingerprint=fingerprint,
                  request_body=body, **data.shipping.model_dump())
    db.add(order)
    try:
        db.commit()
        return order.id, True
    except IntegrityError:
        db.rollback()
        order = db.scalar(select(Order).where(Order.customer_id == customer_id, Order.request_key == key))
        if order is None:
            raise HTTPException(503, "Retry checkout with the same key") from None
        if order.request_fingerprint != fingerprint:
            conflict("IDEMPOTENCY_CONFLICT", "Key was used for a different order")
        return order.id, False


def advance(db: Session, order_id: int):
    # End any prior read snapshot before obtaining the current locked state.
    db.rollback()
    order = order_for_update(db, order_id)
    if order.status == "pending" and expired(order):
        order.status = "cancelling"
        db.commit()
        order = order_for_update(db, order_id)
    if order.status == "creating":
        try:
            receipt = stock_client.reserve(order.customer_id, order.request_key, order.request_body["items"])
        except HTTPException as error:
            if error.status_code == 409:
                order.status = "rejected"
                order.error_code = error.detail.get("code", "PRODUCT_UNAVAILABLE") if isinstance(error.detail, dict) else "PRODUCT_UNAVAILABLE"
                db.commit()
            raise

        groups: dict[int, list] = {}
        for item in receipt.items:
            groups.setdefault(item.seller_id, []).append(item)
        total = 0
        for seller_id, items in groups.items():
            subtotal = sum(item.price * item.quantity for item in items)
            seller_order = SellerOrder(order_id=order.id, seller_id=seller_id, subtotal=subtotal)
            db.add(seller_order)
            db.flush()
            for item in items:
                db.add(OrderItem(seller_order_id=seller_order.id, product_id=item.product_id,
                                 product_name_snapshot=item.name, unit_price_snapshot=item.price,
                                 quantity=item.quantity, subtotal=item.price * item.quantity))
            total += subtotal
        order.total_amount = total
        order.status = "pending"
    elif order.status in ("confirming", "cancelling", "failing"):
        target = order.status
        stock_client.finalize(order.customer_id, order.request_key,
                              "confirm" if target == "confirming" else "release")
        if target == "confirming":
            order.payment_status = "paid"
            order.status = "pending"
        else:
            order.payment_status = "cancelled" if target == "cancelling" else "failed"
            order.status = "cancelled"
            for part in db.scalars(select(SellerOrder).where(SellerOrder.order_id == order.id)):
                part.status = "cancelled"
    db.commit()


def request_action(db: Session, order_id: int, customer_id: int, action: str):
    order = order_for_update(db, order_id, customer_id)
    target = {"success": "confirming", "failure": "failing", "cancel": "cancelling"}[action]
    terminal = {"success": "paid", "failure": "failed", "cancel": "cancelled"}[action]
    if order.payment_status == terminal:
        db.rollback()
        return
    if order.payment_status != "unpaid" or order.status not in ("pending", target):
        conflict("INVALID_STATUS_TRANSITION", "Order cannot perform this action")
    if target == "confirming" and order.status == "pending" and expired(order):
        order.status = "cancelling"
        db.commit()
        advance(db, order_id)
        conflict("RESERVATION_EXPIRED", "Unpaid order expired after 30 minutes")
    order.status = target
    db.commit()  # Persist recovery instruction before touching Product Service.
    advance(db, order_id)


def reconcile_once():
    with SessionLocal() as db:
        ids = db.scalars(select(Order.id).where(or_(
            Order.status.in_(IN_FLIGHT),
            and_(Order.status == "pending", Order.payment_status == "unpaid",
                 Order.created_at <= utc_now() - UNPAID_TTL),
        )).order_by(Order.id)).all()
    for order_id in ids:
        with SessionLocal() as db:
            try:
                advance(db, order_id)
            except (HTTPException, SQLAlchemyError):
                db.rollback()
                # No payloads, tokens, shipping data or SQL parameters in logs.
                logger.warning("Order reconciliation deferred: order_id=%s", order_id)


def order_page(db: Session, filters: list, offset: int, limit: int):
    return {"items": db.scalars(select(Order).where(*filters).order_by(Order.id.desc())
                               .offset(offset).limit(limit)).all(),
            "total": db.scalar(select(func.count()).select_from(Order).where(*filters)) or 0,
            "offset": offset, "limit": limit}


def part_detail(db: Session, part: SellerOrder):
    return {"id": part.id, "order_id": part.order_id, "seller_id": part.seller_id,
            "subtotal": part.subtotal, "status": part.status,
            "items": db.scalars(select(OrderItem).where(OrderItem.seller_order_id == part.id).order_by(OrderItem.id)).all()}


def detail(db: Session, order_id: int):
    order = db.get(Order, order_id)
    return {"id": order.id, "customer_id": order.customer_id, "total_amount": order.total_amount,
            "status": order.status, "payment_status": order.payment_status, "created_at": order.created_at,
            "error_code": order.error_code,
            "shipping": {key: getattr(order, key) for key in ("receiver_name", "phone", "address", "note")},
            "seller_orders": [part_detail(db, part) for part in db.scalars(
                select(SellerOrder).where(SellerOrder.order_id == order.id).order_by(SellerOrder.id))]}


def seller_detail(db: Session, part: SellerOrder):
    order = db.get(Order, part.order_id)
    return {**part_detail(db, part), "payment_status": order.payment_status, "order_status": order.status,
            "shipping": {key: getattr(order, key) for key in ("receiver_name", "phone", "address", "note")}}
