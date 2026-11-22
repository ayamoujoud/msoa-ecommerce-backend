import json
import logging
import os
import uuid

import pika

logger = logging.getLogger("payments.rabbitmq")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
QUEUE_NAME = "shipping_requests"


def publish_shipment_requested(order_id, address: str) -> str:
    """Publie un message ShipmentRequested dans la file shipping_requests.
    Retourne le messageId. Lève une exception si RabbitMQ n'accepte pas le message."""
    message_id = f"msg-{uuid.uuid4()}"
    body = {
        "messageId": message_id,
        "type": "ShipmentRequested",
        "orderId": order_id,
        "address": address,
    }

    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST, port=RABBITMQ_PORT,
        credentials=credentials, heartbeat=30,
    )

    connection = pika.BlockingConnection(params)
    try:
        channel = connection.channel()
        channel.queue_declare(
            queue=QUEUE_NAME, durable=True, exclusive=False, auto_delete=False
        )
        channel.confirm_delivery()  # publisher confirms
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(body),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,  # message persistant
                message_id=message_id,
            ),
            mandatory=True,
        )
        logger.info("ShipmentRequested publié : %s", body)
        return message_id
    finally:
        connection.close()