
import json
import logging
import os
#import time
import pika

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .database import SessionLocal
from .models import Shipment


# ==========================================
# CONFIGURATION LOGGING
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("shipping.rabbitmq")


# ==========================================
# CONFIGURATION RABBITMQ
# ==========================================

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))

RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

QUEUE_NAME = "shipping_requests"


# ==========================================
# EXTRACTION DES INFORMATIONS DE L'ADRESSE
# ==========================================

def extract_address(address):
    """
    Le Producer transmet une adresse sous forme de chaîne :
    'Casablanca, Morocco'

    Notre modèle SQLAlchemy attend :
    name, address, city.
    """

    if not isinstance(address, str) or not address.strip():
        raise ValueError("Invalid shipment address")

    address = address.strip()
    parts = [part.strip() for part in address.split(",")]

    city = parts[0] if parts else address

    return {
        "name": "Client",
        "address": address,
        "city": city
    }


# ==========================================
# TRAITEMENT DU MESSAGE
# ==========================================

def process_shipment_message(body):
    """
    Désérialise et valide le message reçu,
    puis crée une expédition dans SQLite.
    """

    message = json.loads(body.decode("utf-8"))

    # Vérification du type de message
    if message.get("type") != "ShipmentRequested":
        raise ValueError("Unsupported message type")

    # Vérification des données obligatoires
    order_id = message.get("orderId")
    address = message.get("address")

    if order_id is None or str(order_id).strip() == "":
        raise ValueError("Missing orderId")

    order_id = str(order_id).strip()

    address_data = extract_address(address)

    db = SessionLocal()

    try:
        # Vérifier si une expédition existe déjà
        existing = db.query(Shipment).filter(
            Shipment.orderId == order_id
        ).first()

        if existing:
            logger.info(
                "Shipment already exists for order %s. "
                "Duplicate message ignored.",
                order_id
            )

            # Idempotence : le message peut être acquitté
            return

        # Créer une nouvelle expédition
        import uuid

        shipment = Shipment(
            id=str(uuid.uuid4()),
            orderId=order_id,
            name=address_data["name"],
            address=address_data["address"],
            city=address_data["city"],
            trackingNumber=f"MSOA-{uuid.uuid4().hex[:8].upper()}",
            status="PREPARING"
        )

        db.add(shipment)

        # Enregistrer dans SQLite
        db.commit()

        logger.info(
            "Shipment successfully created!"
        )
        logger.info("Order ID: %s", shipment.orderId)
        logger.info("Tracking Number: %s", shipment.trackingNumber)

    except IntegrityError:
        db.rollback()

        # Une autre livraison a pu créer l'expédition
        # entre la vérification et l'insertion.
        existing = db.query(Shipment).filter(
            Shipment.orderId == order_id
        ).first()

        if existing:
            logger.info(
                "Duplicate order %s detected. Ignoring.",
                order_id
            )
            return

        raise

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ==========================================
# CALLBACK DU CONSUMER
# ==========================================

def callback(ch, method, properties, body):

    message_id = getattr(properties, "message_id", None)

    logger.info(
        "Message received from RabbitMQ: %s",
        message_id
    )

    try:
        # Traiter le message
        process_shipment_message(body)

         # PAUSE TEMPORAIRE POUR SIMULER UNE PANNE AVANT ACK
        #logger.warning("TEST : pause avant ACK pendant 15 secondes...")
        #time.sleep(15)
        
        # ACK seulement après le traitement réussi
        ch.basic_ack(
            delivery_tag=method.delivery_tag
        )

        logger.info(
            "Message acknowledged successfully: %s",
            message_id
        )

    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:

        logger.error(
            "Invalid message: %s",
            error
        )

        # Message invalide : ne pas le remettre en boucle
        ch.basic_reject(
            delivery_tag=method.delivery_tag,
            requeue=False
        )

    except Exception as error:

        logger.exception(
            "Shipment processing failed: %s",
            error
        )

        # Erreur technique : demander une nouvelle livraison
        ch.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=True
        )


# ==========================================
# CONNEXION ET CONSOMMATION
# ==========================================

def start_consumer():

    credentials = pika.PlainCredentials(
        RABBITMQ_USER,
        RABBITMQ_PASS
    )

    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=30,
        connection_attempts=3,
        retry_delay=5
    )

    connection = None

    try:

        logger.info("Connecting to RabbitMQ...")

        connection = pika.BlockingConnection(parameters)

        channel = connection.channel()

        # Déclarer la même queue que le Producer
        channel.queue_declare(
            queue=QUEUE_NAME,
            durable=True,
            exclusive=False,
            auto_delete=False
        )

        # Limiter les messages non acquittés
        channel.basic_qos(
            prefetch_count=1
        )

        # Consumer avec ACK manuel
        channel.basic_consume(
            queue=QUEUE_NAME,
            on_message_callback=callback,
            auto_ack=False
        )

        logger.info("Connected to RabbitMQ successfully!")
        logger.info("Waiting for messages in: %s", QUEUE_NAME)

        channel.start_consuming()

    except KeyboardInterrupt:

        logger.info("Consumer stopped by user.")

    except Exception:

        logger.exception("RabbitMQ consumer error.")

        raise

    finally:

        if connection is not None and connection.is_open:
            connection.close()

        logger.info("RabbitMQ connection closed.")


# ==========================================
# EXECUTION
# ==========================================

if __name__ == "__main__":
    start_consumer()
