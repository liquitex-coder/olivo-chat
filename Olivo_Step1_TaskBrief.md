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

詳細な `.gitignore` / `.env.example` / `docker-compose.yml` / `backend/pyproject.toml` / `Dockerfile` / `app/*.py` / `tests/test_health.py` / `auditor.yaml` / `manifesto/olivo.yaml` / `README.md` の本文は、Cursor 実装時にチャットに貼られた Step 1 TaskBrief 全文（または本リポジトリの初回コミット差分）と同一を前提とする。一次情報源は **`docs/olivo_chat_design.md`** および **`.env.example`**。

## 動作確認手順（Step 1 完了判定）

1. `git init` → 全ファイル追加 → `git commit -m "feat: initial scaffolding (Step 1)"`
2. `gh repo create olivo-chat --public --source=. --push` または GitHub UI でリモート作成後 `git push`
3. `docker-compose up -d` → `docker-compose ps` で `db` / `backend` が Up
4. `curl http://localhost:8000/health` → `{"status":"ok"}`（JSON のキー順は問わない）
5. ブラウザで `http://localhost:8000/docs` を開く
6. `cd backend` → `ruff check .` → violation 0
7. `pytest tests/ -v` → テスト PASS
8. Genmyaku Auditor（Tier 1 ruff + Tier 2 env_consistency）を `olivo-chat` ルート相対パスで実行し違反 0

## Step 1 で起こりやすい失敗パターン

- pydantic-settings v1 / v2 の API 差（`SettingsConfigDict` を使用）
- Docker ボリュームマウントの遅延・権限
- `.env` の空値による int 変換失敗（`.env.example` で型の分かる値を示す）
- Auditor の `code_root` を `backend/app` に誤らないこと

## Step 2 への引き継ぎ

Alembic 初期化、DDL / RLS migration、`app/models/`・`app/schemas/`、モデルテスト等（設計書 Section 5 参照）。

## 提供物の出所（Provenance）

| ファイル | 出所 |
|---|---|
| 本 TaskBrief | `docs/olivo_chat_design.md` Section 5「実装順序の推奨」に基づく Step 1 の詳細化 |
| .env.example の項目 | 設計書 §4.5「環境変数」を直接転記 |
| pyproject.toml の依存 | 設計書 §4.2「backend/ 詳細」を実装 |
| docker-compose.yml | 設計書 §4.1「リポジトリ全体」+ 開発環境の慣用構成 |
| auditor.yaml | 設計書 §4.6「Render デプロイ」と Genmyaku Auditor Sprint 2.3 の env_consistency 仕様から逆算 |
