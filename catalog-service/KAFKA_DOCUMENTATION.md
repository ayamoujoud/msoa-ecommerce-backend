# LAB 4 — Communication Kafka du Catalog Service

## 1. Présentation

Dans le cadre du LAB 4 — Implementing Microservice Communication, nous avons ajouté une communication asynchrone basée sur **Apache Kafka** au Catalog Service développé précédemment.

Le Catalog Service utilise **Python, FastAPI et SQLite**. Ses API REST V1 et V2 restent disponibles.

L'objectif de cette intégration est de permettre la publication d'événements produits, qui pourront être consommés par un futur Analytics Service.

## 2. Architecture de communication

Le fonctionnement repose sur trois composants :

- **Catalog Service (Producer)** : génère et publie les événements.
- **Apache Kafka (Broker)** : reçoit et conserve les événements dans un topic, selon sa configuration de rétention.
- **Analytics Service (Consumer prévu)** : pourra lire les événements et rejouer leur historique pour effectuer des analyses.

Flux de communication :

`Catalog Service → Apache Kafka → Analytics Service`

Cette communication est asynchrone : le service Analytics n'a pas besoin d'être disponible au moment où l'événement est publié.

## 3. Configuration Kafka

| Paramètre | Valeur |
|---|---|
| Broker Kafka | `localhost:9092` |
| Topic | `ecommerce.events` |
| Format des messages | JSON |
| Type d'événement | `ProductConsulted` |
| Producteur | Catalog Service |
| Bibliothèque Python | `kafka-python` |
| Interface de supervision | Kafka UI — `localhost:8080` |

Kafka est exécuté localement à l'aide de Docker.

## 4. Contrat de l'événement ProductConsulted

L'événement `ProductConsulted` est publié lorsqu'une consultation de produit est explicitement signalée via une requête REST.

Exemple de message :

```json
{
  "eventId": "86f35d3b-a07d-4d06-b79d-9307d1f00000",
  "eventType": "ProductConsulted",
  "source": "catalog",
  "productId": 1,
  "timestamp": "2026-11-19T11:37:18+00:00"
}
```

### Structure du message

| Champ | Type | Description |
|---|---|---|
| `eventId` | string (UUID) | Identifiant unique de l'événement |
| `eventType` | string | Type d'événement : ProductConsulted |
| `source` | string | Microservice émetteur : catalog |
| `productId` | integer | Identifiant du produit consulté |
| `timestamp` | string (ISO 8601) | Date et heure de l'événement en UTC |

La clé Kafka est l'identifiant du produit, encodé sous forme de chaîne UTF-8.

## 5. Implémentation du Producer

Le fichier `kafka_producer.py` contient la fonction `publish_product_consulted(product_id)`.

Cette fonction :

1. Établit une connexion avec Kafka sur le port 9092.
2. Génère un événement JSON contenant l'identifiant du produit, un UUID et un timestamp.
3. Publie cet événement dans le topic `ecommerce.events`.
4. Attend l'accusé de réception du broker.
5. Ferme la connexion Kafka.

## 6. Intégration avec FastAPI

Un endpoint REST a été ajouté au fichier `main.py` :

**POST /products/{product_id}/consultations**

Ce endpoint :

- Vérifie que le produit demandé existe dans SQLite.
- Appelle la fonction de publication Kafka.
- Retourne une confirmation si le broker accepte le message.
- Retourne une erreur HTTP 404 si le produit est inexistant.
- Retourne une erreur HTTP 503 si la publication Kafka échoue.

Les anciennes API REST V1 et V2 sont conservées afin de préserver la compatibilité avec le frontend React.

## 7. Tests effectués

Le test de publication a été réalisé depuis Swagger UI.

**Scénario testé :**

1. Démarrer Kafka avec Docker.
2. Démarrer le Catalog Service FastAPI.
3. Exécuter `POST /products/1/consultations` depuis Swagger UI.
4. Ouvrir Kafka UI.
5. Consulter le topic `ecommerce.events` dans l'onglet Messages.

**Résultat observé :**

Un message JSON a été retrouvé dans Kafka UI, avec la clé `1`, dans la partition `0`, à l'offset `0`.

Ce résultat confirme la publication d'un événement depuis Catalog Service vers Kafka.

## 8. Conservation et rejeu des événements

Kafka permet de conserver les événements selon la politique de rétention configurée.

Un Analytics Service pourra ensuite consommer ces événements, y compris des événements antérieurs à son démarrage, tant qu'ils sont encore conservés dans Kafka.

Le rejeu peut être réalisé en repositionnant les offsets du consommateur.

**Limite actuelle :** la publication côté Catalog a été vérifiée. La consommation par Analytics et le rejeu des événements restent à intégrer et à tester avec l'équipe.

## 9. Conclusion

L'intégration de Kafka permet au Catalog Service de publier des événements produits sans dépendre directement de la disponibilité d'un consommateur Analytics.

Cette solution répond à la partie publication des événements du scénario *Event Retention and Replay* du LAB 4, tout en conservant les fonctionnalités existantes du Catalog Service.