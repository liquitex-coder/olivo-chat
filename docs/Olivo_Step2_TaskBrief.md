# Olivo Chat - Step 2 TaskBrief: DB スキーマ（Alembic / DDL / RLS / ORM / Pydantic）

> 作成日：2026-05-16
> 営業用デモ「Trattoria Olivo チャットボット SaaS」の Step 2。
> 設計書 `docs/olivo_chat_design.md` の Section 5「実装順序の推奨」に基づく第 2 ステップ。

---

## 位置づけ

Step 1 で `docker-compose up` により FastAPI + PostgreSQL + 空の SQLAlchemy `engine` が起動する状態が確定済み（olivo-chat commit `c43aae5`、auditor-core commit `606290c`）。Step 2 では **DB レイヤを構築する**。

設計書 Section 4.4 は「テーブル作成・RLS は Step 2」とだけ書かれていて具体的なテーブル設計を含まない。本 TaskBrief は Section 4.4 を補完する形で、Step 2 の具体的なテーブル定義・RLS ポリシー・マイグレーション戦略を **一次情報源として確定**する。

完了基準の要約：「`alembic upgrade head` で 3 テーブル + 2 RLS ポリシーが生成され、SQLAlchemy ORM 経由でテナント分離が動作することが pytest で確認できる」。

---

## §A プロトコル遵守事項

1. 本パッケージは Cursor 実装用 TaskBrief。Claude（チャット側）は動作検証していない
2. 既存ファイル上書きは差分提示 + 承認後のみ
3. PowerShell 直接実行で git 操作（Cursor の git 操作は禁止）
4. 数値・パラメータは `docs/olivo_chat_design.md` と本 TaskBrief を一次情報源
5. **Genmyaku Auditor を Step 2 完了直後に投入する**ことを前提に作る（C_spec は Step 3 以降で投入、Step 2 では Tier 1 ruff + Tier 2 env_consistency が継続して通る形）
6. 設計書 Section 4.4 と本 TaskBrief に矛盾がある場合は **本 TaskBrief を優先**（Step 2 完了後に設計書本体を別 commit で更新）

---

## 決め打ち事項（要確認）

本 TaskBrief で以下を確定。違和感があれば Step 2 着手前に修正：

| 項目 | 決定 | 理由 |
|---|---|---|
| 主キー型 | **UUID v4** (`gen_random_uuid()`) | テナント間の ID 衝突回避、外部公開時の連番推測防止 |
| FK 削除挙動 | **ON DELETE CASCADE** | テナント削除 → 会話 → メッセージが連鎖削除。営業デモなので簡素化優先 |
| `updated_at` 更新 | **PostgreSQL トリガー** | アプリ層の更新漏れ防止。一般的な PG パターン |
| RLS 方式 | `current_setting('app.current_tenant_id', true)::uuid` | セッション変数方式。Step 3 の Auth 層で `SET LOCAL` |
| RLS 対象 | `conversations`、`messages`（`tenants` は対象外） | tenants は認証層が触る／メタデータなので RLS 不要 |
| messages の tenant_id | **冗長保持**（FK 二重） | RLS のフィルタを join せず単表で完結させる |
| Alembic 接続 | **sync（psycopg2-binary）** | Alembic は sync 設計。app 本体は async（asyncpg）と切り分け |
| マイグレーション本体 | **手書き**（autogenerate は補助のみ） | RLS / CHECK / トリガーは autogenerate が拾わない |

---

## 完了基準

1. `backend/alembic.ini` と `backend/migrations/` が配置されている
2. `backend/migrations/versions/0001_initial_schema.py` が 3 テーブル + 2 RLS ポリシー + updated_at トリガーを定義
3. `docker-compose up -d` の後、コンテナ内で `alembic upgrade head` が成功
4. `\d tenants conversations messages` で 3 テーブルが存在し、列が本 TaskBrief 通り
5. `SELECT tablename, policyname FROM pg_policies` で 2 ポリシー（`tenant_isolation` on `conversations` と `messages`）が確認できる
6. `backend/app/db/models.py` で 3 つの SQLAlchemy ORM モデル（`Tenant`、`Conversation`、`Message`）が定義
7. `backend/app/schemas/{tenant,conversation,message}.py` で Pydantic v2 スキーマ（`*Base`、`*Create`、`*Read`）が定義
8. `backend/app/db/tenant_context.py` で `set_tenant_context(session, tenant_id)` が定義
9. `pytest tests/test_db_models.py` が PASS（INSERT/SELECT 経由で 3 テーブルの動作確認）
10. `pytest tests/test_rls_isolation.py` が PASS（テナント A のセッションでテナント B のデータが見えない）
11. `ruff check .` で violation 0
12. **Genmyaku Auditor 投入**で Tier 1 ruff = 0、Tier 2 env_consistency = WARN 1 件（`VITE_API_BASE_URL` のみ。新たな MISSING/UNUSED が出ない）

---

## 実装内容

### 1. Alembic 初期化

#### 1.1 ディレクトリ構成

```
backend/
  alembic.ini
  migrations/
    env.py
    script.py.mako
    versions/
      0001_initial_schema.py
```

#### 1.2 `alembic.ini`

主要設定：

```ini
[alembic]
script_location = migrations
sqlalchemy.url =   # env.py で環境変数から動的設定
```

#### 1.3 `migrations/env.py` のポイント

- `DATABASE_URL` 環境変数を読み、**sync 用に書き換え**（`postgresql+asyncpg://...` → `postgresql+psycopg2://...`）
- `target_metadata = Base.metadata` で autogenerate 有効化（補助用途）
- offline / online 両モード対応（標準テンプレートのまま）

#### 1.4 マイグレーション本体（`0001_initial_schema.py`）

手書きで以下を含める：

1. `CREATE EXTENSION IF NOT EXISTS "pgcrypto"` （`gen_random_uuid()` のため）
2. `tenants` テーブル作成
3. `conversations` テーブル作成
4. `messages` テーブル作成
5. INDEX 作成
6. `updated_at` 更新トリガー関数 + トリガー
7. RLS 有効化 + ポリシー作成

`downgrade()` も対称に書く（テーブル DROP → 関数 DROP → 拡張は残す）。

---

### 2. DDL（テーブル定義）

#### 2.1 `tenants`

| 列 | 型 | 制約 |
|---|---|---|
| `id` | `UUID` | PRIMARY KEY, DEFAULT `gen_random_uuid()` |
| `name` | `VARCHAR(255)` | NOT NULL |
| `slug` | `VARCHAR(64)` | NOT NULL, UNIQUE |
| `plan` | `VARCHAR(32)` | NOT NULL, DEFAULT `'free'`, CHECK (`plan IN ('free', 'pro', 'business')`) |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `now()` |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `now()` |

#### 2.2 `conversations`

| 列 | 型 | 制約 |
|---|---|---|
| `id` | `UUID` | PRIMARY KEY, DEFAULT `gen_random_uuid()` |
| `tenant_id` | `UUID` | NOT NULL, FK → `tenants(id)` ON DELETE CASCADE |
| `title` | `VARCHAR(255)` | NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `now()` |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `now()` |

INDEX:
- `idx_conversations_tenant_created` ON `(tenant_id, created_at DESC)`

#### 2.3 `messages`

| 列 | 型 | 制約 |
|---|---|---|
| `id` | `UUID` | PRIMARY KEY, DEFAULT `gen_random_uuid()` |
| `conversation_id` | `UUID` | NOT NULL, FK → `conversations(id)` ON DELETE CASCADE |
| `tenant_id` | `UUID` | NOT NULL, FK → `tenants(id)` ON DELETE CASCADE |
| `role` | `VARCHAR(16)` | NOT NULL, CHECK (`role IN ('user', 'assistant', 'system')`) |
| `content` | `TEXT` | NOT NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT `now()` |

INDEX:
- `idx_messages_conversation_created` ON `(conversation_id, created_at)`
- `idx_messages_tenant_created` ON `(tenant_id, created_at DESC)`

---

### 3. updated_at トリガー

PostgreSQL 標準パターン：

```sql
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

`messages` には `updated_at` 列が無い（メッセージは原則不変）ためトリガー不要。

---

### 4. RLS（Row Level Security）

```sql
-- conversations
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON conversations
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- messages
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON messages
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
```

**重要ポイント**：

- `FORCE ROW LEVEL SECURITY` を付ける：DB 所有者でも RLS を適用させる（テストでの取りこぼし防止）
- `current_setting('app.current_tenant_id', true)`：`true` は「未設定時に NULL を返す」モード。SET LOCAL されていない接続では全行が見えない（安全側）
- `tenants` テーブル自体は RLS 無効：認証層がテナント自体を引く必要があり、tenant_id でフィルタすると自己参照になる

---

### 5. SQLAlchemy ORM モデル

#### 5.1 ファイル分割

```
backend/app/db/
  __init__.py
  base.py           # DeclarativeBase
  models.py         # Tenant / Conversation / Message
  session.py        # async engine / async_sessionmaker（Step 1 で既存）
  tenant_context.py # set_tenant_context()
```

#### 5.2 `base.py`

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

#### 5.3 `models.py`

SQLAlchemy 2.x Mapped/`mapped_column` スタイル。重要点：

- `id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))`
- `created_at: Mapped[datetime] = mapped_column(server_default=func.now())`
- `updated_at: Mapped[datetime] = mapped_column(server_default=func.now())`
- `ForeignKey("tenants.id", ondelete="CASCADE")`
- `Mapped[str | None]` で NULL 許容

relationship は **Step 2 では張らない**（Step 3 で必要に応じて追加）。

#### 5.4 `tenant_context.py`

```python
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def set_tenant_context(session: AsyncSession, tenant_id: UUID) -> None:
    """セッション変数 app.current_tenant_id を設定して RLS を有効化する。

    必ずトランザクション内で呼ぶこと（SET LOCAL のため）。
    Step 3 の Auth ミドルウェアから呼ばれる想定。Step 2 ではテスト用。
    """
    await session.execute(
        text("SET LOCAL app.current_tenant_id = :tid"),
        {"tid": str(tenant_id)},
    )
```

---

### 6. Pydantic スキーマ

#### 6.1 ファイル構成

```
backend/app/schemas/
  __init__.py
  tenant.py
  conversation.py
  message.py
```

#### 6.2 共通パターン

各テーブルにつき 3 つのスキーマ：

- `XxxBase`：書き込み可能フィールドの共通定義
- `XxxCreate(XxxBase)`：POST 用（id、created_at 等を持たない）
- `XxxRead(XxxBase)`：GET 用（id、created_at、updated_at を含む。`model_config = ConfigDict(from_attributes=True)`）

#### 6.3 `tenant.py`

```python
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class TenantBase(BaseModel):
    name: str
    slug: str
    plan: Literal["free", "pro", "business"] = "free"

class TenantCreate(TenantBase):
    pass

class TenantRead(TenantBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

#### 6.4 `conversation.py`

```python
class ConversationBase(BaseModel):
    title: str | None = None

class ConversationCreate(ConversationBase):
    pass

class ConversationRead(ConversationBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

#### 6.5 `message.py`

```python
class MessageBase(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class MessageCreate(MessageBase):
    pass

class MessageRead(MessageBase):
    id: UUID
    conversation_id: UUID
    tenant_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

---

### 7. テスト

#### 7.1 `backend/tests/conftest.py` 追加（必要に応じて）

- テスト用 DB セッションフィクスチャ
- 各テスト後にロールバックする `db_session` フィクスチャ

#### 7.2 `tests/test_db_models.py`

3 テーブルそれぞれに対して：

- `INSERT`（ORM 経由）
- `SELECT`（id で取得、フィールド一致）
- `UPDATE`（updated_at が変化することを確認）
- FK 制約（存在しない tenant_id で会話作成 → IntegrityError）
- CASCADE（tenant 削除で conversations / messages が連鎖削除）

#### 7.3 `tests/test_rls_isolation.py`

シナリオ：

1. テナント A、テナント B を作成
2. A のコンテキストで会話 + メッセージを挿入
3. B のコンテキストで `SELECT` → A のレコードが見えないことを確認
4. SET LOCAL なしで `SELECT` → 0 件
5. A に戻すと再び見える

```python
async def test_rls_isolates_conversations(db_session):
    tenant_a, tenant_b = await _create_two_tenants(db_session)
    await set_tenant_context(db_session, tenant_a.id)
    conv = Conversation(tenant_id=tenant_a.id, title="A の会話")
    db_session.add(conv)
    await db_session.flush()

    # B から見ると見えない
    await set_tenant_context(db_session, tenant_b.id)
    result = await db_session.execute(select(Conversation))
    assert result.scalars().all() == []

    # A に戻すと見える
    await set_tenant_context(db_session, tenant_a.id)
    result = await db_session.execute(select(Conversation))
    assert len(result.scalars().all()) == 1
```

---

## Auditor 投入手順（Step 2 完了直後）

```powershell
cd C:\Users\user\genmyaku-auditor-core
.\venv\Scripts\Activate.ps1
$env:PYTHONPATH = "src"
python scripts/audit_olivo.py
```

期待される結果：

- Tier 1 ruff：0 claims
- Tier 2 env_consistency：1 WARN (`env_var_unused: VITE_API_BASE_URL`、Step 1 と同じ既知 WARN)
- 新たな MISSING/UNUSED が出たら設計書 vs 実装の乖離 → Cursor 改ざんの可能性、調査

新たな env var を実装で使った場合（例：Alembic で `DATABASE_URL` を `os.getenv` で読む等）、`.env.example` 側にも同期されていれば WARN 増加なし。

---

## Step 2 完了後の設計書更新

別 commit として：

1. `docs/olivo_chat_design.md` Section 4.4 を本 TaskBrief 内容で拡充
2. 「テーブル作成・RLS は Step 2」を「3 テーブル（tenants/conversations/messages）+ RLS（conversations/messages）を Alembic マイグレーションで管理」に置換
3. テーブル定義表を Section 4.4 に転記（本 TaskBrief の Section 2 内容）
4. commit メッセージ：`docs: expand Section 4.4 with Step 2 DB schema definitions`

これで設計書が一次情報源として完全になる。

---

## 参照

- 設計書 `docs/olivo_chat_design.md` Section 3「技術スタック」、4.2「backend 詳細」、4.4「データベース」、4.5「環境変数」、5「実装順序」
- Step 1 TaskBrief `docs/Olivo_Step1_TaskBrief.md`
- Genmyaku Auditor 投入スクリプト `scripts/audit_olivo.py`（auditor-core 側 commit `606290c`）
- PostgreSQL RLS 公式: https://www.postgresql.org/docs/16/ddl-rowsecurity.html
- SQLAlchemy 2.x ORM 公式: https://docs.sqlalchemy.org/en/20/orm/quickstart.html
- Alembic 公式: https://alembic.sqlalchemy.org/

---

## 想定作業時間（参考）

| 項目 | 目安 |
|---|---|
| Alembic 初期化 + env.py 修正 | 30 分 |
| マイグレーション本体（DDL + RLS + トリガー） | 60 分 |
| SQLAlchemy ORM モデル | 30 分 |
| Pydantic スキーマ | 20 分 |
| `tenant_context.py` | 10 分 |
| テスト 2 ファイル | 60 分 |
| docker-compose で動作確認 + 修正 | 30 分 |
| Auditor 投入確認 | 10 分 |
| **合計** | **約 4 時間** |
