"""add session_token_hash to activity_sessions for ownership checks

Revision ID: d9b2e6a4f018
Revises: c7a4f1e93b6d
Create Date: 2026-07-21 00:10:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d9b2e6a4f018"
down_revision: Union[str, None] = "c7a4f1e93b6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "activity_sessions",
        sa.Column("session_token_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f("ix_activity_sessions_session_token_hash"),
        "activity_sessions",
        ["session_token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_activity_sessions_session_token_hash"), table_name="activity_sessions"
    )
    op.drop_column("activity_sessions", "session_token_hash")
