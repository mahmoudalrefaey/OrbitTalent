<p align="center">
  <img src="frontend\src\assets\logo-full.png" alt="OrbitTalent" width="420" />
</p>

<p align="center">
  AI-assisted applicant tracking and CV screening for recruiters.
</p>

---

## Table of Contents

- [What OrbitTalent Is](#what-orbittalent-is)
- [What's Inside](#whats-inside)
- [How It Works Internally](#how-it-works-internally)
  - [The Scoring Cascade](#the-scoring-cascade)
  - [The Per-CV Pipeline](#the-per-cv-pipeline)
  - [Deterministic Engines](#deterministic-engines)
  - [The LLM Layer](#the-llm-layer)
  - [Data Model](#data-model)
  - [Multi-Tenancy & Isolation](#multi-tenancy--isolation)
  - [Request Lifecycle](#request-lifecycle)
  - [Frontend Architecture](#frontend-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [API Surface](#api-surface)
- [Running Locally](#running-locally)
- [Development Workflow](#development-workflow)
- [Design Decisions & Trade-offs](#design-decisions--trade-offs)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

---

## What OrbitTalent Is

OrbitTalent is a **multi-tenant applicant tracking system (ATS)** that screens CVs
against a job description and produces an explainable, ranked shortlist. The core
problem it solves: a recruiter facing hundreds of CVs needs to know *which ones
are worth a human's time* — and *why* — without paying to run an expensive
language model over every résumé.

The recruiter's journey is:

1. **Create a job** and paste the job description.
2. **Extract hiring criteria** — the system reads the description and proposes
   required/preferred skills, minimum experience, and must-haves for review.
3. **Upload a batch of CVs** (PDF, DOCX, or TXT).
4. **Receive, per candidate:** an overall fit score (1–10), a job-match percentage,
   an ATS-readiness score, matched/missing skills, and a short rationale.
5. **Work the pipeline** — move candidates through stages, reject with reasons,
   apply automation rules, compare side-by-side, and read analytics.

The defining idea is **cost-optimized cascade scoring**: cheap, deterministic
checks filter out clearly unqualified candidates *before* any paid model is
called, and the expensive model only ever runs on the candidates that warrant it.
Most CVs are resolved for free.

---

## What's Inside

| Capability | What it does |
|------------|--------------|
| **Cascade scoring** | Four tiers (deterministic rules → lexical similarity → cheap model → deep model). Each CV exits at the cheapest tier that yields a confident answer. Per-candidate cost is tracked. |
| **AI criteria extraction** | Turns a free-text job description into structured, screenable criteria for the recruiter to confirm or edit. |
| **Full ATS lifecycle** | Thirteen candidate stages (`new` → … → `hired`, plus `rejected`/`withdrawn`), with an append-only history that powers funnel and conversion analytics. |
| **Rejection workflow** | Candidates filtered by the cascade are auto-moved to `rejected` with a machine-set reason; visible in a dedicated view. |
| **Automation rules** | Recruiter-defined conditions (score, experience, location, missing-skill count, …) that auto-reject, auto-advance, or auto-assign candidates after scoring. |
| **Bulk actions** | Move, reject, shortlist, or export many candidates at once. |
| **Search & comparison** | Structured filters plus free-text (BM25) ranking; side-by-side comparison of up to four candidates. |
| **Analytics** | Per-job dashboards (funnel, conversion, score distribution, skill gaps, geography) and an org-wide rollup, with CSV export. |
| **Usage & cost tracking** | Every model call records token counts and an estimated cost, rolled up per candidate, per job, and per tenant. |
| **Auth & isolation** | Email/password auth with JWT session cookies; every record is scoped to the owning tenant. Per-IP rate limiting on auth endpoints. |

---

## How It Works Internally

This section explains the mechanics — the part a new contributor needs to
understand the system, not just operate it.

### The Scoring Cascade

The cascade (`services/cascade.py`) is the heart of OrbitTalent. For each CV it
runs a sequence of tiers and **stops at the first one that can answer
confidently**, so paid model calls are the exception, not the rule.

```
  Tier 0  ── deterministic gate ───────────────────────────────  free
            parse + ATS score + required-skill keyword coverage
            └─ matches none of the required skills? → filtered_out (stop)

  Tier 1  ── lexical similarity gate ──────────────────────────  free
            BM25(CV vs JD) + weighted skill overlap, scored 0–100
            └─ below the similarity threshold? → filtered_out (stop)

  Tier 2  ── cheap model: screen + score in one call ──────────  low cost
            returns match%, self-reported confidence, gaps, summary
            └─ confident AND not a top candidate? → scored (stop)

  Tier 3  ── deep model: precise score + enrichment ───────────  high cost
            1–10 overall, rationale, matched/missing skills, and
            profile fields (country, experience, education, …)
```

Two rules govern the Tier-2 → Tier-3 decision:

- A **confident** cheap score (`confidence ≥ tier2_accept_confidence`) is accepted
  as final — *unless* the candidate looks strong.
- A **strong** candidate (`match_pct ≥ tier3_escalate_match_pct`) always escalates
  to the deep model, because top matches deserve a precise, defensible score.

Every threshold (`TIER0_MIN_COVERAGE`, `TIER1_MIN_SIMILARITY`,
`TIER2_ACCEPT_CONFIDENCE`, `TIER3_ESCALATE_MATCH_PCT`) is configurable, so you can
trade cost against thoroughness without touching code.

### The Per-CV Pipeline

`services/pipeline.py` orchestrates one candidate end-to-end. It runs as a
**background task** (FastAPI `BackgroundTasks`) so the upload request returns
immediately (`202 Accepted`) while scoring proceeds asynchronously. The frontend
polls until each candidate leaves the `pending`/`processing` state.

```
upload → row created (status: pending)
            │
            ▼  background task (own DB session + LLM service)
   1. parse_cv()        extract text + structural signals
   2. score_ats()       ATS-readiness (0–100), always runs
   3. match_keywords()  matched / missing skills, always runs
   4. run_cascade()     Tier 0→3 (only if an LLM service is configured)
   5. cost telemetry    sum usage rows written during this run
   6. auto-reject       if filtered_out → move to `rejected` stage
   7. automation rules  evaluate tenant/job rules on the final state
            │
            ▼
   row updated (status: scored | filtered_out | failed)
```

Key resilience properties:

- **One bad CV never sinks the batch.** The pipeline catches exceptions per
  candidate and records the error on that row (`status: failed`).
- **The deterministic layer always runs.** Even with no LLM key configured, every
  CV still gets an ATS score and keyword match; it simply stays `pending` instead
  of receiving an AI score.
- **Uploads are bounded.** A rolling 24-hour per-tenant quota and a per-file size
  cap are enforced *before* any row is created, so an oversized or excessive batch
  is rejected atomically rather than partially processed.

### Deterministic Engines

These run with no network calls and are independently unit-tested — they're what
make Tiers 0–1 free.

- **`cv_parser.py`** — dispatches on file extension to pdfplumber (PDF),
  python-docx (DOCX), or plain decode (TXT). It extracts text *and* structural
  signals (page count, word count, presence of images/tables) that the ATS scorer
  consumes. It never raises; parse failures are surfaced as a field on the result.
- **`ats_scorer.py`** — scores *CV hygiene* (would an automated parser read this
  cleanly?), independent of the job: contact info present, standard sections,
  sensible length, structural hazards like multi-column tables or image-only text.
- **`keyword_matcher.py`** — word-boundary-aware skill matching with an alias map
  (so `js`/`javascript`, `k8s`/`kubernetes`, `c#`/`.net` all unify) and correct
  handling of symbol-bearing tokens like `c++` and `node.js`.
- **`similarity.py`** — a from-scratch **Okapi BM25** implementation plus weighted
  skill overlap (required skills count double preferred). Powers both the Tier-1
  gate and free-text search ranking. Deterministic and zero-cost, chosen because
  the target LLM endpoint exposes no embedding models.

### The LLM Layer

`services/llm.py` wraps an **OpenAI-compatible** chat endpoint and exposes three
operations: `extract_criteria` (JD → criteria), `quick_score` (Tier 2), and
`deep_score` (Tier 3). It is defined as a `Protocol`, so tests substitute a fake
implementation with no network access.

Notable internals:

- **Structured output without native JSON mode.** Rather than rely on a provider
  feature that not every gateway supports, it prompts for a strict JSON object,
  extracts it from the response (tolerating code fences/prose), and validates
  against a Pydantic schema — retrying once with a stricter nudge on bad JSON.
- **Model fallbacks.** If the primary model errors, configured fallback models are
  tried in order before giving up. A failed call returns a safe default so the
  pipeline degrades rather than crashes.
- **Cost accounting on every call.** Token counts are normalized across provider
  response shapes and written as usage rows, which the analytics layer aggregates.

### Data Model

Defined in `models.py` (SQLAlchemy). The central entities:

```
Tenant 1──1 User                  (each user owns exactly one tenant = isolation boundary)
   │
   ├──* Job ──1 ScoringCriteria    (required/preferred skills, min years, hiring rules)
   │      │
   │      └──* Candidate           (scores, profile fields, stage, cascade telemetry)
   │             └──* StageEvent   (append-only stage-transition history)
   │
   ├──* AutomationRule             (JSON conditions + action; tenant- or job-scoped)
   └──* UsageRecord                (one row per LLM call: tokens, tier, cost)
```

- A **Candidate** carries three distinct scores — `ats_score` (0–100, hygiene),
  `job_match_pct` (0–100, fit), and `overall_score` (1–10, hire-worthiness) — plus
  cascade telemetry (`tier_reached`, `cache_hit`, `est_cost_usd`) and
  LLM-extracted profile fields (country, experience, education, languages, …).
- **StageEvent** is append-only and is the single source of truth for funnel,
  conversion-rate, and time-in-stage analytics. Every stage change — manual, bulk,
  or automation — flows through one helper (`candidate_service.change_stage`) so
  no transition goes unrecorded.
- **Automation rules** store their conditions and action as JSON, so the rule
  vocabulary can grow without database migrations.

### Multi-Tenancy & Isolation

Isolation is enforced at the query layer, not by middleware:

- Each registered user gets their **own tenant**; the 1:1 mapping is the
  data-isolation boundary.
- Every router resolves the caller via an auth dependency (`deps.py`) and then
  fetches records through ownership-checking helpers (`_owned_job`,
  `_owned_candidate`, …) or filters explicitly on `tenant_id`.
- Cross-tenant access returns **404, not 403**, so the existence of another
  tenant's records is never revealed (IDOR-safe).

### Request Lifecycle

1. The browser sends a request with the `ot_session` cookie (httpOnly).
2. The auth dependency decodes the JWT, loads the user, and resolves the tenant —
   or returns `401`.
3. The router validates the body against a Pydantic schema, performs the
   ownership check, and runs the business logic (often delegating to a service).
4. The response is serialized through a Pydantic response model — which also
   guarantees sensitive fields (e.g. password hashes) are never emitted.

Auth endpoints (`/auth/login`, `/auth/register`) additionally pass through a
small in-memory, per-IP sliding-window rate limiter to blunt brute-force and
credential-stuffing attempts.

### Frontend Architecture

A **React + TypeScript SPA** built with Vite.

- **Data layer:** a single typed API client (`api/client.ts`) wraps `fetch`,
  attaches credentials, and maps non-2xx responses to a typed `ApiError`. All
  server state flows through **TanStack Query**, which handles caching,
  background refetching, and — for candidates still scoring — polling until the
  status settles.
- **Auth:** an `AuthProvider` context hydrates the session once on load (via
  `/auth/me`) and exposes `login`/`register`/`logout`. A `RequireAuth` route
  guard gates the authenticated area.
- **Routing:** React Router with a marketing/auth/app split. The app area uses
  nested layouts (an app shell, then a tabbed job workspace).
- **Single origin in production:** the client always calls a relative `/api/*`
  path. In development a Vite proxy forwards that to the backend; in production a
  host-level rewrite does the same. Because the browser only ever sees one
  origin, the `SameSite=Lax` session cookie works without cross-site cookie
  configuration.

---

## Technology Stack

**Backend** — Python · FastAPI · SQLAlchemy ORM · Alembic · PostgreSQL · PyJWT +
bcrypt · OpenAI SDK (against an OpenAI-compatible endpoint) · pdfplumber +
python-docx · pytest.

**Frontend** — React · TypeScript · Vite · TanStack Query · Tailwind CSS · Framer
Motion · Recharts · React Router.

---

## Project Structure

```
OrbitTalent/
├── backend/
│   ├── alembic/                 Database migrations
│   ├── app/
│   │   ├── routers/             API endpoints (auth, jobs, candidates,
│   │   │                        analytics, search, automation)
│   │   ├── services/            Business logic
│   │   │   ├── cascade.py       Tiered scoring orchestration
│   │   │   ├── pipeline.py      Per-CV scoring pipeline (background task)
│   │   │   ├── similarity.py    BM25 + skill-overlap engine
│   │   │   ├── llm.py           LLM client (structured output, fallbacks)
│   │   │   ├── ats_scorer.py    ATS-readiness scoring
│   │   │   ├── cv_parser.py     PDF/DOCX/TXT text extraction
│   │   │   ├── keyword_matcher.py
│   │   │   ├── automation.py    Automation-rule evaluation
│   │   │   ├── candidate_service.py  Stage transitions + history
│   │   │   ├── analytics_service.py  Aggregation helpers
│   │   │   ├── ratelimit.py     Per-IP auth rate limiter
│   │   │   ├── auth.py          Password hashing + session JWTs
│   │   │   └── usage.py         Token / cost tracking
│   │   ├── models.py            SQLAlchemy models
│   │   ├── schemas.py           Pydantic request/response models
│   │   ├── config.py            Settings (env-driven)
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
└── README.md
```

---

## API Surface

All application endpoints require an authenticated session (the `ot_session`
cookie); registration and login are public. The full interactive schema is at
`/docs` when the backend is running.

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
| GET | `/health` | Liveness and provider info |

---

## Running Locally

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+

### Backend

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Create a `backend/.env` (see [Configuration](#configuration)). The defaults work
for local development; the one value worth setting immediately is `LLM_API_KEY`
to enable AI scoring.

### Frontend

```bash
cd frontend
npm install
```

### Run both (separate terminals)

```bash
# Terminal 1 — backend
cd backend && . .venv/Scripts/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

The app is served at `http://localhost:5173` and proxies `/api` to the backend on
port 8000. Interactive API docs are at `http://localhost:8000/docs`. For local
development the app auto-creates any missing tables on startup; in any real
deployment, migrations (`alembic upgrade head`) are authoritative.

### Try it

1. Register an account and create a job, pasting in the job description.
2. On the job's Settings tab, extract criteria with AI or enter them manually,
   then confirm.
3. On the Candidates tab, upload CVs and watch them score in real time.
4. Review the ranked list, drill into candidates, move them through stages, or
   apply bulk actions.
5. Explore the Analytics, Skill Gaps, and Rejected tabs.

---


### Deployment shape (conceptual)

In production the **frontend is served as a static SPA** and the **backend runs
behind a TLS-terminating reverse proxy**, so the browser only ever talks to a
single HTTPS origin that rewrites `/api/*` to the backend. The backend process
itself binds to localhost and is reached only through the proxy. This README
intentionally omits host-specific provisioning steps — see internal operations
docs for environment specifics.

---

## Development Workflow

Run the backend tests (no network required; LLM calls are stubbed):

```bash
cd backend && pytest
```

Type-check and build the frontend:

```bash
cd frontend && npm run build
```

After changing SQLAlchemy models, generate and apply a migration:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

---

## Design Decisions & Trade-offs

- **Why a cascade instead of one model call per CV?** Cost. The deterministic
  tiers are free and resolve the majority of CVs (obvious non-matches and clear
  fits), so paid calls concentrate on the genuinely borderline middle. Cost is
  tracked per candidate so the savings are visible.
- **Why BM25 instead of embeddings?** The target LLM endpoint exposes no
  embedding models, and lexical ranking is deterministic, offline, and free — a
  good fit for a gate that must run on every CV.
- **Why background tasks instead of a job queue?** Simplicity at current volume.
  Uploads return immediately and the frontend polls. A dedicated async queue is on
  the roadmap for higher throughput.
- **Why one tenant per user?** It makes isolation trivial to reason about for the
  MVP. Team accounts (many users per tenant, with roles) are a planned evolution.
- **Why JSON-prompt structured output instead of native JSON mode?** Portability
  across OpenAI-compatible gateways that may not implement tool/JSON mode; the
  validate-and-retry loop keeps it robust.

---

## Troubleshooting

- **AI scoring disabled / criteria extraction returns 503** — `LLM_API_KEY` is not
  set. Deterministic scoring still runs without it.
- **403 from the LLM provider** — the configured model isn't available on your
  plan. Set `MODEL_DEEP`/`MODEL_CHEAP` to ids the provider serves, or add
  `FALLBACK_MODELS`.
- **`JWT_SECRET is using the insecure dev default` warning** — set `JWT_SECRET`.
- **No candidates ever reach a given tier** — adjust the matching `TIER*`
  threshold; one set too permissively means that gate never fires.
- **`429` on upload** — the rolling 24h per-tenant upload quota is exhausted, or
  the batch exceeds the remaining quota.

---

## Roadmap

- Team accounts: multiple recruiters per tenant, with roles and shared pipelines.
- Email / ATS ingestion of candidates in addition to manual upload.
- An asynchronous job queue to replace in-process background tasks at volume.
- Password reset and email verification.
- Richer export formats (Excel, PDF) beyond CSV.
