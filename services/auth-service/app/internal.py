import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SellerApplication, User


def require_internal(x_service_token: str = Header(default="")):
    expected = os.getenv("INTERNAL_SERVICE_TOKEN", "")
    if not expected:
        raise HTTPException(503, "Internal authentication is not configured")
    if not secrets.compare_digest(x_service_token, expected):
        raise HTTPException(403, "Service authentication required")


class SellerEligibilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seller_ids: list[int] = Field(min_length=1, max_length=50)


router = APIRouter(prefix="/internal", dependencies=[Depends(require_internal)])


@router.post("/sellers/eligibility")
def eligibility(data: SellerEligibilityRequest, db: Session = Depends(get_db)):
    approved = set(db.scalars(
        select(User.id).join(SellerApplication, SellerApplication.user_id == User.id)
        .where(User.id.in_(data.seller_ids), User.role == "seller", SellerApplication.status == "approved")
    ).all())
    return {"eligible": all(seller_id in approved for seller_id in data.seller_ids)}
