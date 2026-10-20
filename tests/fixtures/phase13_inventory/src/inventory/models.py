"""SQLAlchemy database models for Inventory Management Service."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from inventory.database import Base


class Item(Base):
    """Product catalog item."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)

    stock_levels: Mapped[list["StockLevel"]] = relationship("StockLevel", back_populates="item")


class Warehouse(Base):
    """Storage facility / warehouse."""

    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    stock_levels: Mapped[list["StockLevel"]] = relationship("StockLevel", back_populates="warehouse")


class StockLevel(Base):
    """Current on-hand inventory count for an item in a specific warehouse."""

    __tablename__ = "stock_levels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True, nullable=False)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    item: Mapped["Item"] = relationship("Item", back_populates="stock_levels")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="stock_levels")


class TransferOrder(Base):
    """Inter-warehouse transfer transaction record."""

    __tablename__ = "transfer_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)
    source_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    dest_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="COMPLETED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )


class StockAdjustment(Base):
    """Historical stock balance adjustment audit log."""

    __tablename__ = "stock_adjustments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    adjusted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
