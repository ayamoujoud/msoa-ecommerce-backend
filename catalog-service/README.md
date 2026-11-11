# Catalog Service — MSOA Shop

Backend indépendant FastAPI + SQLite, port 8082.

## Installation

Depuis `MSOA-E-com-Demo/catalog-service` dans PowerShell :

```powershell
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8082
```

## Intégration React

Dans `src/config/backend.js` :

```js
CATALOG: "rest",
```

Conserver `API_URLS.CATALOG: "http://localhost:8082"` et les autres modes en `mock` pour l'instant.

Démarrer React séparément avec `npm run dev` à la racine du projet.

## API

- `GET http://localhost:8082/products` : liste des produits
- `GET http://localhost:8082/products/1` : un produit
- `GET http://localhost:8082/docs` : documentation Swagger

Le fichier `catalog.db` est créé au premier lancement. Les six produits initiaux sont ajoutés une seule fois (INSERT OR IGNORE). Pour réinitialiser les produits au jeu de démonstration, arrêter le serveur, supprimer `catalog.db`, et relancer.

Les images sont des placeholders SVG incorporés aux données, sans dépendance à Internet. Les stocks et quantités disponibles appartiennent à Inventory Service, pas à Catalog.
