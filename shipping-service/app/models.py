from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel, ConfigDict
from .database import Base
from datetime import datetime


# Modèle de la base de données
class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(String, primary_key=True, index=True)
    orderId = Column(String, unique=True, nullable=False, index=True)

    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)

    trackingNumber = Column(String, unique=True, nullable=False)
    status = Column(String, nullable=False, default="PREPARING")

    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


# Structure de l'adresse reçue depuis React
class AddressSchema(BaseModel):
    name: str
    address: str
    city: str


# Requête de création
class ShipmentCreate(BaseModel):
    orderId: str
    address: AddressSchema


# Requête de modification du statut
class ShipmentStatusUpdate(BaseModel):
    status: str


# Structure de la réponse
class ShipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    orderId: str
    name: str
    address: str
    city: str
    trackingNumber: str
    status: str
    createdAt: datetime
    updatedAt: datetime