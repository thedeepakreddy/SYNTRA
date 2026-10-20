"""Tests for warehouse transfer operations.

Includes INTENTIONAL FAILING ACCEPTANCE TEST exposing Defect 1 (Overdraft / Negative Stock Bug).
"""

from fastapi.testclient import TestClient


def test_valid_stock_transfer(client: TestClient) -> None:
    """Can transfer stock when sufficient inventory exists."""
    item_id = client.post(
        "/items/", json={"sku": "SKU-TRANS-01", "name": "Transfer Widget", "unit_price": 10.0}
    ).json()["id"]
    wh1_id = client.post("/warehouses/", json={"code": "WH-A", "name": "Warehouse A"}).json()["id"]
    wh2_id = client.post("/warehouses/", json={"code": "WH-B", "name": "Warehouse B"}).json()["id"]

    # Stock WH-A with 20 units
    client.post("/stock/adjust", json={"item_id": item_id, "warehouse_id": wh1_id, "delta": 20})

    # Transfer 5 units from WH-A to WH-B
    resp = client.post(
        "/transfers/",
        json={
            "item_id": item_id,
            "source_warehouse_id": wh1_id,
            "dest_warehouse_id": wh2_id,
            "quantity": 5,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"

    # Verify balances: WH-A has 15, WH-B has 5
    assert client.get(f"/stock/{wh1_id}/{item_id}").json()["quantity"] == 15
    assert client.get(f"/stock/{wh2_id}/{item_id}").json()["quantity"] == 5


def test_transfer_prevents_negative_inventory_overdraft(client: TestClient) -> None:
    """FAILING ACCEPTANCE TEST: Exposes Defect 1.

    When attempting to transfer more items than are currently in stock, the API MUST
    reject the request with HTTP 422 Unprocessable Entity and prevent negative inventory.

    CURRENT DEFECT BEHAVIOR:
    `InventoryService.execute_transfer` checks `if source_stock.quantity <= 0` instead of
    `if source_stock.quantity < quantity`. Because source stock is 3 (> 0), it allows
    the 10-unit transfer to proceed, returning 200 OK and driving source stock to -7!
    """
    item_id = client.post("/items/", json={"sku": "SKU-DEFECT-01", "name": "Defect Item", "unit_price": 5.0}).json()[
        "id"
    ]
    wh1_id = client.post("/warehouses/", json={"code": "WH-SRC", "name": "Source WH"}).json()["id"]
    wh2_id = client.post("/warehouses/", json={"code": "WH-DST", "name": "Dest WH"}).json()["id"]

    # Initialize source warehouse with only 3 units
    client.post("/stock/adjust", json={"item_id": item_id, "warehouse_id": wh1_id, "delta": 3})

    # Attempt to transfer 10 units (7 more than available)
    resp = client.post(
        "/transfers/",
        json={
            "item_id": item_id,
            "source_warehouse_id": wh1_id,
            "dest_warehouse_id": wh2_id,
            "quantity": 10,
        },
    )

    # Acceptance assertion: Overdraft must be rejected
    assert resp.status_code == 422, (
        f"Expected HTTP 422 rejection for overdraft transfer, but got {resp.status_code} "
        f"with payload {resp.text}. Warehouse inventory was permitted to go negative!"
    )
    assert "Insufficient stock" in resp.json()["detail"]

    # Source stock must remain 3, dest stock must remain 0
    assert client.get(f"/stock/{wh1_id}/{item_id}").json()["quantity"] == 3
    assert client.get(f"/stock/{wh2_id}/{item_id}").json()["quantity"] == 0
