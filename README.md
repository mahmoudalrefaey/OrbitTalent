# 🛰️ OrbitTalent

HR CV-screening tool. Upload a batch of CVs against a job posting and get an
explainable ranked dashboard: a **1–10 overall score**, a **job-match %**, an
**ATS-readiness score**, keyword matching, pipeline stages, and analytics.

V1 is a single-tenant MVP. The data model is tenant-scoped from day one so
multi-tenant SaaS is a later switch, not a rewrite.

## How scoring works (hybrid)

Every CV runs through this pipeline (one background task per CV):

1. **Parse** — PDF / DOCX / TXT → text + structure (`services/cv_parser.py`).
2. **ATS-readiness** (deterministic, free) — parse-ability, contact info,
   sections, length, structural hazards → 0–100 (`services/ats_scorer.py`).
3. **Keyword match** (deterministic, free) — criteria keywords vs CV text,
   with aliases → matched / missing (`services/keyword_matcher.py`).
4. **Cheap pre-filter** (Claude Haiku) — quick relevance gate; clearly
   unrelated CVs are filtered out before expensive scoring.
5. **Deep score** (Claude Opus) — 1–10 overall, job-match %, reasoning.

Deterministic steps always run. LLM steps run only when `ANTHROPIC_API_KEY` is
set; without it, candidates still get ATS + keyword results.

The per-job criteria block is sent as a **prompt-cached** system block, so a
whole batch of CVs is billed for the criteria once.

## Backend

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add ANTHROPIC_API_KEY to enable AI scoring
uvicorn app.main:app --reload --port 8000
```

API docs at http://localhost:8000/docs. SQLite DB is created automatically.

### Tests

```bash
cd backend
pytest                                  # unit + API integration (no network)
ANTHROPIC_API_KEY=sk-... pytest tests/test_llm_smoke.py -s   # optional live check
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

FastAPI · SQLAlchemy · SQLite · Anthropic SDK (`claude-opus-4-8`,
`claude-haiku-4-5`) · React · TypeScript · Vite · Recharts.

## Deferred to post-MVP

Auth/login, enforced multi-tenant isolation, billing, an async job queue for
high volume, email/ATS ingestion, Postgres.
