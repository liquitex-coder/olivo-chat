# Olivo Chat — 設計書（営業デモ）

作成: 2026-05-14  
本書は **Trattoria Olivo** をサンプルとしたチャットボット SaaS「Olivo Chat」の実装・デモ用の一次情報源である。

---

## 1. プロダクト概要

レストラン向けに埋め込みチャットウィジェットと管理コンソールを提供するマルチテナント SaaS。Step 1 ではバックエンドのスケルトンのみを対象とする。

---

## 2. 用語

- **Tenant**: 店舗（レストラン）単位の論理分離。
- **Embed**: 店舗サイトに埋め込むチャット UI（Vite、Step 4）。
- **Admin**: 店舗管理者向けコンソール（Vite、Step 4）。

---

## 3. 技術スタック（確定）

| 領域 | 技術 |
|------|------|
| API | FastAPI + Uvicorn |
| 設定 | pydantic-settings v2（`SettingsConfigDict`） |
| DB | PostgreSQL 16、SQLAlchemy 2.x、Alembic（Step 2 で migration） |
| LLM | Anthropic Claude（API キーは環境変数） |
| 課金 | Stripe |
| コンテナ開発 | Docker Compose（`db` + `backend`） |

---

## 4. リポジトリとデプロイ

### 4.1 リポジトリ全体（モノレポ）

```
olivo-chat/
  backend/          # FastAPI（Step 1 スコープ）
  docs/             # 本設計書
  manifesto/        # Genmyaku Tier 3
  frontend/admin/   # Step 4
  frontend/embed/   # Step 4
```

### 4.2 backend 詳細（依存）

Step 1 の `pyproject.toml` に記載のとおり: FastAPI、Uvicorn、pydantic-settings、SQLAlchemy、asyncpg、psycopg2-binary、Alembic、python-jose、passlib、anthropic、stripe、および dev で pytest / httpx / ruff / mypy。

**Python バージョン**: Docker イメージは **3.11.9**。ローカル開発では 3.11 以外（例: 3.14）でも `requires-python = ">=3.11,<4"` の範囲で `pip install -e ".[dev]"` 可能。本番・CI の基準はコンテナと揃えること。

### 4.3 API 表層（Step 1）

- `GET /health` … ライブネス。`{"status":"ok"}`。
- `GET /version` … バージョンと設定上の Claude モデル名。

### 4.4 データベース（Step 1）

PostgreSQL に接続する SQLAlchemy `engine` のみ。テーブル作成・RLS は Step 2。

### 4.5 環境変数（一次情報源）

ローカル・CI・本番の共通キー。値の例はリポジトリ直下 `.env.example` と同一とする。

| 変数名 | 用途 |
|--------|------|
| `DATABASE_URL` | PostgreSQL 接続 URL |
| `JWT_SECRET` | JWT 署名用シークレット |
| `JWT_ACCESS_TTL` | アクセストークン TTL（秒） |
| `JWT_REFRESH_TTL` | リフレッシュトークン TTL（秒） |
| `ANTHROPIC_API_KEY` | Claude API |
| `CLAUDE_MODEL` | 利用モデル ID |
| `STRIPE_SECRET_KEY` | Stripe シークレット |
| `STRIPE_WEBHOOK_SECRET` | Webhook 署名検証 |
| `STRIPE_PRICE_PRO` / `STRIPE_PRICE_BUSINESS` | 価格 ID |
| `CORS_ORIGINS` | 許可オリジン（カンマ区切り） |
| `EMBED_BASE_URL` / `ADMIN_BASE_URL` / `API_BASE_URL` | 各面のベース URL |
| `VITE_API_BASE_URL` | フロント（Step 4）用 API ベース URL |

**Genmyaku Auditor（env_consistency）**: `backend/app` 内のコードと `.env.example` のキーが整合するよう、`app/config.py` の `Settings` に上記を **Field(alias) なし** で宣言する（Step 1）。

### 4.6 Render デプロイ（メモ）

本番では環境変数をホスティング側に設定し、`DATABASE_URL` はマネージド Postgres の URL に差し替える。詳細は Step 3 以降で追記する。

---

## 5. 実装順序の推奨

1. **Step 1**: リポジトリ初期化、Docker Compose、空の FastAPI、`pydantic-settings`、Auditor 用 `auditor.yaml` / manifesto 骨格、`.env.example` 完備。
2. **Step 2**: Alembic、DDL、RLS、ORM / Pydantic スキーマ。
3. **Step 3 以降**: Auth、Stripe Webhook、会話 API、フロント等。

---

## 6. 参照

- `Olivo_Step1_TaskBrief.md` … Step 1 の手順・完了基準。
- `auditor.yaml` … Genmyaku Auditor（Track B）設定。
