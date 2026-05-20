"""auth step 3 part 1: users table (RLS disabled by design)

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-20

Per Step 3 TaskBrief §2.1 + §1.6: users is intentionally RLS-disabled.
Login flow has to look up the row by email before tenant_id is known,
so attaching an RLS policy keyed on app.current_tenant_id would break
authentication. Direct access to this table is restricted to the auth
router by convention; other code paths must hop through
`get_current_user`.

Schema:
    id              UUID PK, gen_random_uuid()
    tenant_id       UUID NOT NULL, FK tenants(id) ON DELETE CASCADE
    email           TEXT NOT NULL (lowercase, normalised at app layer)
    password_hash   TEXT NOT NULL (argon2id output)
    created_at      TIMESTAMPTZ NOT NULL default now()
    updated_at      TIMESTAMPTZ NOT NULL default now(), trigger-maintained
    UNIQUE (tenant_id, email)
    INDEX  (email)         -- login lookup

refresh_tokens (RLS-enabled) is intentionally deferred to migration
0004 to keep this diff small and reviewable.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    op.create_index("idx_users_email", "users", ["email"])

    op.execute(
        """
        CREATE TRIGGER trg_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_users_updated_at ON users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
