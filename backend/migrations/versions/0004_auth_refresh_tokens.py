"""auth step 3 part 2: refresh_tokens (RLS enabled with NULLIF policy)

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-20

Per Step 3 TaskBrief §2.2 + §1.5 + §1.6:
- refresh tokens are random strings (not JWTs); only their SHA-256 hash
  is stored, so a DB leak cannot reveal usable tokens.
- Rotation marks revoked_at on the old row and inserts a new row.
- RLS is enabled + FORCE so tenant isolation holds even for the owner
  role; the policy uses the same NULLIF(current_setting(...), '')
  pattern from migration 0002 to keep an empty GUC value safe.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index(
        "idx_refresh_tokens_user_revoked",
        "refresh_tokens",
        ["user_id", "revoked_at"],
    )
    op.create_index(
        "idx_refresh_tokens_expires_at",
        "refresh_tokens",
        ["expires_at"],
    )

    op.execute("ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE refresh_tokens FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON refresh_tokens
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON refresh_tokens")
    op.execute("ALTER TABLE refresh_tokens DISABLE ROW LEVEL SECURITY")
    op.drop_index("idx_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_index("idx_refresh_tokens_user_revoked", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
