
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Inventory
from app.schemas import InventoryRequest

router = APIRouter(
    prefix="/api/inventory",
    tags=["Inventory"]
)


# 1. Get stock
@router.get("/{productId}")
def get_inventory(productId: int, db: Session = Depends(get_db)):

    inventory = db.query(Inventory).filter(
        Inventory.product_id == productId
    ).first()

    if not inventory:
        raise HTTPException(404, "Product inventory not found")

    return {
        "productId": productId,
        "stock": inventory.quantity_available
    }


# 2. Check availability
@router.post("/check")
def check_inventory(data: InventoryRequest, db: Session = Depends(get_db)):

    for item in data.items:
        inventory = db.query(Inventory).filter(
            Inventory.product_id == item.productId
        ).first()

        if not inventory or inventory.quantity_available < item.quantity:
            return {"available": False}

    return {"available": True}


# 3. Reserve stock
@router.post("/reserve")
def reserve_inventory(data: InventoryRequest, db: Session = Depends(get_db)):

    try:
        for item in data.items:
            inventory = db.query(Inventory).filter(
                Inventory.product_id == item.productId
            ).with_for_update().first()

            if not inventory:
                raise HTTPException(404, f"Product {item.productId} not found")

            if inventory.quantity_available < item.quantity:
                raise HTTPException(400, "Insufficient stock")

        for item in data.items:
            inventory = db.query(Inventory).filter(
                Inventory.product_id == item.productId
            ).with_for_update().first()

            inventory.quantity_available -= item.quantity
            inventory.quantity_reserved += item.quantity

        db.commit()

        return {"success": True, "message": "Stock reserved successfully"}

    except Exception:
        db.rollback()
        raise


# 4. Release stock
@router.post("/release")
def release_inventory(data: InventoryRequest, db: Session = Depends(get_db)):

    try:
        inventories = []

        for item in data.items:
            inventory = db.query(Inventory).filter(
                Inventory.product_id == item.productId
            ).with_for_update().first()

            if not inventory:
                raise HTTPException(404, f"Product {item.productId} not found")

            if inventory.quantity_reserved < item.quantity:
                raise HTTPException(400, "Not enough reserved stock")

            inventories.append((inventory, item.quantity))

        for inventory, quantity in inventories:
            inventory.quantity_reserved -= quantity
            inventory.quantity_available += quantity

        db.commit()

        return {"success": True, "message": "Stock released successfully"}

    except Exception:
        db.rollback()
        raise
