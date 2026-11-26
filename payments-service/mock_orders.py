from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

ADDRESSES = [
    "Casablanca, Morocco",
    "Rabat, Morocco",
    "Marrakech, Morocco",
    "Tanger, Morocco",
    "Fes, Morocco",
]

# order-1 ... order-5, tous PENDING, chacun avec une adresse
ORDERS = {
    f"order-{i}": {
        "id": f"order-{i}",
        "userId": "user-1",
        "items": [{"productId": i, "quantity": 1}],
        "total": 50.0 * i,
        "status": "PENDING",
        "shippingAddress": ADDRESSES[i - 1],
        "createdAt": "2026-11-10T10:00:00Z",
    }
    for i in range(1, 6)
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