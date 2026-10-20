"""Baseline tests for item and warehouse catalog operations (PASSING)."""

from fastapi.testclient import TestClient


def test_create_and_get_item(client: TestClient) -> None:
    """Baseline: Can successfully create an item and verify its attributes."""
    resp = client.post("/items/", json={"sku": "SKU-WIDGET-01", "name": "Standard Widget", "unit_price": 19.99})
    assert resp.status_code == 201
    data = resp.json()
    assert data["sku"] == "SKU-WIDGET-01"
    assert data["name"] == "Standard Widget"
    assert data["unit_price"] == 19.99
    assert data["id"] > 0


def test_duplicate_sku_rejected(client: TestClient) -> None:
    """Baseline: Creating duplicate SKU is rejected with 400."""
    resp1 = client.post("/items/", json={"sku": "SKU-DUP-01", "name": "Item A", "unit_price": 5.0})
    assert resp1.status_code == 201

    resp2 = client.post("/items/", json={"sku": "SKU-DUP-01", "name": "Item B", "unit_price": 7.0})
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]


def test_create_warehouse_and_adjust_stock(client: TestClient) -> None:
    """Baseline: Can create warehouses and adjust initial stock levels."""
    wh_resp = client.post("/warehouses/", json={"code": "WH-NORTH", "name": "North Warehouse"})
    assert wh_resp.status_code == 201
    wh_id = wh_resp.json()["id"]

    item_resp = client.post("/items/", json={"sku": "SKU-STOCK-01", "name": "Stock Item", "unit_price": 10.0})
    item_id = item_resp.json()["id"]

    # Adjust stock +50
    adj_resp = client.post("/stock/adjust", json={"item_id": item_id, "warehouse_id": wh_id, "delta": 50})
    assert adj_resp.status_code == 200
    assert adj_resp.json()["quantity"] == 50

    # Query current stock
    stock_resp = client.get(f"/stock/{wh_id}/{item_id}")
    assert stock_resp.status_code == 200
    assert stock_resp.json()["quantity"] == 50
