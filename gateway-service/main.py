
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
import httpx

app = FastAPI(title="E-commerce API Gateway")

# Routage statique — Problem 1
SERVICES = {
    "catalog": "http://localhost:8082",
    # Ajouter ici les autres services du groupe
}


@app.api_route(
    "/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
)
async def proxy(service: str, path: str, request: Request):
    address = SERVICES.get(service)

    if address is None:
        raise HTTPException(status_code=503, detail="Service unavailable")

    url = f"{address}/{path}"

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.request(
                method=request.method,
                url=url,
                params=request.query_params,
                content=await request.body(),
                headers={
                    key: value
                    for key, value in request.headers.items()
                    if key.lower() not in ("host", "content-length")
                },
            )
        except httpx.RequestError:
            raise HTTPException(
                status_code=503,
                detail="Downstream service unavailable"
            )

    excluded = {"content-length", "transfer-encoding", "connection", "content-encoding"}
    headers = {
        key: value for key, value in response.headers.items()
        if key.lower() not in excluded
    }

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=headers,
    )
