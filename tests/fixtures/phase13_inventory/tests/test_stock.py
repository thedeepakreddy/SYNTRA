"""Tests for stock ledger and adjustment queries.

Includes INTENTIONAL FAILING ACCEPTANCE TEST exposing Defect 2 (Timezone Offset Comparison Bug).
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def test_stock_adjustment_history_naive_filter(client: TestClient) -> None:
    """Baseline: Can query stock adjustments using naive timestamps."""
    item_id = client.post("/items/", json={"sku": "SKU-HIST-01", "name": "History Item", "unit_price": 12.0}).json()[
        "id"
    ]
    wh_id = client.post("/warehouses/", json={"code": "WH-HIST", "name": "History WH"}).json()["id"]

    # Make adjustments
    client.post("/stock/adjust", json={"item_id": item_id, "warehouse_id": wh_id, "delta": 10})
    client.post("/stock/adjust", json={"item_id": item_id, "warehouse_id": wh_id, "delta": -2})

    # Query with naive timestamp (from 1 hour ago)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None)
    resp = client.get(f"/stock/{wh_id}/ledger?from_time={past.isoformat()}")
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) >= 2


def test_stock_ledger_timezone_consistency(client: TestClient) -> None:
    """FAILING ACCEPTANCE TEST: Exposes Defect 2.

    When querying the stock ledger with standard ISO 8601 timezone-aware timestamps
    (e.g. UTC 'Z' or '+00:00'), the API MUST correctly parse the timezone, normalize
    comparisons, and return HTTP 200 OK with the history records.

    CURRENT DEFECT BEHAVIOR:
    `InventoryService.query_stock_history` compares naive database timestamps with
    offset-aware query parameter `from_time` directly without normalization. Python
    raises `TypeError: can't compare offset-naive and offset-aware datetimes`, causing
    the endpoint to crash with HTTP 500!
    """
    item_id = client.post("/items/", json={"sku": "SKU-TZ-01", "name": "Timezone Item", "unit_price": 15.0}).json()[
        "id"
    ]
    wh_id = client.post("/warehouses/", json={"code": "WH-TZ", "name": "Timezone WH"}).json()["id"]

    # Make adjustments
    client.post("/stock/adjust", json={"item_id": item_id, "warehouse_id": wh_id, "delta": 25})

    # Query using standard ISO 8601 timezone-aware UTC timestamp (Z format)
    utc_from = datetime.now(timezone.utc) - timedelta(hours=2)
    resp = client.get(f"/stock/{wh_id}/ledger?from_time={utc_from.strftime('%Y-%m-%dT%H:%M:%SZ')}")

    # Acceptance assertion: Must succeed with 200 and return historical adjustments
    assert resp.status_code == 200, (
        f"Expected HTTP 200 for timezone-aware ledger query, but got {resp.status_code} with payload: {resp.text}"
    )
    records = resp.json()
    assert len(records) >= 1
    assert records[0]["delta"] == 25
