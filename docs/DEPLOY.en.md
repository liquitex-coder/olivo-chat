# Olivo Chat — Deployment Guide

| Field | Value |
|---|---|
| Document ID | OLIVO_DEPLOY |
| Scope | FR-D4 deploy **config** (manifests + preflight). Applying it (real hosting) is **cost-gated**. |
| Status | Manifests + preflight done & audit-confirmed; actual hosted deploy pending cost approval. |

> **No charges from this document.** `render.yaml` is a manifest; *applying* it provisions
> a paid web service + managed Postgres. The demo runs free locally (`docker-compose`) or on
> Render's free tier (spin-down). See "Costs" below.

## 1. What's here
- `render.yaml` — Render Blueprint: backend (Docker), managed Postgres, and the two Vite
  static sites (embed, admin). **No secrets are committed**: secret slots use `sync: false`
  (set in the dashboard) and `JWT_SECRET` uses `generateValue`.
- `backend/app/prodcheck.py` — `insecure_env_keys()` / `is_production_ready()`: a preflight
  that refuses dev placeholders in production secret slots (INV-2). Covered by
  `tests/test_deploy_config.py`.

## 2. Local (free, the demo default)
```bash
docker-compose up -d            # db + backend
curl http://localhost:8000/health
# frontends:
cd frontend/embed && npm install && npm run dev   # and likewise frontend/admin
```
Chat uses the offline `DemoChatProvider` and billing uses the offline `DemoBillingProvider`
— **zero external cost**.

## 3. Production (cost-gated — needs approval)
1. Set real secrets in the host (Render dashboard): `ANTHROPIC_API_KEY`, `STRIPE_*`,
   `CORS_ORIGINS`, the `*_BASE_URL`s, and the frontends' `VITE_API_BASE_URL`.
2. Preflight: `is_production_ready(os.environ)` must be `True` (no placeholders left).
3. Apply the blueprint (`render blueprint launch` / connect the repo on Render).
4. To use **live** Claude / Stripe, swap in `AnthropicChatProvider` / `StripeBillingProvider`
   (the cost-gated D2-3 / D3-3 step) — these make billable calls.

## 4. Costs (estimates — verify current pricing; demo-scale, low volume)
| Item | Demo (mock/offline/test-mode) | Live |
|---|---|---|
| Claude API (`claude-haiku-4-5`) | $0 | ≈ $0.003 / reply → a few $ for demo volume |
| Stripe | $0 (test mode) | no fixed fee; ~3.6%/transaction (JP), revenue-linked |
| Hosting (Render) | $0 (local / free tier) | ≈ $7–25 / month for an always-on small service + DB |

## 5. Notes
- The app expects `DATABASE_URL` as `postgresql://…`; `app/db/session.py` adapts it to
  asyncpg and Alembic to psycopg2. Render's `connectionString` works directly.
- RLS: the managed Postgres app role must be **non-superuser, non-BYPASSRLS** for tenant
  isolation to hold (mirrors the local `db/init/00-create-app-user.sql` setup).
