from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.auth import Identity, require_role
from app.database import get_db
from app.models import Product
from app.schemas import ProductCreate, ProductPage, ProductResponse, ProductUpdate, VisibilityUpdate, ModerationUpdate

router = APIRouter(tags=["products"])


def product_page(db: Session, filters: list, offset: int, limit: int):
    where = tuple(filters)
    total = db.scalar(select(func.count()).select_from(Product).where(*where)) or 0
    items = db.scalars(select(Product).where(*where).order_by(Product.id.desc()).offset(offset).limit(limit)).all()
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get("/products", response_model=ProductPage)
def list_products(
    category: str | None = Query(None, max_length=60),
    search: str | None = Query(None, max_length=120),
    seller_id: int | None = Query(None, gt=0),
    offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    filters = [Product.status == "active"]
    if category:
        filters.append(Product.category == category)
    if search and search.strip():
        # Escape wildcard characters so search treats text literally.
        escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(Product.name.ilike(f"%{escaped}%", escape="\\"))
    if seller_id:
        filters.append(Product.seller_id == seller_id)
    return product_page(db, filters, offset, limit)


@router.get("/products/{product_id}", response_model=ProductResponse)
def product_detail(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None or product.status != "active":
        raise HTTPException(404, "Product not found")
    return product


@router.get("/seller/products", response_model=ProductPage)
def my_products(
    offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    seller: Identity = Depends(require_role("seller")), db: Session = Depends(get_db),
):
    return product_page(db, [Product.seller_id == seller.id], offset, limit)


@router.post("/seller/products", response_model=ProductResponse, status_code=201)
def create_product(data: ProductCreate, seller: Identity = Depends(require_role("seller")), db: Session = Depends(get_db)):
    product = Product(**data.model_dump(mode="json"), seller_id=seller.id)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/seller/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, data: ProductUpdate, seller: Identity = Depends(require_role("seller")), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product or product.seller_id != seller.id:
        raise HTTPException(404, "Product not found")
    if product.status == "blocked":
        raise HTTPException(409, "Product is blocked by an administrator")
    for key, value in data.model_dump(mode="json").items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/seller/products/{product_id}/visibility", response_model=ProductResponse)
def seller_visibility(product_id: int, data: VisibilityUpdate, seller: Identity = Depends(require_role("seller")), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product or product.seller_id != seller.id:
        raise HTTPException(404, "Product not found")
    if product.status == "blocked":
        raise HTTPException(409, "Product is blocked by an administrator")
    product.status = data.status
    db.commit()
    db.refresh(product)
    return product


@router.get("/admin/products", response_model=ProductPage)
def all_products(
    offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    admin: Identity = Depends(require_role("admin")), db: Session = Depends(get_db),
):
    return product_page(db, [], offset, limit)


@router.patch("/admin/products/{product_id}/visibility", response_model=ProductResponse)
def admin_visibility(product_id: int, data: ModerationUpdate, admin: Identity = Depends(require_role("admin")), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    product.status = data.status
    db.commit()
    db.refresh(product)
    return product
