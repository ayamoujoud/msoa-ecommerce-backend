"""Catalog microservice for MSOA Shop — FastAPI + SQLite."""
from contextlib import closing
from pathlib import Path
import sqlite3
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = Path(__file__).with_name("catalog.db")
app = FastAPI(title="Catalog Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def image_for(label: str) -> str:
    """Stable self-contained placeholder that needs no external image host."""
    from html import escape
    clean = escape(label)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="420" viewBox="0 0 640 420">'
        '<rect width="640" height="420" fill="#e7ecf2"/>'
        '<rect x="24" y="24" width="592" height="372" rx="24" fill="#f6f8fb"/>'
        f'<text x="320" y="212" text-anchor="middle" dominant-baseline="middle" '
        f'font-family="Arial,sans-serif" font-weight="700" font-size="35" fill="#52657a">{clean}</text>'
        '</svg>'
    )
    return "data:image/svg+xml;charset=utf-8," + quote(svg, safe="")


SEED_PRODUCTS = [
    (1, "Lenovo ThinkPad E14", "Laptops", 7999.0, "ThinkPad E14", "Ordinateur portable Lenovo ThinkPad E14"),
    (2, "Samsung Galaxy A55", "Smartphones", 4499.0, "Galaxy A55", "Smartphone Samsung Galaxy A55"),
    (3, "Sony Headphones", "Audio", 1499.0, "Sony Headphones", "Casque audio Sony"),
    (4, "Logitech MX Master 3S", "Accessories", 1199.0, "MX Master 3S", "Souris sans fil Logitech"),
    (5, "Dell UltraSharp 27", "Monitors", 3999.0, "Dell Monitor", "Moniteur Dell UltraSharp 27 pouces"),
    (6, "Apple iPad Air", "Tablets", 7299.0, "iPad Air", "Tablette Apple iPad Air"),
]


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(connect_db()) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                image TEXT NOT NULL,
                description TEXT NOT NULL
            )
        """)
        for pid, name, category, price, img_label, description in SEED_PRODUCTS:
            conn.execute(
                "INSERT OR IGNORE INTO products (id, name, category, price, image, description) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (pid, name, category, price, image_for(img_label), description),
            )
        conn.commit()


init_db()


def as_product(row):
    return dict(row)


@app.get("/products")
def get_products():
    with closing(connect_db()) as conn:
        rows = conn.execute(
            "SELECT id, name, category, price, image, description FROM products ORDER BY id"
        ).fetchall()
    return [as_product(row) for row in rows]


@app.get("/products/{product_id}")
def get_product(product_id: int):
    with closing(connect_db()) as conn:
        row = conn.execute(
            "SELECT id, name, category, price, image, description FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return as_product(row)

# LAB 3 - API V2 : nouveau format du prix

def to_v2_product(product):
    product = dict(product)
    product["price"] = {
        "amount": product["price"],
        "currency": "MAD"
    }
    return product


@app.get("/v2/products")
def get_products_v2():
    products = get_products()
    return [to_v2_product(p) for p in products]


@app.get("/v2/products/{product_id}")
def get_product_v2(product_id: int):
    product = get_product(product_id)
    return to_v2_product(product)
