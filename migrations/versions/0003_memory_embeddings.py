"""Add optional embedding vector column to memory_records for semantic retrieval.

Revision ID: 0003_memory_embeddings
Revises: 0002_mcp_infrastructure
Create Date: 2026-10-20 00:17:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003_memory_embeddings"
down_revision: Union[str, None] = "0002_mcp_infrastructure"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add nullable embedding column compatible with SQLite (JSON) and PostgreSQL (JSONB)
    embedding_type = sa.JSON().with_variant(JSONB(), "postgresql")
    op.add_column(
        "memory_records",
        sa.Column("embedding", embedding_type, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("memory_records", "embedding")
