from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="MOCK Inventory")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Stocks identiques à ceux du frontend
STOCK = {1: 12, 2: 20, 3: 8, 4: 25, 5: 10, 6: 15}

class Item(BaseModel):
    productId: int
    quantity: int

class Payload(BaseModel):
    items: List[Item]

@app.get("/api/inventory/{product_id}")
def get_stock(product_id: int):
    return {"productId": product_id, "stock": STOCK.get(product_id, 0)}

@app.post("/api/inventory/check")
def check(p: Payload):
    return {"available": all(STOCK.get(i.productId, 0) >= i.quantity for i in p.items)}

@app.post("/api/inventory/reserve")
def reserve(p: Payload):
    # Atomique : on vérifie TOUT avant de modifier quoi que ce soit
    if not all(STOCK.get(i.productId, 0) >= i.quantity for i in p.items):
        return {"success": False}
    for i in p.items:
        STOCK[i.productId] -= i.quantity
    return {"success": True}

@app.post("/api/inventory/release")
def release(p: Payload):
    for i in p.items:
        STOCK[i.productId] = STOCK.get(i.productId, 0) + i.quantity
    return {"success": True}