from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import SellerApplication, User
from app.schemas import (
    SellerApplicationCreate,
    SellerApplicationPage,
    SellerApplicationResponse,
    SellerReview,
)

router = APIRouter(tags=["sellers"])


@router.post("/seller/application", response_model=SellerApplicationResponse, status_code=201)
def submit_application(
    data: SellerApplicationCreate,
    user: User = Depends(require_roles("customer")),
    db: Session = Depends(get_db),
):
    # Serialize applications for the same account (including first submission).
    db.query(User).filter(User.id == user.id).with_for_update().one()
    application = (
        db.query(SellerApplication)
        .filter(SellerApplication.user_id == user.id)
        .with_for_update()
        .first()
    )
    if application and application.status != "rejected":
        raise HTTPException(status_code=409, detail="An application already exists; contact admin if suspended")
    if application is None:
        application = SellerApplication(user_id=user.id)
        db.add(application)
    application.shop_name = data.shop_name
    application.description = data.description
    application.status = "pending"
    application.review_note = None
    application.reviewed_by = None
    application.reviewed_at = None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An application already exists") from None
    db.refresh(application)
    return application


@router.get("/seller/application", response_model=SellerApplicationResponse)
def my_application(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    application = db.query(SellerApplication).filter(SellerApplication.user_id == user.id).first()
    if application is None:
        raise HTTPException(status_code=404, detail="Seller application not found")
    return application


@router.get("/seller/profile", response_model=SellerApplicationResponse)
def seller_profile(
    user: User = Depends(require_roles("seller")), db: Session = Depends(get_db)
):
    application = db.query(SellerApplication).filter(
        SellerApplication.user_id == user.id, SellerApplication.status == "approved"
    ).first()
    if application is None:
        raise HTTPException(status_code=403, detail="An approved seller application is required")
    return application


@router.get("/admin/seller-applications", response_model=SellerApplicationPage, tags=["admin"])
def list_applications(
    status: Literal["pending", "approved", "rejected", "suspended"] | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    query = db.query(SellerApplication)
    if status is not None:
        query = query.filter(SellerApplication.status == status)
    total = query.count()
    items = query.order_by(SellerApplication.id).offset(offset).limit(limit).all()
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.post(
    "/admin/seller-applications/{application_id}/review",
    response_model=SellerApplicationResponse,
    tags=["admin"],
)
def review_application(
    application_id: int,
    data: SellerReview,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    # Lock in the same order as submission: owner user, then application.
    owner_id = db.query(SellerApplication.user_id).filter(SellerApplication.id == application_id).scalar()
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Seller application not found")
    owner = db.query(User).filter(User.id == owner_id).with_for_update().populate_existing().one()
    application = (
        db.query(SellerApplication).filter(SellerApplication.id == application_id)
        .with_for_update().populate_existing().one()
    )
    if owner.role == "admin":
        raise HTTPException(status_code=409, detail="Cannot change an admin account through seller review")
    transitions = {
        "approve": ({"pending", "suspended"}, "approved", "seller"),
        "reject": ({"pending"}, "rejected", "customer"),
        "suspend": ({"approved"}, "suspended", "customer"),
    }
    allowed, new_status, new_role = transitions[data.action]
    if application.status not in allowed:
        raise HTTPException(status_code=409, detail="Invalid seller status transition")
    application.status = new_status
    application.review_note = data.note
    application.reviewed_by = admin.id
    application.reviewed_at = datetime.now(timezone.utc)
    owner.role = new_role
    # Profile status and account permission change in the same DB transaction.
    db.commit()
    db.refresh(application)
    return application
