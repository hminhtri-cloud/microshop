"""Internal, atomic batch inventory operations. Never publish through a gateway."""
import hashlib
import json
import os
import secrets
from decimal import Decimal
from http.client import HTTPException as HTTPClientError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.inventory import reserve_one_product
from app.models import Product
from app.reservation_models import InventoryReservation, InventoryReservationItem


def fail(code: str, message: str):
    raise HTTPException(409, {"code": code, "message": message})


def require_internal(x_service_token: str = Header(default="")):
    expected = os.getenv("INTERNAL_SERVICE_TOKEN", "")
    if not expected:
        raise HTTPException(503, "Internal authentication is not configured")
    if not secrets.compare_digest(x_service_token, expected):
        raise HTTPException(403, "Service authentication required")


class StockItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: int = Field(gt=0, strict=True)
    quantity: int = Field(ge=1, le=99, strict=True)


class ReservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    buyer_id: int = Field(gt=0, strict=True)
    request_key: str = Field(min_length=1, max_length=64)
    items: list[StockItem] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def unique_items(self):
        if len({item.product_id for item in self.items}) != len(self.items):
            raise ValueError("Duplicate product IDs")
        return self


def check_sellers(seller_ids: list[int]):
    token = os.getenv("INTERNAL_SERVICE_TOKEN", "")
    if not token:
        raise HTTPException(503, "Internal authentication is not configured")
    url = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000").rstrip("/")
    request = Request(url + "/internal/sellers/eligibility",
                      data=json.dumps({"seller_ids": seller_ids}).encode(),
                      headers={"Content-Type": "application/json", "X-Service-Token": token})
    try:
        with urlopen(request, timeout=3) as response:
            result = json.load(response)
        if not isinstance(result, dict) or type(result.get("eligible")) is not bool:
            raise ValueError("Invalid eligibility response")
    except (OSError, HTTPClientError, ValueError):
        raise HTTPException(503, "Seller verification unavailable") from None
    if not result["eligible"]:
        fail("SELLER_NOT_APPROVED", "A seller is no longer approved")


def receipt(db: Session, reservation: InventoryReservation):
    items = db.scalars(select(InventoryReservationItem).where(
        InventoryReservationItem.reservation_id == reservation.id
    ).order_by(InventoryReservationItem.product_id)).all()
    return {"id": reservation.id, "status": reservation.status, "items": [
        {"product_id": item.product_id, "quantity": item.quantity,
         "name": item.product_name_snapshot, "seller_id": item.seller_id_snapshot,
         "price": format(item.unit_price_snapshot, ".2f")} for item in items
    ]}


def find_reservation(db: Session, buyer_id: int, key: str):
    return db.scalar(select(InventoryReservation).where(
        InventoryReservation.buyer_id == buyer_id,
        InventoryReservation.request_key == key,
    ).with_for_update())


def reserve_batch(db: Session, data: ReservationRequest):
    items = sorted(data.items, key=lambda item: item.product_id)
    fingerprint = hashlib.sha256(json.dumps([
        item.model_dump() for item in items
    ], sort_keys=True).encode()).hexdigest()
    try:
        # Claim key BEFORE changing stock; unique constraint serializes duplicate requests.
        reservation = InventoryReservation(buyer_id=data.buyer_id, request_key=data.request_key,
                                           request_fingerprint=fingerprint)
        db.add(reservation)
        db.flush()
    except IntegrityError:
        db.rollback()
        reservation = find_reservation(db, data.buyer_id, data.request_key)
        if reservation is None:
            raise HTTPException(503, "Retry reservation with the same key") from None
        if reservation.request_fingerprint != fingerprint:
            fail("IDEMPOTENCY_CONFLICT", "Reservation key was used for different items")
        return receipt(db, reservation)

    products = []
    for item in items:
        product = db.scalar(select(Product).where(Product.id == item.product_id).with_for_update())
        if product is None or product.status != "active":
            fail("PRODUCT_UNAVAILABLE", "A product is no longer available")
        if product.quantity < item.quantity:
            fail("INSUFFICIENT_STOCK", "A product has insufficient stock")
        products.append(product)

    check_sellers(sorted({product.seller_id for product in products}))
    total = sum((product.price * item.quantity for product, item in zip(products, items)), Decimal("0"))
    if total > Decimal("999999999999.99"):
        fail("AMOUNT_EXCEEDED", "Order total exceeds supported amount")

    for product, item in zip(products, items):
        reserve_one_product(db, product.id, item.quantity)
        db.add(InventoryReservationItem(
            reservation_id=reservation.id, product_id=product.id, quantity=item.quantity,
            product_name_snapshot=product.name, seller_id_snapshot=product.seller_id,
            unit_price_snapshot=product.price,
        ))
    db.commit()
    return receipt(db, reservation)


def transition(db: Session, buyer_id: int, key: str, target: str):
    reservation = find_reservation(db, buyer_id, key)
    if reservation is None:
        raise HTTPException(404, "Reservation not found")
    if reservation.status == target:
        return receipt(db, reservation)
    if reservation.status != "reserved":
        fail("INVALID_STATUS_TRANSITION", "Reservation already finalized")
    if target == "released":
        items = db.scalars(select(InventoryReservationItem).where(
            InventoryReservationItem.reservation_id == reservation.id
        ).order_by(InventoryReservationItem.product_id)).all()
        for item in items:
            product = db.scalar(select(Product).where(Product.id == item.product_id).with_for_update())
            if product is None:
                raise HTTPException(503, "Reserved product missing")
            product.quantity += item.quantity
    reservation.status = target
    db.commit()
    return receipt(db, reservation)


router = APIRouter(prefix="/internal/stock", dependencies=[Depends(require_internal)])


@router.post("/reservations")
def reserve(data: ReservationRequest, db: Session = Depends(get_db)):
    try:
        return reserve_batch(db, data)
    except Exception:
        db.rollback()
        raise


@router.post("/reservations/{buyer_id}/{key}/confirm")
def confirm(buyer_id: int, key: str, db: Session = Depends(get_db)):
    return transition(db, buyer_id, key, "confirmed")


@router.post("/reservations/{buyer_id}/{key}/release")
def release(buyer_id: int, key: str, db: Session = Depends(get_db)):
    return transition(db, buyer_id, key, "released")
