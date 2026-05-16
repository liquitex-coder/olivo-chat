# Olivo Chat - Step 1 TaskBrief: 環境セットアップ

> 作成日：2026-05-14
> 営業用デモ「Trattoria Olivo チャットボット SaaS」の Step 1。
> 設計書 `olivo_chat_design.md` の Section 5「実装順序の推奨」に基づく最初のステップ。

---

## 位置づけ

Olivo Chat 開発の最初のステップ。リポジトリ立ち上げと最小限の開発環境構築のみ。実装ロジック（auth、API、DB スキーマ）はまだ作らない。**「docker-compose up で空の FastAPI が起動する」状態が完了基準**。

## §A プロトコル遵守事項

1. 本パッケージは Cursor 実装用 TaskBrief。Claude（チャット側）は動作検証していない
2. 既存ファイル上書きは差分提示 + 承認後のみ
3. PowerShell 直接実行で git 操作
4. 数値・パラメータは `docs/olivo_chat_design.md` と `.env.example` を一次情報源
5. **Genmyaku Auditor を Step 1 完了直後に投入する**ことを前提に作る（pydantic-settings 採用、env 整合性チェックが動く形）

## 完了基準

1. GitHub に `olivo-chat` リポジトリが作成されている（Public、モノレポ）
2. 設計書 `olivo_chat_design.md` が `docs/` に配置されている
3. ローカルで `docker-compose up -d` で PostgreSQL + backend コンテナが起動
4. `http://localhost:8000/health` が `{"status": "ok"}` を返す
5. `http://localhost:8000/docs` で FastAPI Swagger UI が表示される
6. `auditor.yaml` が Olivo 用設定で配置されている（Step 2 以降で Auditor が動く準備）
7. backend に `ruff check .` を実行して violation 0
8. **Genmyaku Auditor を投入して** Tier 1 ruff + Tier 2 env_consistency で違反 0（クリーン状態）

## ディレクトリ構造（Step 1 終了時点）

```
olivo-chat/
├── .gitignore
├── .env.example
├── docker-compose.yml
├── README.md
├── auditor.yaml
├── docs/
│   └── olivo_chat_design.md      # 既存ファイルを配置
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI 最小 app
│   │   ├── config.py             # pydantic-settings
│   │   └── db.py                 # SQLAlchemy engine（接続のみ、migration はまだ）
│   └── tests/
│       ├── __init__.py
│       └── test_health.py        # /health 動作確認
└── manifesto/
    └── olivo.yaml                # Tier 3 用、Step 1 では空骨格のみ
```

frontend/admin/ と frontend/embed/ は Step 4 で立ち上げる。Step 1 では backend のみ。

## 各ファイルの内容指針

### `.gitignore`

Python 標準 + Node 標準 + IDE 系。具体的には：

```
# Python
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Environment
.env
.env.local
.env.*.local
!.env.example

# Node
node_modules/
dist/
.vite/

# IDE
.vscode/
.idea/
*.swp

# Logs
logs/
*.log

# Auditor
audit_trail.jsonl
test_inventory.txt
```

### `.env.example`

設計書 §4.5 の環境変数を全て列挙。**Step 1 で全部書く**（後で追加するより、最初に揃えた方が env_consistency 検出が綺麗）。

```bash
# Backend
DATABASE_URL=postgresql://olivo:olivo_dev_password@db:5432/olivo_chat
JWT_SECRET=change_me_to_random_64_chars_in_production
JWT_ACCESS_TTL=900
JWT_REFRESH_TTL=2592000

ANTHROPIC_API_KEY=sk-ant-placeholder
CLAUDE_MODEL=claude-haiku-4-5-20251001

STRIPE_SECRET_KEY=sk_test_placeholder
STRIPE_WEBHOOK_SECRET=whsec_placeholder
STRIPE_PRICE_PRO=price_placeholder_pro
STRIPE_PRICE_BUSINESS=price_placeholder_business

CORS_ORIGINS=http://localhost:5173,http://localhost:5174
EMBED_BASE_URL=http://localhost:5174
ADMIN_BASE_URL=http://localhost:5173
API_BASE_URL=http://localhost:8000

# Frontend (Vite) - Step 4 で使用
VITE_API_BASE_URL=http://localhost:8000
```

### `docker-compose.yml`

```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: olivo
      POSTGRES_PASSWORD: olivo_dev_password
      POSTGRES_DB: olivo_chat
    ports:
      - "5432:5432"
    volumes:
      - olivo_db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U olivo -d olivo_chat"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://olivo:olivo_dev_password@db:5432/olivo_chat
      JWT_SECRET: dev_jwt_secret_do_not_use_in_production
      JWT_ACCESS_TTL: "900"
      JWT_REFRESH_TTL: "2592000"
      ANTHROPIC_API_KEY: sk-ant-placeholder
      CLAUDE_MODEL: claude-haiku-4-5-20251001
      STRIPE_SECRET_KEY: sk_test_placeholder
      STRIPE_WEBHOOK_SECRET: whsec_placeholder
      STRIPE_PRICE_PRO: price_placeholder_pro
      STRIPE_PRICE_BUSINESS: price_placeholder_business
      CORS_ORIGINS: "http://localhost:5173,http://localhost:5174"
      EMBED_BASE_URL: http://localhost:5174
      ADMIN_BASE_URL: http://localhost:5173
      API_BASE_URL: http://localhost:8000
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    depends_on:
      db:
        condition: service_healthy

volumes:
  olivo_db_data:
```

### `backend/pyproject.toml`

uv 推奨。最小依存：

```toml
[project]
name = "olivo-chat-backend"
version = "0.1.0"
requires-python = ">=3.11,<3.13"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "sqlalchemy>=2.0",
    "asyncpg>=0.30",
    "psycopg2-binary>=2.9",
    "alembic>=1.13",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "anthropic>=0.40",
    "stripe>=11.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
    "ruff>=0.7",
    "mypy>=1.13",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "S"]
ignore = ["S101"]  # assert は test で許可

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 1 の依存はこれで全部入れる**。alembic / anthropic / stripe を後で追加すると env_consistency が壊れる。

### `backend/Dockerfile`

```dockerfile
FROM python:3.11.9-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
RUN uv pip install --system -e .

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### `backend/app/config.py`（pydantic-settings、Auditor の env_consistency 対象）

```python
"""Application configuration loaded from environment variables."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # Database
    DATABASE_URL: str

    # JWT
    JWT_SECRET: str
    JWT_ACCESS_TTL: int = 900
    JWT_REFRESH_TTL: int = 2592000

    # Anthropic
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-haiku-4-5-20251001"

    # Stripe
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_PRICE_PRO: str
    STRIPE_PRICE_BUSINESS: str

    # CORS / URLs
    CORS_ORIGINS: str = ""
    EMBED_BASE_URL: str = ""
    ADMIN_BASE_URL: str = ""
    API_BASE_URL: str = ""


settings = Settings()
```

**重要**：`Field(alias=...)` は使わない（Step 1 では完全に直接マッピング）。Auditor の env_extractor が拾える形に保つ。

### `backend/app/db.py`（接続のみ、まだ migration しない）

```python
"""SQLAlchemy engine and session setup."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

### `backend/app/main.py`（最小 FastAPI app）

```python
"""Olivo Chat backend - main FastAPI application."""
from fastapi import FastAPI

from app.config import settings

app = FastAPI(
    title="Olivo Chat API",
    version="0.1.0",
    description="Chatbot SaaS for restaurants - Step 1 skeleton",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    """Backend version and configured model."""
    return {
        "version": app.version,
        "claude_model": settings.CLAUDE_MODEL,
    }
```

### `backend/tests/test_health.py`

```python
"""Smoke tests for backend startup."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version() -> None:
    response = client.get("/version")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "0.1.0"
    assert body["claude_model"] == "claude-haiku-4-5-20251001"
```

### `auditor.yaml`（Olivo 用、Track B）

```yaml
project:
  name: "Olivo Chat"
  identifier: "olivo_chat"
  track: "B"

silent_assurance:
  default_mode: "silent"
  proof_log: "logs/audit_trail.jsonl"

hallucination_tracking:
  mode: "independent"

syntactic:
  tools:
    - ruff

contextual:
  spec_sources:
    - type: markdown
      paths:
        - "docs/olivo_chat_design.md"
  env_consistency:
    dotenv_path: ".env.example"
    code_root: "backend/app"
  regime: "spec_evolving"

ethical:
  manifesto_path: "manifesto/olivo.yaml"
  enforcement_level: "strict"

# プラグインは Step 2 以降で必要なら追加
plugins: []
```

### `manifesto/olivo.yaml`（Step 1 では空骨格、Step 2 以降で内容追加）

```yaml
version: "0.1"
project: "olivo_chat"
principles: []
```

### `README.md`

設計書へのリンクと最小起動手順のみ。営業時に GitHub URL を見せる前提で、簡潔に書く。

```markdown
# Olivo Chat

レストラン向けチャットボット SaaS の営業デモ実装。

## クイックスタート

\`\`\`bash
docker-compose up -d
curl http://localhost:8000/health
\`\`\`

## 設計書

[docs/olivo_chat_design.md](docs/olivo_chat_design.md)

## デモ

`/demo/olivo` でサンプル店舗「Trattoria Olivo」の動作確認可能（Step 4 以降）。
\`\`\`
```

## 動作確認手順（Step 1 完了判定）

```powershell
# 1. リポジトリ作成 + 初期化
cd C:\Users\user
mkdir olivo-chat
cd olivo-chat
git init
# ... 全ファイル作成 ...
git add .
git commit -m "feat: initial scaffolding (Step 1)"

# 2. GitHub に push
gh repo create olivo-chat --public --source=. --push
# または手動で GitHub UI で作成 → git remote add origin ... → git push

# 3. Docker でローカル起動
docker-compose up -d
docker-compose ps   # backend と db が Up になっていること

# 4. ヘルスチェック
curl http://localhost:8000/health
# 期待: {"status":"ok"}

curl http://localhost:8000/version
# 期待: {"version":"0.1.0","claude_model":"claude-haiku-4-5-20251001"}

# 5. Swagger UI 確認
# ブラウザで http://localhost:8000/docs を開く

# 6. backend ruff
cd backend
ruff check .
# 期待: All checks passed!

# 7. backend tests
pytest tests/ -v
# 期待: 2 passed

# 8. Genmyaku Auditor 投入
cd C:\Users\user\genmyaku-auditor-core
# Olivo の backend を対象に Tier 1 ruff + Tier 2 env_consistency を実行
# （実行方法は genmyaku_auditor の CLI 整備状況に依存。
#  CLI 未整備なら、Python REPL で各 Detector を直接呼び出して動作確認）
```

## Step 1 で起こりやすい失敗パターン

- **pydantic-settings v1 と v2 の API 差**：v2 は `SettingsConfigDict` を使う。古い `class Config:` 構文だと Auditor の Pattern 4 検出が壊れる
- **Docker volume の権限問題**：Windows + WSL2 環境で `./backend:/app` マウントが遅い場合あり。営業デモなので致命的ではないが、起動時間が長いなら named volume に切り替え
- **env_consistency で `JWT_ACCESS_TTL` 等が `int` 変換失敗**：pydantic-settings は文字列 → int 変換するが、`.env` 側に空文字が入ると失敗。`.env.example` で全項目に値を入れておくこと
- **Auditor 投入時に code_root のパス指定間違い**：`backend/` ではなく `backend/app` を指定（pyproject.toml の付近に余計な os.getenv がないか確認）

## Step 2 への引き継ぎ

Step 1 完了後の Step 2 範囲:
- alembic 初期化（`alembic init alembic`）
- migration 001: 設計書の全テーブル DDL を作成
- migration 002: RLS ポリシー
- `app/models/` 配下に SQLAlchemy ORM モデル一式
- `app/schemas/` 配下に Pydantic スキーマ一式
- `tests/test_models.py` で全モデルが正しく定義されているか確認

## 提供物の出所（Provenance）

| ファイル | 出所 |
|---|---|
| 本 TaskBrief | `docs/olivo_chat_design.md` Section 5「実装順序の推奨」に基づく Step 1 の詳細化 |
| .env.example の項目 | 設計書 §4.5「環境変数」を直接転記 |
| pyproject.toml の依存 | 設計書 §4.2「backend/ 詳細」を実装 |
| docker-compose.yml | 設計書 §4.1「リポジトリ全体」+ 開発環境の慣用構成 |
| auditor.yaml | 設計書 §4.6「Render デプロイ」と Genmyaku Auditor Sprint 2.3 の env_consistency 仕様から逆算 |

私（Claude）の側で根拠なく追加した仕様はありません。