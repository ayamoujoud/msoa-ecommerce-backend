# LAB 5 — API Gateway & Service Discovery

## Objectif

Mettre en place un point d'entrée unique pour les microservices de notre plateforme e-commerce, puis ajouter un mécanisme de Service Discovery permettant de retrouver dynamiquement leurs adresses.

## Travail réalisé

- Création du microservice `gateway-service` avec Python, FastAPI et HTTPX.
- Configuration du Gateway sur le port `8080`.
- Implémentation d'un reverse proxy HTTP avec routage statique.
- Routage Catalog : `/catalog/{path}` vers `http://localhost:8082/{path}`.
- Conservation de la méthode HTTP, du corps de la requête, des paramètres et des principaux en-têtes.
- Transmission du code HTTP et du corps de la réponse du microservice.
- Test réussi avec Catalog :
  - Direct : `http://localhost:8082/products`
  - Via Gateway : `http://localhost:8080/catalog/products`
  - Résultat : mêmes 6 produits.

## Démarrer le Gateway

Installer les dépendances :

```powershell
pip install -r requirements.txt
```

Lancer depuis le dossier `gateway-service` :

```powershell
python -m uvicorn main:app --reload --port 8080
```

## Travail restant — À compléter par le groupe

- Ajouter les routes des autres microservices.
- Tester le Gateway avec au moins deux microservices différents.
- Relier le frontend React au Gateway.
- Ajouter un Service Registry en mémoire.
- Implémenter `POST /registry/register`.
- Implémenter `GET /registry/services`.
- Remplacer les adresses statiques par la résolution dynamique.
- Retour
