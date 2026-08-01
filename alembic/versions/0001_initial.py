"""Initial migration - create all tables.

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("user_id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), server_default=""),
        sa.Column("role", sa.String(50), server_default="user"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("api_keys", sa.JSON, server_default="[]"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime, nullable=True),
        sa.Column("preferences", sa.JSON, server_default="{}"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "chat_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("conversation_id", sa.String(36)),
        sa.Column("role", sa.String(20)),
        sa.Column("content", sa.Text),
        sa.Column("agent_id", sa.String(20), nullable=True),
        sa.Column("specialization", sa.String(100), nullable=True),
        sa.Column("model", sa.String(50), nullable=True),
        sa.Column("verdict_type", sa.String(50), nullable=True),
        sa.Column("verdict_score", sa.Float, nullable=True),
        sa.Column("rag_sources", sa.JSON, server_default="[]"),
        sa.Column("latency_ms", sa.Float, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_chat_conversation_id", "chat_history", ["conversation_id"])
    op.create_index("ix_chat_created_at", "chat_history", ["created_at"])

    op.create_table(
        "rag_documents",
        sa.Column("doc_id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("doc_type", sa.String(50)),
        sa.Column("jurisdiction", sa.String(100), server_default="India"),
        sa.Column("source", sa.String(500), server_default=""),
        sa.Column("content", sa.Text),
        sa.Column("metadata", sa.JSON, server_default="{}"),
        sa.Column("embedding_status", sa.String(20), server_default="pending"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "rag_document_chunks",
        sa.Column("chunk_id", sa.String(128), primary_key=True),
        sa.Column("doc_id", sa.String(64), sa.ForeignKey("rag_documents.doc_id")),
        sa.Column("content", sa.Text),
        sa.Column("chunk_index", sa.Integer, server_default="0"),
        sa.Column("metadata", sa.JSON, server_default="{}"),
        sa.Column("embedding", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_doc_chunks_doc_id", "rag_document_chunks", ["doc_id"])
    op.execute("ALTER TABLE rag_document_chunks ADD COLUMN IF NOT EXISTS embedding_vector vector(1536)")

    op.create_table("compliance_scans", sa.Column("scan_id", sa.String(36), primary_key=True),
        sa.Column("url", sa.String(1000)),
        sa.Column("overall_score", sa.Float),
        sa.Column("scores", sa.JSON, server_default="{}"),
        sa.Column("issues", sa.JSON, server_default="[]"),
        sa.Column("recommendations", sa.JSON, server_default="[]"),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table("dsar_requests", sa.Column("request_id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("request_type", sa.String(50)),
        sa.Column("data_subject_name", sa.String(255)),
        sa.Column("data_subject_email", sa.String(255)),
        sa.Column("status", sa.String(50), server_default="registered"),
        sa.Column("frameworks", sa.JSON, server_default="[]"),
        sa.Column("estimated_completion_days", sa.Integer, server_default="30"),
        sa.Column("rights_exercised", sa.JSON, server_default="[]"),
        sa.Column("next_steps", sa.JSON, server_default="[]"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )

    op.create_table("predictions", sa.Column("prediction_id", sa.String(64), primary_key=True),
        sa.Column("prediction_type", sa.String(50)),
        sa.Column("input_data", sa.JSON, server_default="{}"),
        sa.Column("output_data", sa.JSON, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("model_used", sa.String(50)),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table("security_alerts", sa.Column("alert_id", sa.String(64), primary_key=True),
        sa.Column("alert_type", sa.String(100)),
        sa.Column("severity", sa.String(20)),
        sa.Column("source_ip", sa.String(45)),
        sa.Column("target", sa.String(500)),
        sa.Column("blocked", sa.Boolean, server_default="true"),
        sa.Column("action_taken", sa.String(100)),
        sa.Column("details", sa.JSON, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table("audit_logs", sa.Column("log_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("endpoint", sa.String(500)),
        sa.Column("method", sa.String(10)),
        sa.Column("status_code", sa.Integer),
        sa.Column("request_body", sa.JSON, nullable=True),
        sa.Column("response_summary", sa.String(1000), nullable=True),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("latency_ms", sa.Float, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table("api_keys", sa.Column("key_id", sa.String(36), primary_key=True),
        sa.Column("key_hash", sa.String(255), unique=True, nullable=False),
        sa.Column("key_prefix", sa.String(20)),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.user_id")),
        sa.Column("name", sa.String(255)),
        sa.Column("scopes", sa.JSON, server_default="[]"),
        sa.Column("rate_limit", sa.String(50), server_default="100/minute"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_used", sa.DateTime, nullable=True),
        sa.Column("total_requests", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])


def downgrade() -> None:
    for table in [
        "api_keys", "audit_logs", "security_alerts", "predictions",
        "dsar_requests", "compliance_scans", "rag_document_chunks",
        "rag_documents", "chat_history", "users",
    ]:
        op.drop_table(table)
