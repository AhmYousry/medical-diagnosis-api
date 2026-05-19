"""add email_tokens table

Revision ID: 20260520_0001
Revises: 00814c2093b5
Create Date: 2026-05-20 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260520_0001"
down_revision = "00814c2093b5"
branch_labels = None
depends_on = None

_email_token_type = sa.Enum(
    "email_verification",
    "password_reset",
    name="email_token_type",
)


def upgrade() -> None:
    _email_token_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "email_tokens",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("token_type", _email_token_type, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_tokens_token_hash", "email_tokens", ["token_hash"], unique=True)
    op.create_index("ix_email_tokens_user_id_type", "email_tokens", ["user_id", "token_type"])


def downgrade() -> None:
    op.drop_index("ix_email_tokens_user_id_type", table_name="email_tokens")
    op.drop_index("ix_email_tokens_token_hash", table_name="email_tokens")
    op.drop_table("email_tokens")
    _email_token_type.drop(op.get_bind(), checkfirst=True)
