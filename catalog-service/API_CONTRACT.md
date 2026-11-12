
# LAB 3 - Catalog Service API Contract

## 1. Présentation
Microservice : Catalog
Technologies : Python, FastAPI, SQLite
Port : 8082
Rôle : Fournir les informations des produits.

## 2. Endpoints REST

| Méthode | Endpoint | Description |
|---|---|---|
| GET | /products | Liste des produits V1 |
| GET | /products/{product_id} | Produit par ID V1 |
| GET | /v2/products | Liste des produits V2 |
| GET | /v2/products/{product_id} | Produit par ID V2 |

## 3. Paramètres et headers

- product_id : entier obligatoire dans les URLs concernées.
- Request body : aucun.
- Accept : application/json.
- Content-Type de la réponse : application/json.

## 4. Response Schema V1

{
  "id": 1,
  "name": "Lenovo ThinkPad E14",
  "category": "Laptops",
  "price": 7999.0,
  "image": "data:image/svg+xml;charset=utf-8,...",
  "description": "Ordinateur portable Lenovo ThinkPad E14"
}

Types :
- id : integer
- name : string
- category : string
- price : number
- image : string
- description : string

GET /products retourne un tableau d'objets V1.
GET /products/{product_id} retourne un objet V1.

## 5. Response Schema V2

{
  "id": 1,
  "name": "Lenovo ThinkPad E14",
  "category": "Laptops",
  "price": {
    "amount": 7999.0,
    "currency": "MAD"
  },
  "image": "data:image/svg+xml;charset=utf-8,...",
  "description": "Ordinateur portable Lenovo ThinkPad E14"
}

En V2 :
- price : object
- price.amount : number
- price.currency : string

Les endpoints de liste retournent des tableaux.
Les endpoints de détail retournent un objet.

## 6. HTTP Status Codes

- 200 OK : requête réussie.
- 404 Not Found : produit inexistant.
- 422 Unprocessable Entity : identifiant invalide.

Exemple 404 :
{
  "detail": "Product not found"
}

Exemple 422 : réponse FastAPI contenant
un champ "detail" avec les erreurs de validation.

## 7. API Versioning

La V1 conserve un prix numérique.
La V2 introduit un prix sous forme d'objet.

Les anciennes API restent disponibles pour
éviter les breaking changes.

Le frontend React et les anciens consommateurs
continuent d'utiliser la V1.

La V2 expose actuellement la devise MAD.
La conversion réelle entre devises n'est pas
encore implémentée.

## 8. Customer-Supplier

Catalog : Supplier.
Orders : Customer.

Orders peut utiliser GET /products/{product_id}
pour récupérer les informations d'un produit.

Le contrat REST doit être validé avec l'équipe Orders.

## 9. Tests

Les tests sont effectués avec Swagger UI :
http://localhost:8082/docs

Vérifier :
- Réponses V1 et V2.
- Erreurs 404 et 422.
- Compatibilité du frontend React.
