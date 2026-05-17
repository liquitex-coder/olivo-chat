# Olivo Chat - Step 3 TaskBrief: Auth / JWT

> 作成日：2026-05-17
> 直前 commit：olivo-chat side は W292 fix まで、auditor-core side は `46a64db` (D1+D2 追加)
> 設計書 `docs/olivo_chat_design.md` Section 5 「実装順序の推奨」の第 3 ステップ

---

## 位置づけ

Step 2 + 2.1 で DB レイヤ（tenants, conversations, messages + RLS + Alembic + ORM + Pydantic）が確定し、テナント分離が物理的に機能することを 10/10 テストで実証した（commit `c43aae5` → `b8dbdf1` → `fca06a1` → `07c17b0` → W292 fix）。

Step 3 では **認証層を構築** し、外部から触れる FastAPI エンドポイントが JWT 経由でテナントスコープを設定し、Step 2 で実装した RLS を起動できるようにする。Step 2 で書いた `set_tenant_context()` を実際に呼ぶ最初の使用例となる。

完了基準の要約：「signup → login → access token を Authorization ヘッダで送ると `/api/v1/conversations` で自分のテナントの会話だけが見える。異なるテナントのユーザーは互いの会話を list できない」を pytest で確認できる状態。

---

## §A プロトコル遵守事項

1. 本 TaskBrief は Cursor 実装用指示書。Claude（チャット側）は動作検証していない
2. 既存ファイル上書きは差分提示 + 承認後のみ
3. PowerShell 直接実行で git 操作（Cursor の git 操作は禁止）
4. 完了時の自己検証は本人が以下を実行：
   - `docker compose exec backend pytest tests/ -v --tb=short`
   - `docker compose exec backend ruff check .`
   - `python scripts/audit_olivo.py`（D1+D2 込み）
5. Cursor が「やった」と書いた項目は `git show <hash> --stat` で必ず突合
6. auditor D1（commit_message_reality）が走るので、commit message と実 diff の不一致は自動検出される（fca06a1 の再発防止）
7. auditor D2（cross_file_consistency）が走るので、init script / mount の不整合も検出される

---

## 1. 設計判断（決め打ち）

### 1.1 Tenant モデル

- **1 user = 1 tenant**（MVP）
- `users.tenant_id` は FK → `tenants(id)`
- `(tenant_id, email)` UNIQUE（異なる tenant が同じ email を使える）
- 将来拡張：`user_tenants` 中間テーブルを追加すれば multi-membership 対応可能

### 1.2 Signup フロー

- 新規 tenant 作成 + その tenant の最初の user を **同一トランザクション** で作成
- API: `POST /api/v1/auth/signup` で `{tenant_name, tenant_slug, email, password}` を受ける

### 1.3 Password

- **argon2id**（passlib[argon2]）
- 最低 8 文字、最大 128 文字
- email は小文字に正規化して保存

### 1.4 JWT

- **HS256**、署名鍵は環境変数 `JWT_SECRET`
- access token: TTL 15 分（`JWT_ACCESS_TTL=900`）
- refresh token: TTL 30 日（`JWT_REFRESH_TTL=2592000`）
- access JWT の claim: `sub` (user_id), `tid` (tenant_id), `exp`, `iat`, `typ="access"`
- refresh は **JWT ではなく random string** （`secrets.token_urlsafe(48)`）
- ライブラリは PyJWT（python-jose も可だが、PyJWT の方が依存が軽い）

### 1.5 Refresh Token Storage & Rotation

- DB テーブル `refresh_tokens` に **SHA-256 hash** を保存（raw token は DB に置かない）
- refresh 時に旧 refresh を `revoked_at = now()` でマーク、新 refresh を発行（rotation）
- access は stateless（DB 不要、JWT のみで完結）

### 1.6 RLS と Auth の関係

- **`users` テーブルは RLS 無効**: login 時に tenant_id 未知のため email で逆引きする必要
- **`refresh_tokens` テーブルは RLS 有効**: tenant_id で分離（既存 conversations/messages と同じパターン、`NULLIF` 防御つき）
- 規約：`users` への直接アクセスは **Auth router のみ** が許可される。他のルーターは `get_current_user` 経由でしかアクセスしない（コードレビュー / auditor で担保）
- 認証後：`get_current_user` Dependency が `set_tenant_context(session, jwt.tid)` を呼ぶ → 以降の SELECT は RLS で自動絞り込み

### 1.7 Step 2.1 で得た知見の反映

- `set_tenant_context()` は既に `set_config('app.current_tenant_id', :tid, true)` を使用済み（変更不要）
- 新 RLS ポリシー（`refresh_tokens`）も `NULLIF(current_setting(...), '')::uuid` 防御を継承
- POSTGRES_USER=postgres + olivo は NOSUPERUSER という構成は Step 2.1 で確定済み（変更不要）

---

## 2. テーブル設計

### 2.1 `users`

| 列 | 型 | 制約 / メモ |
|---|---|---|
| `id` | UUID | PK, default `gen_random_uuid()` |
| `tenant_id` | UUID | NOT NULL, FK → `tenants(id)` ON DELETE CASCADE |
| `email` | TEXT | NOT NULL, lowercase (アプリ層で正規化) |
| `password_hash` | TEXT | NOT NULL, argon2id 出力 |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default `now()`、トリガーで更新 |

- UNIQUE: `(tenant_id, email)`
- INDEX: `email`（login の逆引き用）
- **RLS: 無効**（§1.6 参照）

### 2.2 `refresh_tokens`

| 列 | 型 | 制約 / メモ |
|---|---|---|
| `id` | UUID | PK, default `gen_random_uuid()` |
| `tenant_id` | UUID | NOT NULL, FK → `tenants(id)` ON DELETE CASCADE（RLS 用） |
| `user_id` | UUID | NOT NULL, FK → `users(id)` ON DELETE CASCADE |
| `token_hash` | TEXT | NOT NULL, SHA-256 (64 文字 hex) of raw token |
| `expires_at` | TIMESTAMPTZ | NOT NULL |
| `revoked_at` | TIMESTAMPTZ | NULL = 有効、NOT NULL = revoked |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` |

- UNIQUE: `token_hash`
- INDEX: `(user_id, revoked_at)`, `expires_at`
- **RLS: 有効 + FORCE ROW LEVEL SECURITY**
- Policy: `USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)`

---

## 3. 認証フロー

### 3.1 Signup

```
Client → POST /api/v1/auth/signup
  Body: {tenant_name, tenant_slug, email, password}
↓
service.signup_user():
  1. password を argon2id でハッシュ
  2. INSERT tenant (name, slug) → tenant_id 取得 (RLS なし)
  3. INSERT user (tenant_id, lower(email), password_hash) → user_id 取得 (RLS なし)
  4. set_tenant_context(session, tenant_id) で RLS スコープを設定
  5. raw_refresh = secrets.token_urlsafe(48)
  6. INSERT refresh_tokens (tenant_id, user_id, sha256(raw_refresh), expires_at=now+30d)
  7. access_token = encode_access_token(user_id, tenant_id)
  8. commit
↓
Return 201 {access_token, refresh_token: raw_refresh, token_type: "bearer"}
```

### 3.2 Login

```
Client → POST /api/v1/auth/login
  Body: {email, password}
↓
service.authenticate_user():
  1. SELECT user WHERE email = lower(email)
     - MVP では複数 tenant に同じ email がある場合「最初に見つかった 1 件」を採用
     - 将来的に SaaS として育てる際はサブドメインまたは tenant_slug を併用
  2. verify_password(password, user.password_hash)
     - 失敗時は 401（メッセージは "Invalid credentials" のみ、user 有無は漏らさない）
  3. set_tenant_context(session, user.tenant_id)
  4. refresh_token を発行・DB 記録
  5. access_token を発行
↓
Return 200 {access_token, refresh_token, token_type: "bearer"}
```

### 3.3 Refresh (with Rotation)

```
Client → POST /api/v1/auth/refresh
  Body: {refresh_token}
↓
service.rotate_refresh_token():
  1. refresh_hash = sha256(refresh_token)
  2. SELECT FROM refresh_tokens
       WHERE token_hash = refresh_hash
         AND revoked_at IS NULL
         AND expires_at > now()
     - 該当なし → 401
  3. set_tenant_context(session, row.tenant_id)
  4. UPDATE refresh_tokens SET revoked_at = now() WHERE id = row.id
  5. 新 raw_refresh を発行 → INSERT 新 refresh_tokens 行
  6. 新 access_token を発行
↓
Return 200 {access_token: new_access, refresh_token: new_raw, token_type: "bearer"}
```

### 3.4 Logout

```
Client → POST /api/v1/auth/logout
  Authorization: Bearer <access>
  Body: {refresh_token}
↓
service.revoke_refresh_token():
  1. get_current_user で access を検証、tenant_id 取得
  2. set_tenant_context(session, tenant_id)
  3. UPDATE refresh_tokens SET revoked_at = now()
       WHERE token_hash = sha256(refresh_token) AND user_id = current_user.id
↓
Return 204
```

### 3.5 Protected endpoint（例：`GET /api/v1/conversations`）

```
Client → GET /api/v1/conversations
  Authorization: Bearer <access>
↓
Dependency: get_current_user(authorization, session)
  1. Authorization ヘッダ解析、JWT decode
  2. exp, typ="access" を検証
  3. set_tenant_context(session, jwt.tid) で RLS 起動
  4. Return CurrentUser(id, tenant_id)
↓
Route handler:
  rows = await session.execute(select(Conversation))
  # ← RLS が自動で WHERE tenant_id = current_tenant_id を適用
↓
Return [{id, title, created_at, updated_at}, ...]
```

---

## 4. 実装範囲

### やる

- Alembic マイグレーション 0003: users + refresh_tokens + RLS + updated_at トリガー
- ORM モデル (User, RefreshToken)
- Pydantic スキーマ (SignupRequest, LoginRequest, RefreshRequest, LogoutRequest, TokenResponse, UserRead)
- argon2id password hash/verify (`app/auth/password.py`)
- HS256 JWT encode/decode (`app/auth/jwt_tokens.py`)
- 4 つの Auth エンドポイント (signup, login, refresh, logout)
- `get_current_user` Dependency (Bearer 検証 + `set_tenant_context()` 呼び出し)
- 認証必須エンドポイント 1 つ（最小実装の `GET /api/v1/conversations`）で RLS 起動の動作確認

### やらない（後のステップ）

- Email 確認、パスワードリセット、SSO/OAuth
- Rate limiting、CAPTCHA、2FA、デバイス管理
- ロールベース権限（admin/member 区別）
- パスワード強度推定 (zxcvbn)
- セッション一覧 UI
- フロントエンド側の実装

---

## 5. ファイル構成

```
backend/
├── app/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── router.py         # POST /api/v1/auth/{signup, login, refresh, logout}
│   │   ├── schemas.py        # Pydantic
│   │   ├── service.py        # signup_user, authenticate_user, rotate_refresh_token, revoke_refresh_token
│   │   ├── jwt_tokens.py     # encode_access_token, decode_token
│   │   ├── password.py       # hash_password, verify_password (argon2id)
│   │   └── dependencies.py   # get_current_user, AuthenticatedSession
│   ├── db/
│   │   ├── models.py         # ← User, RefreshToken を追加
│   │   └── ...
│   ├── conversations/        # ← protected endpoint の動作確認用（最小実装）
│   │   ├── __init__.py
│   │   └── router.py         # GET /api/v1/conversations
│   └── main.py               # ← auth_router と conversations_router を mount
├── migrations/versions/
│   └── 0003_auth_users_and_refresh_tokens.py
├── tests/
│   ├── test_auth_signup.py
│   ├── test_auth_login.py
│   ├── test_auth_refresh_rotation.py
│   ├── test_auth_logout.py
│   └── test_protected_endpoint.py
└── pyproject.toml             # ← passlib[argon2], pyjwt を追加
```

---

## 6. コード骨子（要点のみ。Cursor が拡充する）

### 6.1 `app/auth/password.py`

```python
"""argon2id ベースのパスワード hash / verify。"""
from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

MIN_PASSWORD_LEN = 8
MAX_PASSWORD_LEN = 128


def hash_password(plain: str) -> str:
    if not MIN_PASSWORD_LEN <= len(plain) <= MAX_PASSWORD_LEN:
        raise ValueError(
            f"password length must be {MIN_PASSWORD_LEN}-{MAX_PASSWORD_LEN}"
        )
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)
```

### 6.2 `app/auth/jwt_tokens.py`

```python
"""HS256 JWT encode/decode。env JWT_SECRET / JWT_ACCESS_TTL を読み込む。"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

_SECRET = os.environ["JWT_SECRET"]
_ALG = "HS256"
ACCESS_TTL_SECONDS = int(os.environ["JWT_ACCESS_TTL"])    # 900
REFRESH_TTL_SECONDS = int(os.environ["JWT_REFRESH_TTL"])  # 2592000


def encode_access_token(user_id: UUID, tenant_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ACCESS_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALG)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _SECRET, algorithms=[_ALG])
```

### 6.3 `app/auth/dependencies.py`

```python
"""認証 Dependency: Bearer から JWT 解析 → set_tenant_context() で RLS 起動。"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_tokens import decode_token
from app.db import async_session_factory, set_tenant_context


async def _get_db_session():
    async with async_session_factory() as session:
        async with session.begin():
            yield session


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    tenant_id: UUID


async def get_current_user(
    authorization: str = Header(default=""),
    session: AsyncSession = Depends(_get_db_session),
) -> CurrentUser:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer required")
    token = authorization[len("Bearer "):]
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from e
    if payload.get("typ") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "wrong token type")

    try:
        tenant_id = UUID(payload["tid"])
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError) as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "malformed claims") from e

    # Step 2.1 で確立した set_config 経由
    await set_tenant_context(session, tenant_id)

    return CurrentUser(id=user_id, tenant_id=tenant_id)
```

### 6.4 `app/auth/service.py`（signup の骨子）

```python
"""Auth ビジネスロジック。"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_tokens import REFRESH_TTL_SECONDS, encode_access_token
from app.auth.password import hash_password, verify_password
from app.db import set_tenant_context
from app.db.models import RefreshToken, Tenant, User


def _hash_refresh(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _new_refresh_raw() -> str:
    return secrets.token_urlsafe(48)


async def signup_user(
    *,
    session: AsyncSession,
    tenant_name: str,
    tenant_slug: str,
    email: str,
    password: str,
) -> tuple[Tenant, User, str, str]:
    """新規 tenant + user を作成し、access_token と raw refresh_token を返す。"""
    pw_hash = hash_password(password)

    tenant = Tenant(name=tenant_name, slug=tenant_slug)
    session.add(tenant)
    await session.flush()

    user = User(
        tenant_id=tenant.id,
        email=email.lower(),
        password_hash=pw_hash,
    )
    session.add(user)
    await session.flush()

    await set_tenant_context(session, tenant.id)  # refresh_tokens は RLS 有効

    raw_refresh = _new_refresh_raw()
    rt = RefreshToken(
        tenant_id=tenant.id,
        user_id=user.id,
        token_hash=_hash_refresh(raw_refresh),
        expires_at=datetime.now(timezone.utc)
        + timedelta(seconds=REFRESH_TTL_SECONDS),
    )
    session.add(rt)
    await session.flush()

    access = encode_access_token(user.id, tenant.id)
    return tenant, user, access, raw_refresh
```

（同様に `authenticate_user`, `rotate_refresh_token`, `revoke_refresh_token` を実装。Cursor に展開を任せる）

### 6.5 `app/auth/router.py`（signup ハンドラ抜粋）

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import _get_db_session, get_current_user
from app.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
)
from app.auth.service import (
    authenticate_user,
    revoke_refresh_token,
    rotate_refresh_token,
    signup_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/signup", status_code=201, response_model=TokenResponse)
async def signup(
    req: SignupRequest,
    session: AsyncSession = Depends(_get_db_session),
):
    try:
        _, _, access, refresh = await signup_user(
            session=session,
            tenant_name=req.tenant_name,
            tenant_slug=req.tenant_slug,
            email=req.email,
            password=req.password,
        )
    except IntegrityError as e:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "tenant slug or email already exists"
        ) from e
    return TokenResponse(access_token=access, refresh_token=refresh)


# /login, /refresh, /logout も同様に実装（Cursor 任せ）
```

---

## 7. Alembic マイグレーション 0003 の方針

ファイル: `backend/migrations/versions/0003_auth_users_and_refresh_tokens.py`

```python
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```

含めるもの：

1. `CREATE TABLE users` (上記スキーマ通り、RLS 無効)
2. `CREATE TABLE refresh_tokens` (上記スキーマ通り)
3. `ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY`
4. `ALTER TABLE refresh_tokens FORCE ROW LEVEL SECURITY`
5. RLS ポリシー（NULLIF 防御）：
   ```sql
   CREATE POLICY tenant_isolation ON refresh_tokens
     USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
   ```
6. `set_updated_at` トリガー（0001 で作成済みの関数を users に適用）
7. インデックス: `users(email)`, `refresh_tokens(user_id, revoked_at)`, `refresh_tokens(expires_at)`
8. UNIQUE: `users(tenant_id, email)`, `refresh_tokens(token_hash)`

`downgrade()` で逆順に DROP（INDEX → POLICY → TABLE）。

---

## 8. テスト範囲

### 8.1 `test_auth_signup.py`（4 件）

- 新規 tenant + user の作成、access + refresh が返る
- 同一 (tenant_id, email) の二重 signup は 409
- 同一 tenant_slug の二重 signup は 409
- パスワード短すぎ (< 8) は 422 or 400

### 8.2 `test_auth_login.py`（4 件）

- 正しい password でログイン成功、access + refresh が返る
- 誤 password で 401（メッセージは "Invalid credentials"）
- 存在しない email で 401（タイミング攻撃対策は MVP では緩い）
- access token の claim が想定通り（`sub`, `tid`, `exp`, `iat`, `typ="access"`）

### 8.3 `test_auth_refresh_rotation.py`（3 件）

- 有効な refresh で新 access + 新 refresh が返る
- 旧 refresh の `revoked_at` が設定される（rotation）
- 旧 refresh で再度 refresh しようとすると 401

### 8.4 `test_auth_logout.py`（2 件）

- logout で refresh が revoke される
- revoked refresh での refresh は 401

### 8.5 `test_protected_endpoint.py`（4 件、Step 3 のキモ）

- 認証なしで `GET /api/v1/conversations` → 401
- 自分の tenant の会話だけ返る（RLS が JWT 経由で起動していることの確認）
- 別 tenant のユーザーが同じエンドポイントを叩いても、その tenant の会話だけ返る
- 期限切れ access token で 401

合計 17 件。pytest 10 + 17 = **27 件** を目指す。

---

## 9. 完了基準（チェックリスト）

- [ ] `alembic upgrade head` で 0003 が適用、エラーなし
- [ ] `psql` で users（RLS 無効）と refresh_tokens（RLS 有効 + FORCE）の状態を確認
- [ ] signup → 201 + tokens
- [ ] login → 200 + tokens
- [ ] refresh → 旧 refresh が revoke + 新 tokens 発行
- [ ] logout → 該当 refresh が revoke される
- [ ] protected endpoint で別 tenant の会話が見えない（RLS が動作）
- [ ] 認証なしリクエストは 401
- [ ] pytest 全件 PASS（既存 10 + 新規 17 = 27 件）
- [ ] `docker compose exec backend ruff check .` で 0 violations
- [ ] `python scripts/audit_olivo.py` で **PASS with WARN**（VITE_API_BASE_URL のみ）
- [ ] auditor D1（commit_message_reality）が commit に対して claim を出さない
- [ ] auditor D2（cross_file_consistency）が 0 claim

---

## 10. 想定作業時間（Cursor の作業ベース）

| 項目 | 目安 |
|---|---|
| Alembic 0003（users + refresh_tokens + RLS + トリガー + インデックス） | 60 分 |
| ORM モデル + Pydantic スキーマ | 30 分 |
| `password.py` / `jwt_tokens.py` | 30 分 |
| `service.py`（4 つのビジネス関数） | 60 分 |
| `router.py`（4 つのエンドポイント） | 30 分 |
| `dependencies.py`（`get_current_user`） | 30 分 |
| 最小実装の `conversations/router.py`（GET のみ） | 20 分 |
| テスト 5 ファイル（17 件） | 90 分 |
| docker-compose 動作確認 + 修正 | 30 分 |
| Auditor 投入確認（D1+D2 込み） | 10 分 |
| **合計** | **約 6 時間** |

Step 2 より重め（auth は微妙な落とし穴が多い、token rotation や RLS との交差で詰まりやすい）。

---

## 11. 参照

- 設計書 `docs/olivo_chat_design.md` Section 5
- Step 1 TaskBrief `docs/Olivo_Step1_TaskBrief.md`
- Step 2 TaskBrief `docs/Olivo_Step2_TaskBrief.md`
- Step 2.1 で確立した `set_tenant_context()` 実装（`backend/app/db/tenant_context.py`）
- Alembic 0002 の NULLIF 防御パターン（`backend/migrations/versions/0002_harden_rls_nullif.py`）
- argon2 仕様: https://github.com/P-H-C/phc-winner-argon2
- passlib argon2: https://passlib.readthedocs.io/en/stable/lib/passlib.hash.argon2.html
- PyJWT: https://pyjwt.readthedocs.io/
- PostgreSQL RLS: https://www.postgresql.org/docs/16/ddl-rowsecurity.html

---

## 12. 重要な落とし穴（Step 2.1 からの教訓を継承）

1. **commit message と現実の乖離**: 「やったことにする」commit は auditor D1 が止める。`fca06a1` の再発を防ぐため、Cursor の作業後は必ず `git show <hash> --stat` で本人が確認すること
2. **RLS と認証の交差**: `users` は RLS 無効、`refresh_tokens` は RLS 有効 + NULLIF 防御。これを混同しないこと
3. **`set_tenant_context` は `set_config` を使う**: `SET LOCAL` は bind parameter 非対応（Step 2.1 で確定済み、変更不要）
4. **`RESET` の罠**: 未登録 custom GUC を `RESET` すると空文字列 `''` に戻る（NULL ではない）。これが Step 2.1 で 0002 マイグレーションを追加した理由。新ポリシー (`refresh_tokens`) も同じ `NULLIF` 防御を必ず適用
5. **`JWT_SECRET` は本番で必ず変更**: docker-compose.yml のデフォルトは `dev_jwt_secret_do_not_use_in_production` という明確なプレースホルダ。Step 7（VPS デプロイ）で必ず差し替える
6. **argon2 のメモリ要件**: デフォルト設定で問題ないはずだが、CI 環境（GitHub Actions 等）で OOM になる場合は `argon2_memory_cost` を下げる選択肢を検討（passlib の default は memory_cost=10240 KiB ≒ 10 MB）
7. **email の case sensitivity**: `users.email` は小文字に正規化して保存。検索時も小文字に。これを忘れると「同じメールで signup できてしまう」状態になる
8. **token rotation の race condition**: 同時に複数の refresh リクエストが来た場合、最初の 1 件が rotate、2 件目以降は 401 になるのが想定動作。テストでは concurrency までは検証しない（MVP）

---

## 13. 次の判断ポイント（Step 3 完了後）

Step 3 完了後の判断材料：

- **Step 4**: フロントエンド（React + Vite）の signup/login UI 実装、protected ページ
- **Step 5**: Claude API 連携によるチャット応答（既存 `ANTHROPIC_API_KEY` env を使う）
- **Step 6**: Stripe 連携によるサブスク（既存 `STRIPE_*` env を使う）

Step 3 で確立する Auth 基盤がそのまま Step 4-6 で使われる。よって Step 3 は十分に固めてから次に進む方が手戻りが少ない。

---

*EOF*
