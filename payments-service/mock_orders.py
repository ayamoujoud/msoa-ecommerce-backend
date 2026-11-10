from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

ORDERS = {
    "order-1": {"id": "order-1", "userId": "user-1", "items": [{"productId": 1, "quantity": 2}],
                "total": 100.0, "status": "PENDING", "createdAt": "2026-11-10T10:00:00Z"},
    "order-2": {"id": "order-2", "userId": "user-1", "items": [{"productId": 2, "quantity": 1}],
                "total": 50.0, "status": "PENDING", "createdAt": "2026-11-10T10:05:00Z"},
}


class StatusBody(BaseModel):
    status: str


@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    if order_id not in ORDERS:
        return JSONResponse(status_code=404, content={"error": "not found"})
    return ORDERS[order_id]


@app.patch("/api/orders/{order_id}/status")
def patch_status(order_id: str, body: StatusBody):
    if order_id not in ORDERS:
        return JSONResponse(status_code=404, content={"error": "not found"})
    ORDERS[order_id]["status"] = body.status
    return ORDERS[order_id]