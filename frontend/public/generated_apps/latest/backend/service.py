"""Domain Business Service Layer for Autonomous.

Encapsulates all database operations, filters, validations, and statistical aggregations.
"""

from __future__ import annotations

from typing import Sequence
from sqlalchemy import delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AutonomousModel
from .schemas import AutonomousCreate, AutonomousUpdate, FilterParams


class AutonomousService:
    """Core domain business logic service."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_items(self, filters: FilterParams) -> Sequence[AutonomousModel]:
        stmt = select(AutonomousModel)
        if filters.category:
            stmt = stmt.where(AutonomousModel.category == filters.category)
        if filters.status:
            stmt = stmt.where(AutonomousModel.status == filters.status)
        if filters.priority:
            stmt = stmt.where(AutonomousModel.priority == filters.priority)
        if filters.q:
            kw = f"%{filters.q}%"
            stmt = stmt.where(
                or_(
                    AutonomousModel.title.ilike(kw),
                    AutonomousModel.description.ilike(kw),
                    AutonomousModel.tags_csv.ilike(kw),
                )
            )
        stmt = stmt.order_by(desc(AutonomousModel.created_at)).offset(filters.offset).limit(filters.limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, item_id: str) -> AutonomousModel | None:
        stmt = select(AutonomousModel).where(AutonomousModel.id == item_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_item(self, payload: AutonomousCreate) -> AutonomousModel:
        record = AutonomousModel(
            title=payload.title,
            category=payload.category,
            status=payload.status,
            priority=payload.priority,
            description=payload.description or "",
            tags_csv=",".join(payload.tags),
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def update_item(self, item_id: str, payload: AutonomousUpdate) -> AutonomousModel | None:
        item = await self.get_by_id(item_id)
        if not item:
            return None
        if payload.title is not None:
            item.title = payload.title
        if payload.category is not None:
            item.category = payload.category
        if payload.status is not None:
            item.status = payload.status
        if payload.priority is not None:
            item.priority = payload.priority
        if payload.description is not None:
            item.description = payload.description
        if payload.tags is not None:
            item.tags_csv = ",".join(payload.tags)
        await self.session.flush()
        return item

    async def delete_item(self, item_id: str) -> bool:
        item = await self.get_by_id(item_id)
        if not item:
            return False
        await self.session.delete(item)
        await self.session.flush()
        return True

    async def get_stats(self) -> dict:
        stmt = select(AutonomousModel)
        result = await self.session.execute(stmt)
        items = result.scalars().all()

        by_category: dict[str, int] = {}
        by_status: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        active_count = 0
        completed_count = 0

        for it in items:
            by_category[it.category] = by_category.get(it.category, 0) + 1
            by_status[it.status] = by_status.get(it.status, 0) + 1
            by_priority[it.priority] = by_priority.get(it.priority, 0) + 1
            if it.status in ["DONE", "RESOLVED", "COMPLETED"]:
                completed_count += 1
            else:
                active_count += 1

        return {
            "total_records": len(items),
            "active_count": active_count,
            "completed_count": completed_count,
            "by_category": by_category,
            "by_status": by_status,
            "by_priority": by_priority,
        }
