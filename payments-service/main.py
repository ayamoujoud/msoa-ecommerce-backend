import os
import sqlite3
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ---------- Configuration ----------
ORDERS_URL = os.getenv("ORDERS_URL", "http://localhost:8084")
DB_PATH = os.getenv("DB_PATH", "payments.db")

# "CARD_DECLINED" sert uniquement à tester un paiement refusé
ALLOWED_METHODS = {"CARD", "PAYPAL", "CASH_ON_DELIVERY", "CARD_DECLINED"}

# Statuts de commande qui autorisent un paiement (à aligner avec l'équipe Orders)
PAYABLE_STATUSES = set(
    os.getenv("PAYABLE_STATUSES", "PENDING,CREATED,PENDING_PAYMENT").split(",")
)

app = FastAPI(title="Payments Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Gestion des erreurs (format JSON uniforme) ----------
class ApiError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "message": exc.message},
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": "Internal server error"},
    )


# ---------- Base de données (propre au service Payments) ----------
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id         TEXT PRIMARY KEY,
                order_id   TEXT NOT NULL,
                user_id    TEXT,
                amount     REAL NOT NULL,
                method     TEXT NOT NULL,
                status     TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        # Garantit qu'une commande n'a qu'un seul paiement réussi
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_one_success_per_order
            ON payments(order_id) WHERE status = 'SUCCESS'
            """
        )


init_db()


def row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "orderId": row["order_id"],
        "userId": row["user_id"],
        "amount": row["amount"],
        "method": row["method"],
        "status": row["status"],
        "createdAt": row["created_at"],
    }


# ---------- Modèles ----------
class PaymentRequest(BaseModel):
    orderId: str
    method: str


# ---------- Communication avec Orders (service Supplier) ----------
async def fetch_order(order_id: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{ORDERS_URL}/api/orders/{order_id}")
    except httpx.RequestError:
        raise ApiError(503, "Orders service unavailable")
    if resp.status_code == 404:
        raise ApiError(404, f"Order {order_id} not found")
    if resp.status_code != 200:
        raise ApiError(502, "Unexpected response from Orders service")
    return resp.json()


async def mark_order_paid(order_id: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.patch(
                f"{ORDERS_URL}/api/orders/{order_id}/status",
                json={"status": "PAID"},
            )
        return resp.status_code in (200, 204)
    except httpx.RequestError:
        return False


# ---------- Endpoints ----------
@app.get("/health")
def health():
    return {"status": "UP", "service": "payments"}


@app.get("/api/payments")
def list_payments(userId: str | None = None):
    with get_conn() as conn:
        if userId:
            rows = conn.execute(
                "SELECT * FROM payments WHERE user_id = ? ORDER BY created_at DESC",
                (userId,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM payments ORDER BY created_at DESC"
            ).fetchall()
    return [row_to_dict(r) for r in rows]


@app.get("/api/payments/order/{order_id}")
def get_payment_by_order(order_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM payments WHERE order_id = ? ORDER BY created_at DESC LIMIT 1",
            (order_id,),
        ).fetchone()
    if row is None:
        raise ApiError(404, f"No payment found for order {order_id}")
    return row_to_dict(row)


@app.post("/api/payments", status_code=201)
async def create_payment(body: PaymentRequest):
    method = body.method.upper().strip()
    if method not in ALLOWED_METHODS:
        raise ApiError(400, f"Invalid payment method: {body.method}")

    # 1) Vérifier la commande auprès de Orders (source de vérité)
    order = await fetch_order(body.orderId)

    # 2) Pas de double paiement
    with get_conn() as conn:
        already_paid = conn.execute(
            "SELECT 1 FROM payments WHERE order_id = ? AND status = 'SUCCESS'",
            (body.orderId,),
        ).fetchone()
    if already_paid:
        raise ApiError(409, "Order already paid")

    # 3) La commande doit être dans un état payable
    order_status = str(order.get("status", "")).upper()
    if order_status not in PAYABLE_STATUSES:
        raise ApiError(409, f"Order cannot be paid (status: {order_status})")

    amount = order.get("total")
    if amount is None or amount <= 0:
        raise ApiError(409, "Order has an invalid total")

    # 4) Simulation du paiement
    status = "FAILED" if method == "CARD_DECLINED" else "SUCCESS"

    payment_id = f"pay-{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()

    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO payments (id, order_id, user_id, amount, method, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (payment_id, body.orderId, order.get("userId"), amount, method, status, created_at),
            )
    except sqlite3.IntegrityError:
        raise ApiError(409, "Order already paid")

    # 5) Si succès, informer Orders -> statut PAID
    if status == "SUCCESS":
        ok = await mark_order_paid(body.orderId)
        if not ok:
            # Compensation : on annule le paiement pour rester cohérent
            with get_conn() as conn:
                conn.execute(
                    "UPDATE payments SET status = 'FAILED' WHERE id = ?", (payment_id,)
                )
            raise ApiError(502, "Could not update order status; payment cancelled")

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
    return row_to_dict(row)