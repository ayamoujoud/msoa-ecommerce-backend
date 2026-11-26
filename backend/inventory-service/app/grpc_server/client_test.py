
import grpc

from app.grpc_server import inventory_pb2
from app.grpc_server import inventory_pb2_grpc


def test_check_stock():

    with grpc.insecure_channel("localhost:50051") as channel:

        stub = inventory_pb2_grpc.InventoryServiceStub(channel)

        request = inventory_pb2.StockRequest(
            product_id=1,
            quantity=3
        )

        response = stub.CheckStock(request)

        print("===== REPONSE DU INVENTORY SERVICE =====")
        print("Produit :", request.product_id)
        print("Quantité demandée :", request.quantity)
        print("Disponibilité :", response.available)
        print("Message :", response.message)


if __name__ == "__main__":
    test_check_stock()
