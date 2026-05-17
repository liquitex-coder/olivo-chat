"""Set the per-session tenant ID for RLS."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_tenant_context(session: AsyncSession, tenant_id: UUID) -> None:
    """セッション変数 app.current_tenant_id を設定して RLS を有効化する。

    必ずトランザクション内で呼ぶこと（set_config の 3 番目引数 true = LOCAL）。
    Step 3 の Auth ミドルウェアから呼ばれる想定。Step 2 ではテスト用。
    """
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )
