"""harden RLS policies with NULLIF for empty tenant context

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-17

Background:
    PostgreSQL's RESET command resets a custom GUC parameter to its
    startup value. For unregistered custom parameters this default is
    an empty string '' (not NULL). Therefore, after
    `RESET app.current_tenant_id`, current_setting('app.current_tenant_id', true)
    returns '' rather than NULL, and ''::uuid raises
    InvalidTextRepresentationError.

Fix:
    Wrap current_setting() in NULLIF(..., '') so that empty string is
    normalised to NULL. NULL::uuid is harmless, and tenant_id = NULL is
    NULL (false) for every row, which is the safe default (no rows
    visible without a valid tenant context).
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP POLICY tenant_isolation ON conversations")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON conversations
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
        """
    )

    op.execute("DROP POLICY tenant_isolation ON messages")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON messages
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY tenant_isolation ON conversations")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON conversations
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
        """
    )

    op.execute("DROP POLICY tenant_isolation ON messages")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON messages
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
        """
    )
