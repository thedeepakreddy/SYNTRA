"""Business logic and operations for Inventory Management Service."""

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from inventory.models import Item, StockAdjustment, StockLevel, TransferOrder, Warehouse


class InventoryService:
    """Core domain service for catalog, warehouse transfers, and stock ledgers."""

    @staticmethod
    def create_item(db: Session, sku: str, name: str, unit_price: float = 0.0) -> Item:
        """Create a new catalog item."""
        existing = db.scalar(select(Item).where(Item.sku == sku))
        if existing:
            raise ValueError(f"Item with SKU '{sku}' already exists")
        item = Item(sku=sku, name=name, unit_price=unit_price)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def create_warehouse(db: Session, code: str, name: str) -> Warehouse:
        """Create a new storage warehouse."""
        existing = db.scalar(select(Warehouse).where(Warehouse.code == code))
        if existing:
            raise ValueError(f"Warehouse with code '{code}' already exists")
        wh = Warehouse(code=code, name=name)
        db.add(wh)
        db.commit()
        db.refresh(wh)
        return wh

    @staticmethod
    def adjust_stock(db: Session, item_id: int, warehouse_id: int, delta: int) -> StockLevel:
        """Adjust stock level for an item in a warehouse."""
        stock = db.scalar(
            select(StockLevel).where(
                StockLevel.item_id == item_id,
                StockLevel.warehouse_id == warehouse_id,
            )
        )
        if not stock:
            stock = StockLevel(item_id=item_id, warehouse_id=warehouse_id, quantity=0)
            db.add(stock)

        stock.quantity += delta
        adj = StockAdjustment(
            item_id=item_id,
            warehouse_id=warehouse_id,
            delta=delta,
            adjusted_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(adj)
        db.commit()
        db.refresh(stock)
        return stock

    @staticmethod
    def get_stock(db: Session, item_id: int, warehouse_id: int) -> int:
        """Get current on-hand stock for an item in a warehouse."""
        stock = db.scalar(
            select(StockLevel).where(
                StockLevel.item_id == item_id,
                StockLevel.warehouse_id == warehouse_id,
            )
        )
        return stock.quantity if stock else 0

    @staticmethod
    def execute_transfer(
        db: Session,
        item_id: int,
        source_warehouse_id: int,
        dest_warehouse_id: int,
        quantity: int,
    ) -> TransferOrder:
        """Transfer stock between two warehouses.

        NOTE ON INTENTIONAL DEFECT 1:
        The logic below deliberately checks `source_stock.quantity <= 0` instead of
        `source_stock.quantity < quantity`. If a warehouse has 3 units and a transfer
        requests 10 units, it erroneously proceeds and causes stock to become -7.
        """
        if quantity <= 0:
            raise ValueError("Transfer quantity must be strictly positive")
        if source_warehouse_id == dest_warehouse_id:
            raise ValueError("Source and destination warehouses must be different")

        source_stock = db.scalar(
            select(StockLevel).where(
                StockLevel.item_id == item_id,
                StockLevel.warehouse_id == source_warehouse_id,
            )
        )
        if not source_stock:
            raise ValueError(f"No stock record found for item {item_id} in warehouse {source_warehouse_id}")

        # --- INTENTIONAL DEFECT 1 ---
        # Bug: Checks `<= 0` instead of `< quantity`.
        # Overdrafts are incorrectly permitted when quantity > source_stock.quantity > 0.
        if source_stock.quantity <= 0:
            raise ValueError(f"Insufficient stock for item {item_id} in warehouse {source_warehouse_id}")

        dest_stock = db.scalar(
            select(StockLevel).where(
                StockLevel.item_id == item_id,
                StockLevel.warehouse_id == dest_warehouse_id,
            )
        )
        if not dest_stock:
            dest_stock = StockLevel(item_id=item_id, warehouse_id=dest_warehouse_id, quantity=0)
            db.add(dest_stock)

        source_stock.quantity -= quantity
        dest_stock.quantity += quantity

        transfer = TransferOrder(
            item_id=item_id,
            source_warehouse_id=source_warehouse_id,
            dest_warehouse_id=dest_warehouse_id,
            quantity=quantity,
            status="COMPLETED",
        )
        db.add(transfer)
        db.commit()
        db.refresh(transfer)
        return transfer

    @staticmethod
    def query_stock_history(
        db: Session,
        warehouse_id: int,
        from_time: datetime,
        to_time: datetime | None = None,
    ) -> Sequence[StockAdjustment]:
        """Query historical stock adjustments for a warehouse within a time range.

        NOTE ON INTENTIONAL DEFECT 2:
        Compares naive database timestamp `adj.adjusted_at` directly with timezone-aware
        parameter `from_time` without normalizing timezones. When callers pass ISO
        timezone-aware timestamps (e.g. UTC), Python raises a runtime TypeError.
        """
        query = select(StockAdjustment).where(StockAdjustment.warehouse_id == warehouse_id)
        results = db.scalars(query).all()

        filtered: list[StockAdjustment] = []
        for adj in results:
            # --- INTENTIONAL DEFECT 2 ---
            # Bug: Direct comparison between offset-naive (adj.adjusted_at) and offset-aware (from_time)
            # causes `TypeError: can't compare offset-naive and offset-aware datetimes`.
            if adj.adjusted_at < from_time:
                continue
            if to_time is not None and adj.adjusted_at > to_time:
                continue
            filtered.append(adj)

        return filtered
