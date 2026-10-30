from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Product


def reserve_one_product(
    db: Session,
    product_id: int,
    requested_quantity: int,
) -> None:
    if product_id <= 0:
        raise ValueError("product_id must be positive")

    if requested_quantity <= 0:
        raise ValueError("requested_quantity must be positive")

    statement = (
        update(Product)
        .where(
            Product.id == product_id,
            Product.status == "active",
            Product.quantity >= requested_quantity,
        )
        .values(
            quantity=Product.quantity - requested_quantity,
        )
    )

    result = db.execute(statement)

    if result.rowcount != 1:
        raise HTTPException(
            status_code=409,
            detail=f"Product {product_id} is unavailable or out of stock",
        )

    # Cố ý KHÔNG db.commit() ở đây.