
from fastapi import FastAPI
from app.database import engine, Base
from app import models
from app.routes.inventory import router as inventory_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Inventory Service",
    description="Microservice de gestion des stocks",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Création des tables
Base.metadata.create_all(bind=engine)

# Enregistrement des routes
app.include_router(inventory_router)


@app.get("/")
def home():
    return {
        "message": "Inventory Service is running!"
    }
