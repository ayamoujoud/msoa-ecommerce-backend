from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MOCK Catalog")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PRODUCTS = {
    1: {"id": 1, "name": "Lenovo ThinkPad E14", "category": "Laptops", "price": 8499,
        "image": "https://placehold.co/600x400?text=ThinkPad+E14",
        "description": "Reliable 14-inch business laptop with Intel Core i5, 16GB RAM and 512GB SSD."},
    2: {"id": 2, "name": "Samsung Galaxy A55", "category": "Smartphones", "price": 4299,
        "image": "https://placehold.co/600x400?text=Galaxy+A55",
        "description": "5G smartphone with a 6.6-inch AMOLED display and 128GB storage."},
    3: {"id": 3, "name": "Sony WH-1000XM5", "category": "Audio", "price": 3499,
        "image": "https://placehold.co/600x400?text=Sony+Headphones",
        "description": "Wireless noise-cancelling headphones with premium sound."},
    4: {"id": 4, "name": "Logitech MX Master 3S", "category": "Accessories", "price": 1199,
        "image": "https://placehold.co/600x400?text=MX+Master+3S",
        "description": "Ergonomic wireless mouse designed for productivity."},
    5: {"id": 5, "name": "Dell UltraSharp 27", "category": "Monitors", "price": 3999,
        "image": "https://placehold.co/600x400?text=Dell+Monitor",
        "description": "27-inch QHD monitor with excellent color accuracy."},
    6: {"id": 6, "name": "Apple iPad Air", "category": "Tablets", "price": 7299,
        "image": "https://placehold.co/600x400?text=iPad+Air",
        "description": "Powerful and lightweight tablet for work and entertainment."},
}

@app.get("/products")
def list_products():
    return list(PRODUCTS.values())

@app.get("/products/{product_id}")
def get_product(product_id: int):
    if product_id not in PRODUCTS:
        raise HTTPException(404, "Product not found")
    return PRODUCTS[product_id]