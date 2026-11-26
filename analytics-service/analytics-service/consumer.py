
import json
import sys
from collections import Counter

from kafka import KafkaConsumer
from kafka.errors import KafkaError

TOPIC = "ecommerce.events"
BOOTSTRAP_SERVERS = "localhost:9092"

# Mode replay : relire les événements depuis le début
REPLAY = "--replay" in sys.argv

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=BOOTSTRAP_SERVERS,
    group_id="analytics-service",
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    value_deserializer=lambda message: json.loads(
        message.decode("utf-8")
    ),
)

# Pour rejouer les anciens événements
if REPLAY:
    consumer.poll(timeout_ms=1000)
    consumer.seek_to_beginning()

stats = Counter()

print("Analytics Service démarré !")
print("En attente des événements Kafka...")

try:
    for message in consumer:
        event = message.value

        if event.get("eventType") == "ProductConsulted":
            product_id = event["productId"]
            stats[product_id] += 1

            print("\n=== ANALYTICS ===")
            for product, views in stats.items():
                print(f"Produit {product} : {views} consultations")

except KeyboardInterrupt:
    print("\nAnalytics arrêté.")

except KafkaError as error:
    print(f"Erreur Kafka : {error}")

finally:
    consumer.close()
