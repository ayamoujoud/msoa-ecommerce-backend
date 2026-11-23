
# LAB 4 - Analytics Service

## 1. Présentation
Analytics Service est un consommateur Kafka développé
en Python avec kafka-python.

Il reçoit des événements provenant des microservices
de la plateforme e-commerce.

## 2. Architecture
Catalog Service -> Kafka -> Analytics Service

- Catalog : publie les événements.
- Kafka : conserve les événements.
- Analytics : lit et analyse les événements.

## 3. Configuration
- Broker : localhost:9092
- Topic : ecommerce.events
- Consumer Group : analytics-service
- Format : JSON
- Bibliothèque : kafka-python

## 4. Événement ProductConsulted
Exemple :

{
  "eventId": "uuid",
  "eventType": "ProductConsulted",
  "source": "catalog",
  "productId": 1,
  "timestamp": "2026-11-19T11:37:18+00:00"
}

## 5. Fonctionnement
Le Consumer lit les événements ProductConsulted
depuis Kafka et calcule les consultations
pour chaque produit.

Exemple :
Produit 1 : 5 consultations
Produit 2 : 1 consultation
Produit 3 : 1 consultation

## 6. Exécution
Installer les dépendances :

python -m pip install -r requirements.txt

Lancer Analytics :

python consumer.py

Relire les événements historiques :

python consumer.py --replay

## 7. Tests réalisés
- Réception des événements Kafka.
- Calcul des consultations de plusieurs produits.
- Relance du Consumer.
- Replay des anciens événements conservés dans Kafka.

## 8. Limites
- Les statistiques sont conservées en mémoire.
- Le replay reconstruit les statistiques depuis Kafka.
- La consommation des événements d'autres microservices
  reste à intégrer et tester avec le groupe.
- Kafka doit être disponible pour consommer les messages.

## 9. Conclusion
Analytics permet une consommation asynchrone
des événements et leur rejeu historique.

Cette implémentation contribue au scénario
Event Retention and Replay du LAB 4.
