from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Inventory(Base):

    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(Integer, unique=True, nullable=False, index=True)

    quantity_available = Column(Integer, default=0, nullable=False)

    quantity_reserved = Column(Integer, default=0, nullable=False)

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )