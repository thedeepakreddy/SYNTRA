"""Initial incomplete fixture suite; it deliberately omits quantity zero."""

from app import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_positive_order():
    assert client.post("/orders", json={"quantity": 2}).json() == {"quantity": 2}


def test_negative_order():
    assert client.post("/orders", json={"quantity": -1}).status_code == 422
