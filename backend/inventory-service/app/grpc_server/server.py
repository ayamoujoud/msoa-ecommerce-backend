
from concurrent import futures
import grpc

from app.database import SessionLocal
from app.models import Inventory

from app.grpc_server import inventory_pb2
from app.grpc_server import inventory_pb2_grpc


class InventoryServicer(inventory_pb2_grpc.InventoryServiceServicer):

    def CheckStock(self, request, context):

        db = SessionLocal()

        try:
            inventory = db.query(Inventory).filter(
                Inventory.product_id == request.product_id
            ).first()

            if not inventory:
                return inventory_pb2.StockResponse(
                    available=False,
                    message="Product inventory not found"
                )

            if inventory.quantity_available < request.quantity:
                return inventory_pb2.StockResponse(
                    available=False,
                    message="Insufficient stock"
                )

            return inventory_pb2.StockResponse(
                available=True,
                message="Stock available"
            )

        finally:
            db.close()


def serve():

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )

    inventory_pb2_grpc.add_InventoryServiceServicer_to_server(
        InventoryServicer(),
        server
    )

    server.add_insecure_port("[::]:50051")

    server.start()

    print("Inventory gRPC server running on port 50051")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
