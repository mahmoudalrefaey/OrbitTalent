<p align="center">
  <img src="frontend\src\assets\logo-full.png" alt="OrbitTalent" width="420" />
</p>

<p align="center">
  AI-assisted applicant tracking and CV screening for recruiters.
</p>

---

## Project Overview

OrbitTalent is a multi-tenant ATS (applicant tracking system) that screens CVs
against a job description and surfaces an explainable, ranked shortlist. A
recruiter creates a job, lets the system extract structured hiring criteria from
the job description, uploads a batch of CVs, and receives — for each candidate —
an overall fit score, a job-match percentage, an ATS-readiness score, matched
and missing skills, and a short rationale.

Scoring runs through a cost-optimized cascade: cheap deterministic checks filter
out clearly unqualified candidates before any paid model is called, and the
expensive model only scores the candidates that warrant it. Every account is an
isolated tenant, so recruiters only ever see their own jobs and candidates.

## Key Features

- **Cascade scoring** — four tiers (deterministic rules, lexical similarity, a
  cheap model pass, a deep model pass) so most CVs never reach the expensive
  model. Per-candidate cost is tracked and shown in analytics.
- **AI criteria extraction** — paste a job description and the system extracts
  required/preferred skills, minimum experience, and must-haves for review.
- **Full ATS lifecycle** — thirteen candidate stages from `new` through `hired`,
  with an append-only stage history that powers funnel and conversion analytics.
- **Rejection workflow** — candidates filtered by the cascade are moved to a
  `rejected` stage with a reason, visible in a dedicated rejected view.
- **Automation rules** — auto-reject, auto-advance, or auto-assign candidates
  based on score, experience, location, and other conditions.
- **Bulk actions** — move, reject, shortlist, or export many candidates at once.
- **Search and comparison** — structured filters plus free-text (BM25) ranking,
  and side-by-side comparison of up to four candidates.
- **Analytics** — per-job dashboards (funnel, conversion, score distribution,
  skill gaps, geography) and an organization-wide overview, with CSV export.
- **Authentication and isolation** — email/password auth with JWT session
  cookies; every record is scoped to the owning tenant.

## Architecture Overview

```
                         Browser (React SPA)
                                |
                      Vite dev server / static host
                                |  /api proxy
                                v
                         FastAPI application
        ┌───────────────────────┼───────────────────────────┐
        |                       |                            |
   Auth & tenancy        Scoring pipeline              Analytics & search
   (JWT cookie,          (cascade, background          (aggregation,
    per-user tenant)      task per CV)                  BM25 ranking)
        |                       |                            |
        └───────────────────────┼───────────────────────────┘
                                |
                       SQLAlchemy + Alembic
                                |
                            PostgreSQL

   Scoring cascade calls out to an OpenAI-compatible LLM endpoint (g0i.ai).
```

The scoring cascade is the core of the system. For each uploaded CV, a
background task runs the following tiers and stops at the cheapest one that
yields a confident answer:

| Tier | What it does | Cost | Where |
|------|--------------|------|-------|
| 0 | Parse the file, score ATS-readiness, and check required-skill keyword coverage. CVs that match none of the required skills stop here. | free | `cv_parser`, `ats_scorer`, `keyword_matcher` |
| 1 | Deterministic lexical similarity between the CV and the job description (BM25 plus weighted skill overlap). Poor matches stop here. | free | `similarity`, `cascade` |
| 2 | A single cheap-model call that screens and scores in one shot. If the model is confident and the candidate is not a top match, this score is final. | low | `llm.quick_score` |
| 3 | A deep-model call producing a precise 1–10 score, rationale, and profile enrichment, only for borderline or strong candidates. | high | `llm.deep_score` |

Candidates filtered at any tier are moved to the `rejected` stage. Automation
rules are evaluated after scoring completes.

## Technology Stack

**Backend**

- Python, FastAPI
- SQLAlchemy ORM, Alembic migrations
- PostgreSQL
- PyJWT and bcrypt for authentication
- OpenAI SDK targeting an OpenAI-compatible endpoint
- pdfplumber and python-docx for CV parsing
- pytest for tests

**Frontend**

- React, TypeScript, Vite
- TanStack Query for data fetching and caching
- Tailwind CSS for styling
- Framer Motion for animation
- Recharts for charts
- React Router for navigation

## Installation Guide

### Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer
- PostgreSQL 14 or newer

### Backend

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Create a `backend/.env` file with the variables listed under
[Environment Configuration](#environment-configuration). The defaults work for
local development; the only value worth setting immediately is `LLM_API_KEY` to
enable AI scoring.

### Frontend

```bash
cd frontend
npm install
```

## Environment Configuration

Backend configuration is read from `backend/.env`. Create that file with the
values below:

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_API_KEY` | for AI scoring | API key for the LLM endpoint. Without it, only deterministic scoring runs. |
| `LLM_BASE_URL` | no | OpenAI-compatible endpoint. Defaults to `https://api.g0i.ai/v1` (the `/v1` suffix is required). |
| `MODEL_DEEP` | no | Model id for the deep (Tier 3) pass. Defaults to `gpt-4o`. |
| `MODEL_CHEAP` | no | Model id for the cheap (Tier 2) pass. Defaults to `gpt-4o-mini`. |
| `FALLBACK_MODELS` | no | Comma-separated model ids tried in order if the primary errors. |
| `JWT_SECRET` | in production | Secret used to sign session cookies. The dev default is insecure and logs a warning. |
| `JWT_EXPIRE_DAYS` | no | Session lifetime in days (default 7). |
| `COOKIE_SECURE` | no | Set `true` when serving over HTTPS so the cookie gets the `Secure` flag. |
| `DATABASE_URL` | yes | PostgreSQL connection URL, e.g. `postgresql+psycopg://user:pass@host:5432/orbittalent`. |
| `CORS_ORIGINS` | no | Comma-separated allowed origins (default covers the Vite dev server). |
| `TIER0_MIN_COVERAGE`, `TIER1_MIN_SIMILARITY`, `TIER2_ACCEPT_CONFIDENCE`, `TIER3_ESCALATE_MATCH_PCT` | no | Cascade tuning thresholds. |

Generate a strong `JWT_SECRET` with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Privacy note:** CV text (which contains candidate personal data) is sent to
whatever `LLM_BASE_URL` points at. Only configure a provider you are permitted
to share that data with.

## Running the Application

Run the backend and frontend in separate terminals.

```bash
# Terminal 1 — backend
cd backend
. .venv/Scripts/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

The app is served at `http://localhost:5173` and proxies `/api` to the backend
on port 8000. Interactive API documentation is available at
`http://localhost:8000/docs`.

Create the database schema before first run with `alembic upgrade head` (see
Deployment Instructions). The application also creates any missing tables on
startup as a convenience for local development.

### Using the application

1. Register an account and create a job, pasting in the job description.
2. On the job's Settings tab, extract criteria with AI or enter them manually,
   then confirm.
3. On the Candidates tab, upload CVs (PDF, DOCX, or TXT) and watch them score in
   real time.
4. Review the ranked list, drill into candidates, move them through stages, or
   apply bulk actions.
5. Use the Analytics, Skill Gaps, and Rejected tabs to review the pipeline.

## Project Structure

```
OrbitTalent/
├── backend/
│   ├── alembic/                 Database migrations
│   ├── app/
│   │   ├── routers/             API endpoints (auth, jobs, candidates,
│   │   │                        analytics, search, automation, usage)
│   │   ├── services/            Business logic
│   │   │   ├── cascade.py       Tiered scoring orchestration
│   │   │   ├── similarity.py    BM25 + skill-overlap engine
│   │   │   ├── llm.py           LLM client (structured output, fallbacks)
│   │   │   ├── pipeline.py      Per-CV scoring pipeline
│   │   │   ├── automation.py    Automation rule evaluation
│   │   │   ├── analytics_service.py
│   │   │   ├── candidate_service.py
│   │   │   ├── cv_parser.py     PDF/DOCX/TXT text extraction
│   │   │   ├── ats_scorer.py    ATS-readiness scoring
│   │   │   ├── keyword_matcher.py
│   │   │   └── usage.py         Token/cost tracking
│   │   ├── models.py            SQLAlchemy models
│   │   ├── schemas.py           Pydantic request/response models
│   │   ├── config.py            Settings
│   │   ├── db.py                Engine and session
│   │   ├── deps.py              Auth dependency
│   │   └── main.py              Application entry point
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/               Route components
│   │   ├── components/          Layouts, UI primitives, shared widgets
│   │   ├── context/             Auth provider
│   │   ├── api/client.ts        Typed API client
│   │   └── lib/                 Utilities
│   └── package.json
└── docs/                        Documentation and assets
```

## API Overview

All application endpoints require an authenticated session (the `ot_session`
cookie). Registration and login are public.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create an account and tenant; sets the session cookie |
| POST | `/auth/login` | Authenticate; sets the session cookie |
| POST | `/auth/logout` | Clear the session cookie |
| GET | `/auth/me` | Current user |
| GET / POST | `/jobs` | List or create jobs |
| GET | `/jobs/{id}` | Job detail with criteria |
| POST | `/jobs/{id}/extract-criteria` | Extract criteria from the job description |
| PUT | `/jobs/{id}/criteria` | Save criteria and hiring rules |
| POST | `/jobs/{id}/candidates` | Upload CVs (multipart) |
| GET | `/jobs/{id}/candidates` | List candidates (optional `?stage=`) |
| GET / PATCH | `/candidates/{id}` | Candidate detail or partial edit |
| PATCH | `/candidates/{id}/stage` | Change stage (records history) |
| GET | `/candidates/{id}/history` | Stage-change history |
| POST | `/candidates/bulk` | Bulk move/reject/shortlist/export |
| POST | `/candidates/search` | Structured + free-text search |
| GET | `/candidates/compare` | Compare 2–4 candidates (`?ids=1,2,3`) |
| GET | `/jobs/{id}/analytics` | Per-job analytics |
| GET | `/jobs/{id}/analytics/export` | Candidates as CSV |
| GET | `/analytics/overview` | Organization-wide rollup |
| GET / POST | `/automation-rules` | List or create rules |
| PUT / DELETE | `/automation-rules/{id}` | Update or delete a rule |
| GET | `/usage` | Token usage and cost summary |
| GET | `/health` | Liveness and provider info |

The full, interactive schema is available at `/docs` when the backend is
running.

## Deployment Instructions

OrbitTalent targets PostgreSQL in production.

1. Provision a PostgreSQL database and set `DATABASE_URL`:

   ```bash
   export DATABASE_URL="postgresql+psycopg://user:password@host:5432/orbittalent"
   ```

2. Set a real `JWT_SECRET` and `COOKIE_SECURE=true` (assuming HTTPS).

3. Create the schema:

   ```bash
   cd backend
   alembic upgrade head
   ```

4. Serve the API with a production server, for example:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

5. Build the frontend and serve the static output behind a web server or CDN,
   proxying `/api` to the backend:

   ```bash
   cd frontend
   npm run build      # output in frontend/dist
   ```

The database engine uses connection pooling with liveness checks
(`pool_pre_ping`).

## Configuration Options

- **LLM provider** — point `LLM_BASE_URL` at any OpenAI-compatible endpoint and
  set `MODEL_DEEP` / `MODEL_CHEAP` to ids that provider serves. Structured
  output is produced by prompting for JSON and validating it, so native
  tool/JSON-mode support is not required.
- **Cascade thresholds** — tune `TIER1_MIN_SIMILARITY` and the other `TIER*`
  variables to trade cost against thoroughness. Lower thresholds send more
  candidates to the paid models.
- **Cost estimates** — per-model pricing lives in `config.py` (`price_*`
  fields) and can be overridden via environment variables to match your
  provider's rates.

## Development Workflow

Run the backend tests (no network required; LLM calls are stubbed):

```bash
cd backend
pytest
```

An optional live smoke test against the real provider runs only when a key is
present:

```bash
LLM_API_KEY=sk-... pytest tests/test_llm_smoke.py -s
```

Type-check and build the frontend:

```bash
cd frontend
npm run build
```

After changing SQLAlchemy models, generate and apply a migration:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## Troubleshooting

- **AI scoring is disabled / criteria extraction returns 503** — `LLM_API_KEY`
  is not set. Deterministic scoring still runs without it.
- **403 from the LLM provider** — the configured model is not available on your
  plan. Set `MODEL_DEEP` / `MODEL_CHEAP` to ids the provider serves (list them
  at the provider's `/v1/models` endpoint) or add `FALLBACK_MODELS`.
- **`JWT_SECRET is using the insecure dev default` warning** — set `JWT_SECRET`
  in the environment.
- **Duplicate key on `tenants_pkey` during registration** — the tenant id
  sequence is out of sync, usually from manually seeded rows. Reset it with
  `SELECT setval(pg_get_serial_sequence('tenants','id'), COALESCE((SELECT MAX(id) FROM tenants),0)+1, false);`.
- **No candidates ever reach a given tier** — adjust the corresponding `TIER*`
  threshold; a threshold set too permissively means that gate never fires.

## Future Enhancements

- Team accounts: multiple recruiters within a single tenant, with roles and
  candidate assignment across a shared pipeline.
- Email and ATS ingestion of candidates in addition to manual upload.
- An asynchronous job queue to replace in-process background tasks at higher
  volume.
- Password reset and email verification.
- Richer export formats (Excel, PDF) beyond CSV.
