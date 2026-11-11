# MSOA E-commerce Backend

Backend en microservices pour l'application e-commerce du TP « Microservice-oriented Architectures »
(Master Big Data & Data Science, Pr. Zouheir BANOU).

Frontend fourni : https://github.com/ZOUHEIRBN/MSOA-E-com-Demo

## Équipe

| Service   | Port | Responsable | Technologie        |
|-----------|------|-------------|--------------------|
| Auth      | 8081 | hiba ouafi      | Python |
| Catalog   | 8082 |  ouatile yousra      | Python           |
| Inventory | 8083 | Fouzi hajar     | Python          |
| Orders    | 8084 | hiba mhada  | Python       |
| Payments  | 8085 | Aya Moujoud | Python / FastAPI + SQLite |
| Shipping  | 8086 | ablou fatime zahera      | Python           |

## Architecture

- Chaque service est indépendant, avec sa propre base de données et son propre dossier.
- Pattern de Context Mapping : **Customer/Supplier**. Le service amont (Supplier) fournit un contrat REST
  stable, le service aval (Customer) s'y conforme.
- Les contrats REST sont ceux du README du frontend (méthodes, chemins, JSON).

## Dépendances entre services

| Service (Customer) | Appelle (Supplier) | Pourquoi |
|--------------------|--------------------|----------|
| Orders             | Inventory          | Réserver / libérer le stock |
| Orders             | Catalog            | Récupérer les prix (le frontend n'est pas source de vérité) |
| Payments           | Orders             | Vérifier la commande, puis la passer à `PAID` |
| Shipping           | Orders             | Garder le suivi cohérent avec le statut de la commande |

## Conventions communes (à respecter par tous)

- Statuts de commande : `PENDING`, `PAID`, `SHIPPED`, `CANCELLED` <à compléter ensemble>
- `PATCH /api/orders/{id}/status` : body `{"status": "PAID"}`
- Erreurs : JSON `{"error": "...", "message": "..."}` avec le bon code HTTP (400, 404, 409, 503...)
- CORS : autoriser `http://localhost:5173`
- URLs des autres services via variables d'environnement
  (`ORDERS_URL`, `INVENTORY_URL`, `CATALOG_URL`), valeurs par défaut `http://localhost:<port>`

## Lancement

Chaque service a son propre README avec ses instructions dans son dossier.

Ordre conseillé : Auth, Catalog, Inventory, Orders, Payments, Shipping, puis le frontend (`npm run dev`).

## Connexion au frontend

Dans `src/config/backend.js` du frontend, passer chaque service de `"mock"` à `"rest"`
au fur et à mesure qu'il est opérationnel, et vérifier l'URL dans `API_URLS`.
Les composants React ne sont pas modifiés.

## Organisation Git

- Un dossier par service, une branche par service (`payments-service`, `orders-service`, ...).
- Pull request vers `main` quand le service fonctionne.
- Ne pas commiter `venv/`, `node_modules/`, `*.db`, `.env`.

## Tests et preuves

Les preuves de tests (captures, commandes curl) sont dans le dossier de chaque service.
