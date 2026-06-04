# Olivo Chat — Completion Roadmap

| Field | Value |
|---|---|
| Document ID | OLIVO_COMPLETION_ROADMAP |
| Kind | Roadmap + task extraction + audit-confirmed progress dashboard |
| Created | 2026-06-03 |
| Oracle | `docs/REQUIREMENTS_SPEC.en.md` (**signed**, liquitex / 2026-06-03, FR-A…FR-D) |
| Discipline | A task is **Done** only when its acceptance gate (pytest / ruff / RLS test / `env_consistency`) **actually passes**. Progress % counts audit-confirmed Done only — never "I did it". |
| Constraints | (1) **No new charges without explicit approval** — Claude API / Stripe / paid hosting are cost-gated. (2) This is a **sales demo**: forward phases are built against **mocks / dummy data**, not live paid services. |

---

## 1. Roadmap

```
Phase 0  Requirements spec + human signature (re-root)     ✅ signed 2026-06-03
  └─ INV-R1 human-signature gate (bulk pre-approval FR-A…FR-D) ── unblocks all below
Phase 1  Scaffold (FastAPI, settings, compose)             ✅ FR-A
Phase 2  DB layer + RLS tenant isolation (Alembic 0001/02) ✅ FR-B
Phase 3  Auth / JWT (users, refresh rotation, RLS-armed)   ✅ FR-C
Phase 4  Frontend (React/Vite embed + admin) + conv API    ✅ FR-D1
Phase 5  Claude-backed chat responses                      ◐ FR-D2  pipeline ✅ mock / live 💲
Phase 6  Stripe subscription + webhook verification        ◐ FR-D3  pipeline ✅ offline / live 💲 ← this session
Phase 7  Production deploy (real secrets, managed PG)       ⬜ FR-D4  💲 cost-gated → demo only
```

## 2. Tasks (audit-verifiable Done criteria)

Legend: ✅ audit-confirmed · ⬜ not started · 💲 incurs charges → needs approval before live work.

### Phase 3 — Auth / JWT (FR-C) ✅ DONE
| ID | Task | Done gate | Status |
|---|---|---|---|
| C-1 | Migration `0003` (users RLS-off, refresh_tokens RLS-on+FORCE+NULLIF) | `alembic upgrade head` clean; RLS state verified | ✅ |
| C-2 | `User` / `RefreshToken` ORM models | imported, tables created | ✅ |
| C-3 | argon2id password hash/verify | used by signup/login tests | ✅ |
| C-4 | HS256 access JWT encode/decode | claims test green | ✅ |
| C-5 | signup / login / refresh(rotation) / logout endpoints | `test_auth_*` (13) green | ✅ |
| C-6 | `get_current_user` Bearer dep arms RLS; protected GET | `test_protected_endpoint` (4) green | ✅ |
| C-7 | ruff Tier-1 = 0; full suite 27 passed | `ruff check .` = 0; `pytest -q` = 27 | ✅ |

### Phase 4 — Frontend embed + admin (FR-D1) ✅ DONE — no charge
| ID | Task | Done gate | Status |
|---|---|---|---|
| D1-1 | Conversation/message read+create API (auth-scoped, RLS; foreign conv → 404) | `test_conversations_api.py` (5) green | ✅ |
| D1-2 | Vite embed widget (chat UI) against the API | `frontend/embed`: `npm run build` (tsc+vite) + `vitest` (3) green | ✅ |
| D1-3 | Vite admin console (login, conversation list) | `frontend/admin`: `npm run build` + `vitest` (3) green | ✅ |

### Phase 5 — Claude chat (FR-D2) ◐ pipeline done (mock); live cost-gated
| ID | Task | Done gate | Status |
|---|---|---|---|
| D2-1 | Chat service **behind `ChatProvider` interface** (`DemoChatProvider` default; `AnthropicChatProvider` lazy, unwired) + `/chat` endpoint | `test_chat.py` mock provider green | ✅ |
| D2-2 | Persist user + assistant messages (role) under RLS | `test_chat.py` green (2 turns persisted) | ✅ |
| D2-3 | *(approval-gated)* swap in `AnthropicChatProvider` + live smoke test | manual, **only after cost approval** | ⬜ 💲 |

### Phase 6 — Stripe billing (FR-D3) ◐ pipeline done (offline); live cost-gated
| ID | Task | Done gate | Status |
|---|---|---|---|
| D3-1 | Subscription checkout + webhook signature verification behind `BillingProvider` (`DemoBillingProvider` default, real Stripe-compatible HMAC-SHA256 verify; `StripeBillingProvider` lazy, unwired) | `test_billing.py` (checkout, webhook upgrade, bad-signature 400) green | ✅ |
| D3-2 | Plan gating (`tenants.plan` free/pro/business; `/billing/premium` 402 until paid) | `test_billing.py` (gating + ranking) green | ✅ |
| D3-3 | *(approval-gated)* swap in `StripeBillingProvider` + live test-mode wiring | **only after cost approval** | ⬜ 💲 |

### Phase 7 — Deploy (FR-D4) ⬜ 💲 cost-gated
| ID | Task | Done gate | Note |
|---|---|---|---|
| D4-1 | Deploy manifests, real-secret wiring, managed-PG `DATABASE_URL` | config validated; no placeholders in prod path | mocks/dummy for demo |
| D4-2 | *(approval-gated)* actual hosted deploy | **only after cost approval** | 💲 |

## 3. Progress (audit-confirmed, Done only)

| Phase | Reqs | Done | Progress |
|---|---:|---:|---:|
| Phase 0 signature | 1 | 1 | 100% ✅ |
| Phase 1 scaffold (FR-A) | 3 | 3 | 100% ✅ |
| Phase 2 DB+RLS (FR-B) | 6 | 6 | 100% ✅ |
| Phase 3 Auth (FR-C) | 7 | 7 | 100% ✅ |
| Phase 4 Conv API + frontends (FR-D1) | 1 | 1 | 100% ✅ |
| Phase 5 chat pipeline (FR-D2, mock) | — | — | pipeline ✅ / live ⬜ 💲 |
| Phase 6 billing pipeline (FR-D3, offline) | — | — | pipeline ✅ / live ⬜ 💲 |
| Phase 7 + live activations (FR-D2/3/4) | 3 | 0 | 0% ⬜ 💲 |
| **Signed scope done (FR-A…C + D1)** | **17** | **17** | **100% ✅** |
| **Full product (FR-A…FR-D)** | **20** | **17** | **85%** |

```
Full product (Olivo completion)  [██████████████████████░░░] 85%  (17/20 reqs audit-confirmed)
Phase 1 Scaffold   [██████████████████████████] 100% ✅
Phase 2 DB + RLS   [██████████████████████████] 100% ✅
Phase 3 Auth/JWT   [██████████████████████████] 100% ✅  (pytest green, ruff 0)
Phase 4 Frontend   [██████████████████████████] 100% ✅  (5 pytest + 2× build/vitest)
Phase 5 Claude     [████████████████████░░░░░]  pipeline ✅ mock · live 💲 approval
Phase 6 Stripe     [████████████████████░░░░░]  pipeline ✅ offline · live 💲 approval
Phase 7 Deploy     [░░░░░░░░░░░░░░░░░░░░░░░░░░]   0% 💲  demo only; hosting = approval
```

> **85% is requirement-count, audit-confirmed (41 pytest + ruff + 2 frontend builds).**
> The chat (FR-D2) and billing (FR-D3) *pipelines* are mock/offline-complete and tested;
> the remaining work is the **cost-gated live activations** (real Claude, live Stripe, paid
> hosting) plus deploy manifests (FR-D4). Next no-charge step: **FR-D4 deploy manifests**
> (config only); live activations need cost approval.

---

*Roadmap derived from the signed `REQUIREMENTS_SPEC.en.md` under the Claim-Auditor
discipline. Progress reflects only gates that actually passed (27 pytest + ruff 0 this
session). Cost-incurring work stops for approval (FR-D2/D3/D4).*
