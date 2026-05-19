"""create core domain tables

Revision ID: 20260515_0001
Revises: None
Create Date: 2026-05-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260515_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = postgresql.ENUM("admin", "doctor", "user", name="user_role", create_type=False)
user_status = postgresql.ENUM("active", "inactive", "suspended", name="user_status", create_type=False)
doctor_verification_status = postgresql.ENUM(
    "pending",
    "verified",
    "rejected",
    name="doctor_verification_status",
    create_type=False,
)
uploaded_file_status = postgresql.ENUM(
    "pending",
    "stored",
    "processing",
    "processed",
    "failed",
    "deleted",
    name="uploaded_file_status",
    create_type=False,
)
prediction_status = postgresql.ENUM(
    "pending",
    "processing",
    "completed",
    "failed",
    "cancelled",
    name="prediction_status",
    create_type=False,
)
prediction_log_event = postgresql.ENUM(
    "created",
    "status_changed",
    "model_invoked",
    "completed",
    "failed",
    name="prediction_log_event",
    create_type=False,
)
notification_status = postgresql.ENUM(
    "unread",
    "read",
    "archived",
    name="notification_status",
    create_type=False,
)
notification_type = postgresql.ENUM(
    "system",
    "prediction_completed",
    "prediction_failed",
    name="notification_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    op.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
    op.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "citext"'))
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION set_updated_at()
            RETURNS trigger AS $$
            BEGIN
                NEW.updated_at = now();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
    )

    user_role.create(bind, checkfirst=True)
    user_status.create(bind, checkfirst=True)
    doctor_verification_status.create(bind, checkfirst=True)
    uploaded_file_status.create(bind, checkfirst=True)
    prediction_status.create(bind, checkfirst=True)
    prediction_log_event.create(bind, checkfirst=True)
    notification_status.create(bind, checkfirst=True)
    notification_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, server_default="user", nullable=False),
        sa.Column("status", user_status, server_default="active", nullable=False),
        sa.Column("is_email_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_created_at", "users", ["created_at"])
    op.create_index("ix_users_role_status", "users", ["role", "status"])
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at()
            """
        )
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_token_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_refresh_tokens_updated_at
            BEFORE UPDATE ON refresh_tokens
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at()
            """
        )
    )

    op.create_table(
        "doctor_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("license_number", sa.String(length=100), nullable=False),
        sa.Column("specialization", sa.String(length=150), nullable=False),
        sa.Column("clinic_name", sa.String(length=255), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("verification_status", doctor_verification_status, server_default="pending", nullable=False),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("license_number"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_doctor_profiles_specialization", "doctor_profiles", ["specialization"])
    op.create_index("ix_doctor_profiles_verification_status", "doctor_profiles", ["verification_status"])
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_doctor_profiles_updated_at
            BEFORE UPDATE ON doctor_profiles
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at()
            """
        )
    )

    op.create_table(
        "uploaded_files",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("status", uploaded_file_status, server_default="pending", nullable=False),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_uploaded_files_checksum", "uploaded_files", ["checksum_sha256"])
    op.create_index("ix_uploaded_files_created_at", "uploaded_files", ["created_at"])
    op.create_index("ix_uploaded_files_owner_status", "uploaded_files", ["owner_id", "status"])
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_uploaded_files_updated_at
            BEFORE UPDATE ON uploaded_files
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at()
            """
        )
    )

    op.create_table(
        "predictions",
        sa.Column("requested_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", prediction_status, server_default="pending", nullable=False),
        sa.Column("model_name", sa.String(length=150), nullable=True),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column("predicted_label", sa.String(length=255), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=6, scale=5), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["doctor_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_file_id"], ["uploaded_files.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predictions_created_at", "predictions", ["created_at"])
    op.create_index("ix_predictions_requested_by_status", "predictions", ["requested_by_id", "status"])
    op.create_index("ix_predictions_reviewed_by", "predictions", ["reviewed_by_id"])
    op.create_index("ix_predictions_uploaded_file", "predictions", ["uploaded_file_id"])
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_predictions_updated_at
            BEFORE UPDATE ON predictions
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at()
            """
        )
    )

    op.create_table(
        "prediction_logs",
        sa.Column("prediction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event", prediction_log_event, nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prediction_logs_event", "prediction_logs", ["event"])
    op.create_index(
        "ix_prediction_logs_prediction_created_at",
        "prediction_logs",
        ["prediction_id", "created_at"],
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_prediction_logs_updated_at
            BEFORE UPDATE ON prediction_logs
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at()
            """
        )
    )

    op.create_table(
        "notifications",
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", notification_type, server_default="system", nullable=False),
        sa.Column("status", notification_status, server_default="unread", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
    op.create_index("ix_notifications_recipient_status", "notifications", ["recipient_id", "status"])
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_notifications_updated_at
            BEFORE UPDATE ON notifications
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at()
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_notifications_type", table_name="notifications")
    op.drop_index("ix_notifications_recipient_status", table_name="notifications")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_prediction_logs_prediction_created_at", table_name="prediction_logs")
    op.drop_index("ix_prediction_logs_event", table_name="prediction_logs")
    op.drop_table("prediction_logs")

    op.drop_index("ix_predictions_uploaded_file", table_name="predictions")
    op.drop_index("ix_predictions_reviewed_by", table_name="predictions")
    op.drop_index("ix_predictions_requested_by_status", table_name="predictions")
    op.drop_index("ix_predictions_created_at", table_name="predictions")
    op.drop_table("predictions")

    op.drop_index("ix_uploaded_files_owner_status", table_name="uploaded_files")
    op.drop_index("ix_uploaded_files_created_at", table_name="uploaded_files")
    op.drop_index("ix_uploaded_files_checksum", table_name="uploaded_files")
    op.drop_table("uploaded_files")

    op.drop_index("ix_doctor_profiles_verification_status", table_name="doctor_profiles")
    op.drop_index("ix_doctor_profiles_specialization", table_name="doctor_profiles")
    op.drop_table("doctor_profiles")

    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index("ix_users_role_status", table_name="users")
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_table("users")

    op.execute(sa.text("DROP FUNCTION IF EXISTS set_updated_at()"))

    notification_type.drop(bind, checkfirst=True)
    notification_status.drop(bind, checkfirst=True)
    prediction_log_event.drop(bind, checkfirst=True)
    prediction_status.drop(bind, checkfirst=True)
    uploaded_file_status.drop(bind, checkfirst=True)
    doctor_verification_status.drop(bind, checkfirst=True)
    user_status.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
