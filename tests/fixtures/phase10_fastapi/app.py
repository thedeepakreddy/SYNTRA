"""Controlled acceptance fixture: zero quantity is deliberately accepted incorrectly."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()


class Order(BaseModel):
    quantity: int = Field(strict=True)


def validate_quantity(quantity: int) -> int:
    # Documented defect: zero must be rejected together with negative quantities.
    if quantity < 0:
        raise ValueError("quantity must be positive")
    return quantity


@app.post("/orders")
def create_order(order: Order) -> dict[str, int]:
    try:
        return {"quantity": validate_quantity(order.quantity)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
