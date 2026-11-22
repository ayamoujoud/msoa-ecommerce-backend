from rabbitmq_publisher import publish_shipment_requested

message_id = publish_shipment_requested(order_id=101, address="Casablanca, Morocco")
print("Message publié :", message_id)
