from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import uuid4
from datetime import datetime, timezone

from .database import Base, engine, get_db
from .models import (
    Shipment,
    ShipmentCreate,
    ShipmentStatusUpdate,
    ShipmentResponse
)

# Création de la base de données
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Shipping Microservice",
    description="Microservice de gestion et de suivi des expéditions",
    version="1.0.0"
)

# Configuration CORS pour React / Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Transitions autorisées
TRANSITIONS = {
    "PREPARING": ["SHIPPED", "CANCELLED"],
    "SHIPPED": ["IN_TRANSIT"],
    "IN_TRANSIT": ["DELIVERED"],
    "DELIVERED": [],
    "CANCELLED": []
}


# Gestion des erreurs au format attendu par apiClient.js
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": str(exc.detail)}
    )


# Vérifier le fonctionnement du service
@app.get("/")
def home():
    return {
        "service": "Shipping",
        "status": "running"
    }


# 1. GET : récupérer toutes les expéditions
@app.get("/api/shipments", response_model=list[ShipmentResponse])
def get_shipments(db: Session = Depends(get_db)):
    return db.query(Shipment).all()


# 2. GET : récupérer une expédition par commande
@app.get("/api/shipments/order/{orderId}", response_model=ShipmentResponse)
def get_shipment_by_order(
    orderId: str,
    db: Session = Depends(get_db)
):
    shipment = db.query(Shipment).filter(
        Shipment.orderId == orderId
    ).first()

    if not shipment:
        raise HTTPException(
            status_code=404,
            detail="Shipment not found"
        )

    return shipment


# 3. POST : créer une expédition
@app.post("/api/shipments", status_code=201, response_model=ShipmentResponse)
def create_shipment(
    data: ShipmentCreate,
    db: Session = Depends(get_db)
):
    existing = db.query(Shipment).filter(
        Shipment.orderId == data.orderId
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Shipment already exists for this order"
        )

    shipment = Shipment(
        id=str(uuid4()),
        orderId=data.orderId,
        name=data.address.name,
        address=data.address.address,
        city=data.address.city,
        trackingNumber=f"MSOA-{uuid4().hex[:8].upper()}",
        status="PREPARING"
    )

    try:
        db.add(shipment)
        db.commit()
        db.refresh(shipment)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Shipment already exists for this order"
        )

    return shipment


# 4. PATCH : modifier le statut d'une expédition
@app.patch("/api/shipments/{id}/status", response_model=ShipmentResponse)
def update_shipment_status(
    id: str,
    data: ShipmentStatusUpdate,
    db: Session = Depends(get_db)
):
    shipment = db.query(Shipment).filter(
        Shipment.id == id
    ).first()

    if not shipment:
        raise HTTPException(
            status_code=404,
            detail="Shipment not found"
        )

    new_status = data.status.upper()

    if new_status not in TRANSITIONS:
        raise HTTPException(
            status_code=400,
            detail="Unknown shipment status"
        )

    allowed = TRANSITIONS[shipment.status]

    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition: {shipment.status} to {new_status}"
        )

    shipment.status = new_status
    shipment.updatedAt = datetime.now(timezone.utc)

    db.commit()
    db.refresh(shipment)

    return shipment