# Olivo Chat — Requirements Specification (要件定義書)

| Field | Value |
|---|---|
| Document ID | OLIVO_REQUIREMENTS_SPEC |
| Kind | Requirements specification, authored under the Claim-Auditor discipline (claimed-vs-actual, B-anchor backward derivation, auditor-verifiable AC) |
| Version | 0.1.0 |
| Status | **DRAFT — not human-signed.** Not a binding oracle until §13 is signed (INV-R1). |
| Created | 2026-06-03 |
| Upstream sources | `docs/olivo_chat_design.md` (WHY/tech stack), `docs/Olivo_Step1/2/3_TaskBrief.md` (WHAT/AC), `auditor.yaml` (Track B config), `manifesto/olivo.yaml` (Tier-3 principles) |
| Self-application | A requirement counts as **Done** only when its acceptance criterion **actually passes** an auditor-checkable gate (pytest / ruff / RLS isolation test / `env_consistency`), never because a document or commit says so. Progress % counts audit-confirmed Done only. |

---

## 1. Purpose and outcome anchor (B)

### 1.1 Product
Olivo Chat is a **multi-tenant SaaS** that gives restaurants an embeddable chat widget
plus an admin console (a sales demo built around the sample tenant *Trattoria Olivo*).

### 1.2 Outcome anchor B (結末アンカー)
Following the Auditor's backward-derivation model, every requirement is derived from a
single target outcome **B**, against which "done" is measured:

> **B = A restaurant operator can sign up, embed the widget, and have end-customers hold
> a Claude-backed chat — with each tenant's conversations, messages, and billing strictly
> isolated from every other tenant, provably (RLS-enforced) and auditably (Silent
> Assurance, Track B).**

The current state **A** is: scaffold + DB layer with tenant isolation proven by tests.
The gap **B∖A** (what is not yet built) is the implementation backlog in §4. Tenant
isolation is the **non-negotiable invariant on the path A→B** (INV-1); any requirement
that would weaken it is an *infeasibility* to escalate, not a trade-off (see §11).

## 2. Scope

### 2.1 In scope (this spec governs)
Backend SaaS foundation: scaffold, DB schema + RLS, authentication (JWT), and the
auditor integration that guards them. Frontend, Claude chat, and Stripe billing are
**named here as forward requirements** (so the B-anchor is complete) but their detailed
AC are deferred to their own signed step-specs.

### 2.2 Out of scope (explicit non-goals for the signed step)
Email verification, password reset, SSO/OAuth, rate limiting, CAPTCHA, 2FA, RBAC
(admin/member), password-strength estimation, session-list UI, and all frontend code.
(From `Olivo_Step3_TaskBrief §4 "やらない"`.)

## 3. Personas
- **Operator** — restaurant owner/admin; signs up, configures, reads billing.
- **End-customer** — diner chatting via the embedded widget (no account).
- **Platform/auditor** — CI + Claim-Auditor (Track B) verifying claimed-vs-actual.

## 4. Functional requirements

Legend — status is **claimed-vs-actual**: ✅ audit-confirmed Done · 🟡 designed, not
implemented · ⬜ forward requirement (B-anchor only, AC deferred to its step-spec).

### FR-A · Scaffold (Step 1)
| ID | Requirement | Acceptance criterion (auditor-checkable) | Status |
|---|---|---|---|
| FR-A1 | FastAPI app boots under Docker Compose (`db` + `backend`) | `docker compose up -d` then `GET /health` → `{"status":"ok"}` | ✅ |
| FR-A2 | `GET /version` returns version + configured Claude model | response includes `CLAUDE_MODEL` from settings | ✅ |
| FR-A3 | `pydantic-settings` `Settings` declares every `.env.example` key, no orphan fields | `env_consistency` (Tier-2): 0 MISSING, ≤1 known WARN (`VITE_API_BASE_URL`) | ✅ |

### FR-B · Database layer + tenant isolation (Step 2 / 2.1)
| ID | Requirement | Acceptance criterion | Status |
|---|---|---|---|
| FR-B1 | Alembic-managed schema: `tenants`, `conversations`, `messages` (UUIDv4 PK, `ON DELETE CASCADE`, `updated_at` triggers) | `alembic upgrade head` clean; `\d` matches spec | ✅ |
| FR-B2 | RLS `tenant_isolation` on `conversations` + `messages`, `FORCE ROW LEVEL SECURITY` | `pg_policies` shows 2 policies | ✅ |
| FR-B3 | `set_tenant_context()` sets `app.current_tenant_id` via `set_config(..., is_local=true)` | tenant-context unit path exercised by RLS test | ✅ |
| FR-B4 | A session scoped to tenant A cannot read tenant B's rows; unset context → 0 rows | `pytest tests/test_rls_isolation.py` PASS (3) | ✅ |
| FR-B5 | `NULLIF(current_setting(...),'')` guard so an empty GUC (post-`RESET`) leaks nothing | migration `0002_harden_rls_nullif` present + RLS test green | ✅ |
| FR-B6 | SQLAlchemy 2.x ORM + Pydantic v2 `*Base/*Create/*Read` for all three tables | `pytest tests/test_db_models.py` PASS (5) | ✅ |

### FR-C · Authentication / JWT (Step 3) — **designed, not implemented**
| ID | Requirement | Acceptance criterion | Status |
|---|---|---|---|
| FR-C1 | Migration `0003`: `users` (RLS **off**) + `refresh_tokens` (RLS **on** + NULLIF guard) | `alembic upgrade head` clean; `users` RLS off, `refresh_tokens` RLS on+FORCE | 🟡 |
| FR-C2 | `POST /api/v1/auth/signup` creates tenant + first user in one transaction | `test_auth_signup.py` (4): 201+tokens; dup `(tenant_id,email)`/`slug`→409; short pw→422/400 | 🟡 |
| FR-C3 | `POST /api/v1/auth/login` (argon2id verify, generic 401) | `test_auth_login.py` (4): success; wrong pw→401 "Invalid credentials"; unknown email→401; claims `sub/tid/exp/iat/typ=access` | 🟡 |
| FR-C4 | `POST /api/v1/auth/refresh` with **rotation** (old revoked, new issued) | `test_auth_refresh_rotation.py` (3): rotate; `revoked_at` set; reused old→401 | 🟡 |
| FR-C5 | `POST /api/v1/auth/logout` revokes the presented refresh token | `test_auth_logout.py` (2): revoke; reused→401 | 🟡 |
| FR-C6 | `get_current_user` Bearer dependency calls `set_tenant_context(jwt.tid)` → arms RLS | `test_protected_endpoint.py` (4): no-auth→401; per-tenant rows only; expired→401 | 🟡 |
| FR-C7 | Refresh tokens stored as SHA-256 hash only; access stateless; HS256 via `JWT_SECRET` | no raw token in DB (schema review); access TTL 900s, refresh 2 592 000s | 🟡 |

### FR-D · Forward requirements (B-anchor only — AC deferred to signed step-specs)
| ID | Requirement | Status |
|---|---|---|
| FR-D1 | Conversation/message API consumed by the embed + admin frontends (React/Vite) | ⬜ |
| FR-D2 | Claude-backed chat responses using `ANTHROPIC_API_KEY` / `CLAUDE_MODEL` | ⬜ |
| FR-D3 | Stripe subscription + webhook signature verification (`STRIPE_*` env) | ⬜ |
| FR-D4 | Production deploy: real secrets, managed Postgres `DATABASE_URL` (no dev placeholders) | ⬜ |

## 5. Non-functional requirements / invariants (do not break)
- **INV-1 Tenant isolation** — every tenant-scoped table is RLS-protected with `FORCE` +
  NULLIF guard; cross-tenant reads are impossible even for the table owner. This is the
  load-bearing invariant of B; weakening it is an infeasibility (§11), not a trade-off.
- **INV-2 No plaintext secrets** — refresh tokens stored hashed; `JWT_SECRET` and all
  `*_KEY/*_SECRET` come from env, never committed. `docker-compose` defaults are
  obvious placeholders and MUST be replaced for prod (FR-D4).
- **INV-3 Env consistency** — `app/config.py` ⇄ `.env.example` stay in sync; the only
  accepted divergence is the documented `VITE_API_BASE_URL` WARN (frontend-only var).
- **INV-4 Claimed == actual** — CI runs Claim-Auditor D1 (`commit_message_reality`) and
  D2 (`cross_file_consistency`); a commit message or cross-file mount that contradicts
  the real diff is rejected (the `fca06a1` regression class).
- **INV-5 Determinism of isolation tests** — RLS tests run under `FORCE ROW LEVEL
  SECURITY` so the owner role cannot mask a leak.

## 6. Data model requirements
Authoritative tables and columns are in `Olivo_Step2_TaskBrief §2` (tenants /
conversations / messages) and `Olivo_Step3_TaskBrief §2` (users / refresh_tokens).
This spec requires: UUIDv4 PKs, `ON DELETE CASCADE` FKs, redundant `tenant_id` on
`messages` (single-table RLS filter, no join), and `messages` immutable (no
`updated_at`).

## 7. Security requirements
argon2id password hashing (8–128 chars, lowercased email); HS256 access JWT
(`sub/tid/typ=access/iat/exp`); opaque random refresh token (`secrets.token_urlsafe(48)`)
stored as SHA-256; rotation on refresh; generic 401 that does not reveal account
existence; `users` reachable only through the auth router (enforced by review + auditor).

## 8. Auditor integration (Track B — Silent Assurance)
Per `auditor.yaml`: Track B, `silent` default mode, independent hallucination tracking,
Tier-1 `ruff`, Tier-2 `env_consistency` (`.env.example` ⇄ `backend/app`), Tier-3
manifesto (`manifesto/olivo.yaml`, currently an empty principle skeleton — see §11-G3),
regime `spec_evolving`. Process detectors D1 (`commit_message_reality`) and D2
(`cross_file_consistency`) run in CI. **Definition of Done for any FR = its AC gate
passes AND the auditor emits no new claim.**

## 9. Definition of Done (per step)
A step is Done when, on a fresh container: `alembic upgrade head` is clean · all
targeted pytest pass · `ruff check .` = 0 · the auditor run is PASS (≤ the one known
`VITE_API_BASE_URL` WARN) · D1/D2 emit 0 claims.

## 10. Traceability (requirement → design → test)
| FR group | Design source | Verifying tests |
|---|---|---|
| FR-A | design §3, §4.3, §4.5 | `test_health.py` (2) |
| FR-B | design §4.4 + Step2 brief | `test_db_models.py` (5), `test_rls_isolation.py` (3) |
| FR-C | Step3 brief §1–§8 | `test_auth_*` ×4 + `test_protected_endpoint.py` (planned 17) |
| FR-D | design §5, §4.6 | (deferred to step-specs) |

## 11. Gaps and infeasibility findings (claimed-vs-actual, auditor self-applied)
- **G1 (gap, expected):** FR-C (Auth) is **designed but unimplemented** — no
  `backend/app/auth/`, no `User`/`RefreshToken` models, no migration `0003`, no auth
  tests. The 27-test target (10 existing + 17 new) is **not yet actual**; only the 10
  Step-2 tests exist. Counting FR-C as Done would be a false claim.
- **G2 (doc drift, low):** design §4.5 still tabulates `VITE_API_BASE_URL` as a backend
  env var, but it was deliberately removed from `Settings` (commit `f7a48f2`). This is
  the source of the one *accepted* `env_consistency` WARN; keep it documented so the
  WARN is never mistaken for new drift.
- **G3 (manifesto stub, medium):** `manifesto/olivo.yaml` has `principles: []`, so Tier-3
  ethical enforcement is effectively inert despite `enforcement_level: strict`. Either
  populate principles (e.g. tenant-data-isolation, no-secret-logging) or record that the
  strict level is intentionally vacuous for the demo.
- **No A↛B infeasibility detected:** every B-anchor requirement has a feasible path under
  the stated stack; nothing in scope contradicts INV-1.

## 12. Progress dashboard (audit-confirmed, Done only)
Counted from static inspection of the repo (models, migrations, file presence) and the
recorded Step-2 `10/10` result. Full pytest re-execution needs a running Postgres, which
this container does not provide; FR-B is therefore marked audit-confirmed on schema +
test-presence, to be re-confirmed by `pytest` in CI.

| Layer | Reqs | Audit-confirmed Done | Progress |
|---|---:|---:|---:|
| FR-A Scaffold | 3 | 3 | **100% ✅** |
| FR-B DB + isolation | 6 | 6 | **100% ✅** |
| FR-C Auth/JWT | 7 | 0 | **0% 🟡 (designed)** |
| FR-D Forward (B-anchor) | 4 | 0 | **0% ⬜ (deferred)** |
| **Backend (A→Auth scope)** | **16** | **9** | **≈56%** |

```
Backend foundation (scaffold→auth)  [██████████████░░░░░░░░░░░░] 56%  (9/16 audit-confirmed)
FR-A Scaffold        [██████████████████████████] 100% ✅
FR-B DB + isolation  [██████████████████████████] 100% ✅
FR-C Auth / JWT      [░░░░░░░░░░░░░░░░░░░░░░░░░░]   0% 🟡 designed, not built
FR-D Forward         [░░░░░░░░░░░░░░░░░░░░░░░░░░]   0% ⬜ deferred to step-specs
```

> The % is **audit-confirmed, not self-reported**: FR-C is designed in detail but no test
> passes yet, so it is 0% Done. The honest next milestone is implementing FR-C to its AC
> gate (target 27 pytest green) under the same Done discipline.

## 13. Signature / re-root gate — **UNSIGNED (draft)**
This spec is **not** a binding oracle until a human signs it (INV-R1). Until then it
guides but does not authorize "Done" claims.

| Signature | Where | Effect | State |
|---|---|---|---|
| Requirements approval (re-root) | this §13 | makes this the trusted SOURCE; unblocks FR-C implementation as signed scope | ⬜ **unsigned** |

> Signer: ____________  Date: ____________  Scope: FR-A … FR-D as written above.
> Any later re-definition of a requirement requires a **fresh** signature (INV-R1).

## 14. References
`docs/olivo_chat_design.md` · `docs/Olivo_Step1/2/3_TaskBrief.md` · `auditor.yaml` ·
`manifesto/olivo.yaml` · `backend/migrations/versions/0001_initial_schema.py`,
`0002_harden_rls_nullif.py` · PostgreSQL RLS (v16) · PyJWT · passlib argon2.

---

*Authored under the Claim-Auditor discipline: requirements derived backward from the
outcome anchor B, each with an auditor-verifiable AC, progress counted only where an
audit gate actually passes. Draft until §13 is human-signed (INV-R1).*
