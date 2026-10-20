"""FastAPI HTTP interface for Inventory Management Service."""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from inventory.database import get_db, init_db
from inventory.service import InventoryService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on application launch."""
    init_db()
    yield


app = FastAPI(title="Inventory Management Service", version="0.1.0", lifespan=lifespan)


# ------------------------------------------------------------------------------
# Request & Response Schemas
# ------------------------------------------------------------------------------
class ItemCreate(BaseModel):
    sku: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    unit_price: float = Field(default=0.0, ge=0.0)


class ItemResponse(BaseModel):
    id: int
    sku: str
    name: str
    unit_price: float


class WarehouseCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=255)


class WarehouseResponse(BaseModel):
    id: int
    code: str
    name: str


class StockAdjustmentRequest(BaseModel):
    item_id: int
    warehouse_id: int
    delta: int


class StockLevelResponse(BaseModel):
    item_id: int
    warehouse_id: int
    quantity: int


class TransferRequest(BaseModel):
    item_id: int
    source_warehouse_id: int
    dest_warehouse_id: int
    quantity: int = Field(..., gt=0)


class TransferResponse(BaseModel):
    id: int
    item_id: int
    source_warehouse_id: int
    dest_warehouse_id: int
    quantity: int
    status: str


class StockAdjustmentResponse(BaseModel):
    id: int
    item_id: int
    warehouse_id: int
    delta: int
    adjusted_at: datetime


# ------------------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------------------
@app.post("/items/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, db: Annotated[Session, Depends(get_db)]) -> ItemResponse:
    try:
        item = InventoryService.create_item(db, sku=payload.sku, name=payload.name, unit_price=payload.unit_price)
        return ItemResponse(id=item.id, sku=item.sku, name=item.name, unit_price=item.unit_price)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/warehouses/", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def create_warehouse(payload: WarehouseCreate, db: Annotated[Session, Depends(get_db)]) -> WarehouseResponse:
    try:
        wh = InventoryService.create_warehouse(db, code=payload.code, name=payload.name)
        return WarehouseResponse(id=wh.id, code=wh.code, name=wh.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/stock/adjust", response_model=StockLevelResponse)
def adjust_stock(payload: StockAdjustmentRequest, db: Annotated[Session, Depends(get_db)]) -> StockLevelResponse:
    stock = InventoryService.adjust_stock(
        db,
        item_id=payload.item_id,
        warehouse_id=payload.warehouse_id,
        delta=payload.delta,
    )
    return StockLevelResponse(item_id=stock.item_id, warehouse_id=stock.warehouse_id, quantity=stock.quantity)


@app.post("/transfers/", response_model=TransferResponse)
def create_transfer(payload: TransferRequest, db: Annotated[Session, Depends(get_db)]) -> TransferResponse:
    try:
        transfer = InventoryService.execute_transfer(
            db,
            item_id=payload.item_id,
            source_warehouse_id=payload.source_warehouse_id,
            dest_warehouse_id=payload.dest_warehouse_id,
            quantity=payload.quantity,
        )
        return TransferResponse(
            id=transfer.id,
            item_id=transfer.item_id,
            source_warehouse_id=transfer.source_warehouse_id,
            dest_warehouse_id=transfer.dest_warehouse_id,
            quantity=transfer.quantity,
            status=transfer.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@app.get("/stock/{warehouse_id}/ledger", response_model=list[StockAdjustmentResponse])
def get_stock_ledger(
    warehouse_id: int,
    from_time: Annotated[datetime, Query()],
    to_time: Annotated[datetime | None, Query()] = None,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
) -> list[StockAdjustmentResponse]:
    try:
        history = InventoryService.query_stock_history(
            db,
            warehouse_id=warehouse_id,
            from_time=from_time,
            to_time=to_time,
        )
        return [
            StockAdjustmentResponse(
                id=a.id,
                item_id=a.item_id,
                warehouse_id=a.warehouse_id,
                delta=a.delta,
                adjusted_at=a.adjusted_at,
            )
            for a in history
        ]
    except TypeError as exc:
        # Runtime crash from timezone comparison defect
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Timezone comparison error in stock ledger: offset-naive vs offset-aware mismatch",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@app.get("/stock/{warehouse_id}/{item_id}", response_model=StockLevelResponse)
def get_stock(warehouse_id: int, item_id: int, db: Annotated[Session, Depends(get_db)]) -> StockLevelResponse:
    qty = InventoryService.get_stock(db, item_id=item_id, warehouse_id=warehouse_id)
    return StockLevelResponse(item_id=item_id, warehouse_id=warehouse_id, quantity=qty)
