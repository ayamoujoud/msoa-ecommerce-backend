
from pydantic import BaseModel, Field
from typing import List


class InventoryItem(BaseModel):
    productId: int
    quantity: int = Field(gt=0)


class InventoryRequest(BaseModel):
    items: List[InventoryItem] = Field(min_length=1)
