import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

INVENTORY_URL = os.getenv("INVENTORY_URL", "http://localhost:8083")
CATALOG_URL = os.getenv("CATALOG_URL", "http://localhost:8082")
DB_PATH = os.getenv("DB_PATH", "orders.db")

app = FastAPI(title="Orders Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Base de données ----------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

with db() as c:
    c.execute(
        """CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            customer TEXT NOT NULL,
            items TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )

def to_dict(row):
    return {
        "id": row["id"],
        "userId": row["user_id"],
        "customer": json.loads(row["customer"]),
        "items": json.loads(row["items"]),
        "total": row["total"],
        "status": row["status"],
        "createdAt": row["created_at"],
    }

def get_row(order_id: str):
    with db() as c:
        row = c.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Order not found")
    return row

# ---------- Modèles ----------
class Item(BaseModel):
    productId: int
    quantity: int = Field(gt=0)

class Customer(BaseModel):
    name: str
    address: str
    city: str

class OrderCreate(BaseModel):
    userId: str
    customer: Customer
    items: List[Item] = Field(min_length=1)

class StatusUpdate(BaseModel):
    status: str

# ---------- Règles métier ----------
TRANSITIONS = {
    "PENDING_PAYMENT": {"PAID", "CANCELLED"},
    "PAID": {"SHIPPED", "CANCELLED"},
    "SHIPPED": {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}
CANCELLABLE = {"PENDING_PAYMENT", "PAID"}

# ---------- Clients vers les autres services ----------
def fetch_product(product_id: int) -> dict:
    try:
        r = httpx.get(f"{CATALOG_URL}/products/{product_id}", timeout=5)
    except httpx.RequestError:
        raise HTTPException(503, "Catalog service unavailable")
    if r.status_code == 404:
        raise HTTPException(400, f"Product {product_id} does not exist")
    r.raise_for_status()
    return r.json()

def inventory_call(action: str, items: list) -> bool:
    try:
        r = httpx.post(
            f"{INVENTORY_URL}/api/inventory/{action}",
            json={"items": items},
            timeout=5,
        )
    except httpx.RequestError:
        raise HTTPException(503, "Inventory service unavailable")
    if r.status_code >= 500:
        raise HTTPException(502, "Inventory service error")
    if r.status_code >= 400:
        return False
    return bool(r.json().get("success", False))

# ---------- Endpoints ----------
@app.get("/api/orders")
def list_orders(userId: Optional[str] = Query(None)):
    with db() as c:
        if userId:
            rows = c.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
                (userId,),
            ).fetchall()
        else:
            rows = c.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    return [to_dict(r) for r in rows]

@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    return to_dict(get_row(order_id))

@app.post("/api/orders", status_code=201)
def create_order(body: OrderCreate):
    # 1. Les prix et noms viennent de Catalog, jamais du frontend
    items, total = [], 0.0
    for it in body.items:
        product = fetch_product(it.productId)
        price = float(product["price"])
        total += price * it.quantity
        items.append({
            "productId": it.productId,
            "name": product.get("name", ""),
            "quantity": it.quantity,
            "price": price,
        })

    # 2. Réservation atomique du stock
    stock_items = [{"productId": i["productId"], "quantity": i["quantity"]} for i in items]
    if not inventory_call("reserve", stock_items):
        raise HTTPException(409, "Insufficient stock")

    # 3. Enregistrement (compensation : on libère le stock si l'insertion échoue)
    order_id = f"order-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    try:
        with db() as c:
            c.execute(
                "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)",
                (order_id, body.userId, body.customer.model_dump_json(),
                 json.dumps(items), round(total, 2), "PENDING_PAYMENT", now),
            )
    except Exception:
        inventory_call("release", stock_items)
        raise HTTPException(500, "Could not save order")
    return to_dict(get_row(order_id))

@app.patch("/api/orders/{order_id}/status")
def update_status(order_id: str, body: StatusUpdate):
    row = get_row(order_id)
    new = body.status.upper()
    if new not in TRANSITIONS.get(row["status"], set()):
        raise HTTPException(409, f"Transition {row['status']} -> {new} not allowed")
    with db() as c:
        c.execute("UPDATE orders SET status = ? WHERE id = ?", (new, order_id))
    return to_dict(get_row(order_id))

@app.post("/api/orders/{order_id}/cancel")
def cancel_order(order_id: str):
    row = get_row(order_id)
    if row["status"] not in CANCELLABLE:
        raise HTTPException(409, f"Order in status {row['status']} cannot be cancelled")
    items = [{"productId": i["productId"], "quantity": i["quantity"]}
             for i in json.loads(row["items"])]
    if not inventory_call("release", items):
        raise HTTPException(502, "Could not release stock, order not cancelled")
    with db() as c:
        c.execute("UPDATE orders SET status = 'CANCELLED' WHERE id = ?", (order_id,))
    return to_dict(get_row(order_id))