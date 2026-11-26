import os

import grpc

import inventory_pb2
import inventory_pb2_grpc

INVENTORY_GRPC_ADDR = os.getenv("INVENTORY_GRPC_ADDR", "localhost:50051")
TIMEOUT_SECONDS = 5


class InventoryUnavailable(Exception):
    """Inventory ne répond pas (arrêté ou trop lent) -> HTTP 503."""


class InventoryError(Exception):
    """Inventory a répondu avec une erreur inattendue -> HTTP 502."""


# Un seul canal pour tout le service : la connexion HTTP/2 reste ouverte et est réutilisée
_channel = grpc.insecure_channel(INVENTORY_GRPC_ADDR)
_stub = inventory_pb2_grpc.InventoryServiceStub(_channel)


def call(action: str, items: list) -> bool:
    """action = 'check' | 'reserve' | 'release'. items = [{"productId": 1, "quantity": 2}, ...]"""
    request = inventory_pb2.ItemsRequest(
        items=[
            inventory_pb2.Item(product_id=i["productId"], quantity=i["quantity"])
            for i in items
        ]
    )
    try:
        if action == "check":
            return _stub.Check(request, timeout=TIMEOUT_SECONDS).available
        if action == "reserve":
            return _stub.Reserve(request, timeout=TIMEOUT_SECONDS).success
        if action == "release":
            return _stub.Release(request, timeout=TIMEOUT_SECONDS).success
        raise ValueError(f"Action inconnue : {action}")
    except grpc.RpcError as e:
        if e.code() in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED):
            raise InventoryUnavailable(e.code().name) from e
        raise InventoryError(e.code().name) from e
