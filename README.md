# 🛰️ OrbitTalent

HR CV-screening tool. Upload a batch of CVs against a job posting and get an
explainable ranked dashboard: a **1–10 overall score**, a **job-match %**, an
**ATS-readiness score**, keyword matching, pipeline stages, and analytics.

Multi-tenant with real authentication: each user signs up, gets their own
isolated tenant, and only ever sees their own jobs/candidates/usage.

## Authentication

- Email/password sign up + sign in. Passwords hashed with **bcrypt**.
- Sessions are **JWTs in an httpOnly, SameSite=Lax cookie** (`ot_session`),
  signed with `JWT_SECRET`. Set `COOKIE_SECURE=true` behind HTTPS.
- **Each user = own tenant.** Every app endpoint (`/jobs`, `/candidates`,
  `/analytics`, `/usage`) requires a valid session and is scoped to the
  caller's tenant; by-id access to another tenant's data returns 404.
- Endpoints: `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`,
  `GET /auth/me`. Self-signup is open.
- **Set `JWT_SECRET` in the environment before deploying** — the dev default is
  insecure and logs a warning.

## How scoring works (cost-optimized cascade)

Every CV runs through a tiered cascade (`services/cascade.py`). Each candidate
**exits at the cheapest tier that yields a confident answer**, so the expensive
model runs on only a small fraction of CVs:

| Tier | What | Cost | Implemented in |
|---|---|---|---|
| **0** | Parse + ATS readiness + keyword coverage. CVs matching none of the required skills are filtered out here. | **free** | `cv_parser`, `ats_scorer`, `keyword_matcher` |
| **1** | *(optional)* Embedding similarity gate between the role and the CV. Disabled unless `MODEL_EMBED` is set. | cheap | `cascade.run_cascade` + `llm.embed` |
| **2** | One **cheap-model** call that combines pre-filter + score (match %, confidence, gaps). If confidence is high and the candidate isn't a top match, we accept and stop here. | cheap | `llm.quick_score` |
| **3** | **Deep-model** precise 1–10 overall score + reasoning, only for borderline or strong candidates worth the spend. | expensive | `llm.deep_score` |

Deterministic steps (Tier 0) always run. LLM tiers run only when `LLM_API_KEY`
is set; without it candidates still get ATS + keyword results.

The per-job criteria block is sent as a **prompt-cached** system block, so a
whole batch of CVs is billed for the criteria once. Tuning thresholds
(`TIER0_MIN_COVERAGE`, `TIER2_ACCEPT_CONFIDENCE`, …) are env-configurable.

### Cost tracking

Every LLM call records token counts + an estimated USD cost (`UsageRecord`,
`services/usage.py`). See it at `GET /usage` and in per-job analytics
(`tier_distribution`, `cache_hit_rate`, `est_total_cost_usd`). Prices are a
configurable per-model table in settings — tune them to your provider's rates.

## LLM provider

LLM traffic uses the **OpenAI SDK** against an **OpenAI-compatible endpoint**
(g0i.ai, chosen for cost). The client is pointed at `LLM_BASE_URL` (default
`https://api.g0i.ai/v1` — the `/v1` suffix is required). The API key is read
from `LLM_API_KEY` **(env only — never hardcoded)**. If a primary model errors,
the models in `FALLBACK_MODELS` are tried in order.

`MODEL_DEEP` / `MODEL_CHEAP` must be ids your g0i.ai plan allows — list them
with the provider's `/v1/models` endpoint. Structured output (criteria/scores)
is obtained by prompting for strict JSON and validating against Pydantic
(retry once on bad JSON), so it works on any OpenAI-compatible chat model.

> ⚠️ **Privacy:** all CV text (candidate PII) is sent to whatever `LLM_BASE_URL`
> points at. Only configure a provider you trust to process personal data
> (relevant for GDPR and similar regimes).

## Backend

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add LLM_API_KEY to enable AI scoring
uvicorn app.main:app --reload --port 8000
```

API docs at http://localhost:8000/docs. With the default SQLite URL the DB is
created automatically on startup.

### PostgreSQL + migrations (Alembic)

SQLite is the zero-config dev default. For production use Postgres:

```bash
# 1. point at your database
export DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/orbittalent"
# 2. create/upgrade the schema (includes the users table for auth)
alembic upgrade head
# 3. run the app
uvicorn app.main:app --port 8000
```

> Already running an older Postgres DB? Run `alembic upgrade head` again to
> add the `users` table introduced with authentication.

The engine uses a real connection pool (`pool_pre_ping`, recycling) for
non-SQLite URLs. After changing models, generate a migration with
`alembic revision --autogenerate -m "describe change"` and apply it with
`alembic upgrade head`.

### Tests

```bash
cd backend
pytest                                  # unit + API integration (no network)
LLM_API_KEY=sk-... pytest tests/test_llm_smoke.py -s   # optional live check
```

## Frontend

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173 (proxies /api -> :8000)
```

## Using it

1. **Jobs** → create a job, paste the job description.
2. **Setup** → "Extract criteria with AI" (or fill in manually), edit the
   skills/weights, confirm.
3. **Candidates** → upload CVs (PDF/DOCX/TXT), watch them score in real time,
   sort the ranked table, drill into any candidate, move them through pipeline
   stages.
4. **Analytics** → per-job stats, stage breakdown, top skill gaps.

## Stack

FastAPI · SQLAlchemy · Alembic · PostgreSQL (SQLite for dev) · JWT auth
(bcrypt + httpOnly cookie) · OpenAI SDK against an OpenAI-compatible gateway
(g0i.ai by default) · React · TypeScript · Vite · Tailwind · Framer Motion ·
Recharts.

## Deferred to post-MVP

Auth/login, enforced multi-tenant isolation, real billing/payments, an async
job queue for high volume, email/ATS ingestion.
