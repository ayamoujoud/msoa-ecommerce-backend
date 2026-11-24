import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

import inventory_client

CATALOG_URL = os.getenv("CATALOG_URL", "http://localhost:8082")
SHIPPING_URL = os.getenv("SHIPPING_URL", "http://localhost:8086")
DB_PATH = os.getenv("DB_PATH", "orders.db")

app = FastAPI(title="Orders Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Format d'erreur commun : {"error": "...", "message": "..."} ----------
ERROR_CODES = {
    400: "bad_request",
    404: "not_found",
    409: "conflict",
    500: "internal_error",
    502: "bad_gateway",
    503: "service_unavailable",
}


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": ERROR_CODES.get(exc.status_code, "error"),
            "message": str(exc.detail),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0]
    where = ".".join(str(p) for p in first["loc"] if p not in ("body", "query"))
    return JSONResponse(
        status_code=400,
        content={
            "error": "bad_request",
            "message": f"{where}: {first['msg']}" if where else first["msg"],
        },
    )


# ---------- Base de données ----------
@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        with conn:  # commit / rollback
            yield conn
    finally:
        conn.close()


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


def set_status_if(order_id: str, expected: str, new: str) -> bool:
    """Changement de statut atomique : n'applique que si le statut est celui attendu."""
    with db() as c:
        cur = c.execute(
            "UPDATE orders SET status = ? WHERE id = ? AND status = ?",
            (new, order_id, expected),
        )
        return cur.rowcount == 1


# ---------- Modèles ----------
class Item(BaseModel):
    productId: int
    quantity: int = Field(gt=0)


class Customer(BaseModel):
    name: str = Field(min_length=1)
    address: str = Field(min_length=1)
    city: str = Field(min_length=1)


class OrderCreate(BaseModel):
    userId: str = Field(min_length=1)
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
STATUSES = set(TRANSITIONS)
CANCELLABLE = {"PENDING_PAYMENT", "PAID"}
SHIPMENT_CANCELLABLE = {"PREPARING", "CANCELLED"}


# ---------- Clients vers les autres services ----------
def fetch_product(product_id: int) -> dict:
    try:
        r = httpx.get(f"{CATALOG_URL}/products/{product_id}", timeout=5)
    except httpx.RequestError:
        raise HTTPException(503, "Catalog service unavailable")
    if r.status_code == 404:
        raise HTTPException(400, f"Product {product_id} does not exist")
    if r.status_code != 200:
        raise HTTPException(502, "Catalog service error")
    return r.json()


def extract_price(product: dict) -> float:
    """Accepte le prix v1 (nombre) comme le prix v2 ({"amount": ..., "currency": ...})."""
    price = product.get("price")
    if isinstance(price, dict):
        price = price.get("amount")
    try:
        value = float(price)
    except (TypeError, ValueError):
        raise HTTPException(502, "Catalog returned an invalid price")
    if value < 0:
        raise HTTPException(502, "Catalog returned an invalid price")
    return value


def inventory_call(action: str, items: list) -> bool:
    try:
        return inventory_client.call(action, items)
    except inventory_client.InventoryUnavailable:
        raise HTTPException(503, "Inventory service unavailable")
    except inventory_client.InventoryError:
        raise HTTPException(502, "Inventory service error")


def get_shipment_if_any(order_id: str) -> Optional[dict]:
    try:
        r = httpx.get(f"{SHIPPING_URL}/api/shipments/order/{order_id}", timeout=5)
    except httpx.RequestError:
        raise HTTPException(503, "Shipping service unavailable")
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise HTTPException(502, "Shipping service error")
    return r.json()


def cancel_shipment_best_effort(shipment: dict) -> None:
    """Garde le suivi cohérent : si l'expédition est encore en préparation, on l'annule."""
    if not shipment or shipment.get("status") != "PREPARING":
        return
    try:
        httpx.patch(
            f"{SHIPPING_URL}/api/shipments/{shipment['id']}/status",
            json={"status": "CANCELLED"},
            timeout=5,
        )
    except httpx.RequestError:
        pass


# ---------- Annulation (logique unique, utilisée par /cancel et par PATCH CANCELLED) ----------
def do_cancel(order_id: str) -> dict:
    row = get_row(order_id)
    previous = row["status"]
    if previous not in CANCELLABLE:
        raise HTTPException(409, f"Order in status {previous} cannot be cancelled")

    # Une commande payée peut déjà avoir une expédition : on refuse si elle est partie.
    shipment = None
    if previous == "PAID":
        shipment = get_shipment_if_any(order_id)
        if shipment and shipment.get("status") not in SHIPMENT_CANCELLABLE:
            raise HTTPException(409, "Cannot cancel an order that has already been shipped")

    # On "réserve" l'annulation de façon atomique : deux annulations simultanées
    # ne peuvent pas libérer le stock deux fois.
    if not set_status_if(order_id, previous, "CANCELLED"):
        raise HTTPException(409, "Order status changed, please retry")

    items = [
        {"productId": i["productId"], "quantity": i["quantity"]}
        for i in json.loads(row["items"])
    ]
    try:
        released = inventory_call("release", items)
    except HTTPException:
        set_status_if(order_id, "CANCELLED", previous)
        raise
    if not released:
        set_status_if(order_id, "CANCELLED", previous)
        raise HTTPException(502, "Could not release stock, order not cancelled")

    cancel_shipment_best_effort(shipment)
    return to_dict(get_row(order_id))


# ---------- Endpoints ----------
@app.get("/health")
def health():
    return {"status": "UP", "service": "orders"}


@app.get("/api/orders")
def list_orders(userId: str = Query(..., min_length=1)):
    with db() as c:
        rows = c.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (userId,),
        ).fetchall()
    return [to_dict(r) for r in rows]


@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    return to_dict(get_row(order_id))


@app.post("/api/orders", status_code=201)
def create_order(body: OrderCreate):
    # 0. Regrouper les lignes qui portent sur le même produit
    #    (sinon Inventory vérifie chaque ligne séparément et peut sur-réserver)
    merged = {}
    for it in body.items:
        merged[it.productId] = merged.get(it.productId, 0) + it.quantity

    # 1. Les prix et noms viennent de Catalog, jamais du frontend
    items, total = [], 0.0
    for product_id, quantity in merged.items():
        product = fetch_product(product_id)
        price = extract_price(product)
        total += price * quantity
        items.append({
            "productId": product_id,
            "name": product.get("name", ""),
            "quantity": quantity,
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
        try:
            inventory_call("release", stock_items)
        except HTTPException:
            pass
        raise HTTPException(500, "Could not save order")
    return to_dict(get_row(order_id))


@app.patch("/api/orders/{order_id}/status")
def update_status(order_id: str, body: StatusUpdate):
    new = body.status.strip().upper()
    if new not in STATUSES:
        raise HTTPException(400, f"Unknown status {body.status}")

    # Passer à CANCELLED par PATCH doit aussi libérer le stock : même logique que /cancel
    if new == "CANCELLED":
        return do_cancel(order_id)

    row = get_row(order_id)
    if new not in TRANSITIONS.get(row["status"], set()):
        raise HTTPException(409, f"Transition {row['status']} -> {new} not allowed")
    if not set_status_if(order_id, row["status"], new):
        raise HTTPException(409, "Order status changed, please retry")
    return to_dict(get_row(order_id))


@app.post("/api/orders/{order_id}/cancel")
def cancel_order(order_id: str):
    return do_cancel(order_id)