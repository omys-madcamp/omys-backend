"""store participant token as sha256 hash instead of plaintext

Revision ID: c7a4f1e93b6d
Revises: b4d2c701a9ef
Create Date: 2026-07-21 00:00:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c7a4f1e93b6d"
down_revision: Union[str, None] = "b4d2c701a9ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_participant_room_token", "participants", type_="unique")
    op.drop_index(op.f("ix_participants_participant_token"), table_name="participants")
    op.alter_column("participants", "participant_token", new_column_name="token_hash")
    op.create_index(
        op.f("ix_participants_token_hash"), "participants", ["token_hash"], unique=True
    )
    op.create_unique_constraint(
        "uq_participant_room_token", "participants", ["room_id", "token_hash"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_participant_room_token", "participants", type_="unique")
    op.drop_index(op.f("ix_participants_token_hash"), table_name="participants")
    op.alter_column("participants", "token_hash", new_column_name="participant_token")
    op.create_index(
        op.f("ix_participants_participant_token"),
        "participants",
        ["participant_token"],
        unique=True,
    )
    op.create_unique_constraint(
        "uq_participant_room_token", "participants", ["room_id", "participant_token"]
    )
