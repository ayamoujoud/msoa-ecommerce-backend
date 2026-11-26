
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
import httpx

app = FastAPI(title="E-commerce API Gateway")

# Problem 1 : Routage statique
SERVICES = {
    "catalog": "http://127.0.0.1:8082",
    "shipping": "http://127.0.0.1:8086",
    "inventory": "http://localhost:8083",
    "orders": "http://localhost:8084",
    "payements": "http://localhost:8085",
    "auth": "http://localhost:8081"
}


@app.api_route(
    "/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
)
@app.api_route(
    "/{service}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
)
async def proxy(service: str, request: Request, path: str = ""):

    address = SERVICES.get(service)

    if address is None:
        raise HTTPException(
            status_code=503,
            detail=f"Service {service} unavailable"
        )

    # Construire l'URL du microservice
    url = f"{address.rstrip('/')}/{path.lstrip('/')}"

    # Transférer les headers utiles
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in (
            "host",
            "content-length",
            "connection",
            "transfer-encoding"
        )
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.request(
                method=request.method,
                url=url,
                params=request.query_params,
                content=await request.body(),
                headers=headers
            )

        except httpx.RequestError:
            raise HTTPException(
                status_code=503,
                detail=f"Service {service} is unavailable"
            )

    excluded = {
        "content-length",
        "transfer-encoding",
        "connection",
        "content-encoding"
    }

    response_headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in excluded
    }

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers
    )


@app.get("/")
def home():
    return {
        "service": "API Gateway",
        "status": "running"
    }
