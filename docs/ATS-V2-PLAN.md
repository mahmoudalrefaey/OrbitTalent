# OrbitTalent V2 — ATS Expansion: Audit, Architecture & Roadmap

> Planning deliverable. This document audits the current system against the V2 ATS
> request and proposes schema/API/frontend changes plus a phased roadmap. **Nothing
> here is built yet** — it's the plan to review and sequence before implementation.

---

## 0. Audit — what exists today (grounded in current code)

**Data model (`backend/app/models.py`)**
- `Tenant` (per-user, isolation boundary) · `User` (email, bcrypt hash, 1:1 tenant).
- `Job` (title, jd_text, `JobStatus` = draft|ready|archived, tenant_id).
- `ScoringCriteria` (1:1 job): `required_skills[]`, `preferred_skills[]`, `min_years`, `must_haves[]`, `weights{}` (JSON dict).
- `Candidate`: filename, parsed_text, `ats_score`, `job_match_pct`, `overall_score`, `ats_issues[]`, `matched_keywords[]`, `missing_keywords[]`, `reasoning`, `tier_reached`, `cache_hit`, `est_cost_usd`, `stage`, `score_status`, `error`, `created_at`.
- `UsageRecord` (per-LLM-call tokens + cost).
- Enums: **`CandidateStage` = new | shortlisted | interview | rejected** (only 4) · `ScoreStatus` = pending | processing | scored | failed | filtered_out.

**API (`backend/app/routers/`)** — all tenant-scoped behind auth:
- jobs: `POST/GET /jobs`, `GET /jobs/{id}`, `POST /jobs/{id}/extract-criteria`, `PUT /jobs/{id}/criteria`
- candidates: `POST /jobs/{id}/candidates` (upload), `GET /jobs/{id}/candidates`, `GET /candidates/{id}`, `PATCH /candidates/{id}/stage`
- analytics: `GET /jobs/{id}/analytics` → total, scored/pending/filtered/failed, avg overall/ats/match, `stage_counts`, `top_missing_keywords` (Counter, top 10), `tier_distribution`, `cache_hit_rate`, `est_total_cost_usd`
- usage: `GET /usage` · auth: register/login/logout/me

**Frontend (`frontend/src/`)**
- Per-job nav already exists in `app-layout.tsx` (`JobNav`: Setup / Candidates / Analytics) — a natural seed for "job workspaces."
- `Analytics.tsx`: 8 stat cards + pipeline **pie** + Top Missing Skills **bar** + tier-distribution **bar** (recharts). Per-job only; no global dashboard.
- `CandidatesDashboard.tsx`: list with score/ATS meters, a **stage filter dropdown** (all/new/shortlisted/interview/rejected), polling, upload, per-row `StageSelect`. No bulk actions, no multi-select.

### Gap summary (what the V2 ask needs that does NOT exist)
| Area | Missing today |
|---|---|
| Candidate fields | country, city, experience_years, education, certifications[], languages[], expected_salary, rejection_reason, assigned_recruiter, applied_at (distinct from created_at) |
| Stages | only 4; ATS spec wants 13 |
| Rejection | `filtered_out` candidates are kept but there's no reason tracking or a dedicated rejected view/analytics |
| Workspaces | no per-job Dashboard/Skill-Gaps/Interviews/Rejected/Shortlist sub-pages; no **global** dashboard |
| Bulk actions | none |
| Automation | none (no rules engine) |
| Config center | criteria editing exists; no geography/education/experience rule config or weighted AI ranking UI |
| Search | stage filter only; no multi-filter or semantic search |
| Comparison | none |
| Analytics | no funnel, conversion rates, score distribution, skills trends, geography, recruiter metrics; no filters/drill-down/export on charts |

---

## 1. UX/UI redesign proposal (high level)

**Information architecture shift:** from "a job has 3 tabs" → **Global workspace + per-job workspaces**.

```
/app                      Global dashboard (all jobs, org-wide KPIs)
/app/jobs                 Jobs list
/app/jobs/:id             Job workspace shell (tabbed)
  ├── overview            Job dashboard (KPIs for this job)
  ├── candidates          Pipeline board / table (bulk actions, filters)
  ├── candidates/:cid     Candidate detail
  ├── compare?ids=...     Side-by-side comparison
  ├── analytics           Funnel, conversions, score dist, skill gaps, geo
  ├── skill-gaps          Dedicated skill-gap drill-down (table + heatmap)
  ├── interviews          Interview-stage subset
  ├── rejected            Rejected list + reasons + rejection analytics
  ├── automation          Per-job automation rules
  └── settings            Criteria + hiring rules + AI ranking weights
/app/search               Cross-job advanced + semantic search
/app/settings             Account/appearance/usage (existing)
```

- **Candidates view:** add a **Kanban board** mode (columns = stages) alongside the existing table mode; both get a multi-select checkbox column + a bulk-action toolbar (move stage / reject-with-reason / shortlist / export).
- **Top Missing Skills redesign:** replace the single cramped bar with a **sortable data table** (skill, # affected, % missing, drill-down link) as the primary, plus an optional **horizontal bar** (top N, with "show all" in the table) and a **treemap** toggle. Tooltips show affected-count, %, and example candidates. Per-chart **filter bar** (stage, date range) + **export** (CSV first; Excel/PDF later).
- Reuse existing design system (`components/ui/*`, `common.tsx`, recharts, framer-motion). No new component library.

---

## 2. Database schema updates

**Extend `Candidate`** (new nullable columns — safe, additive):
`country`, `city`, `experience_years` (float), `education` (str), `certifications` (JSON[]), `languages` (JSON[]), `expected_salary` (int), `rejection_reason` (enum/str, null unless rejected), `assigned_recruiter_id` (FK users, null), `applied_at` (datetime, defaults to created_at). Most can be LLM-extracted from the CV at scoring time (extend the deep-score schema) or entered manually.

**Replace `CandidateStage` enum** (4 → 13): new, ai_screened, qualified, shortlisted, assessment_pending, assessment_passed, interview_scheduled, interview_passed, final_review, offer_sent, hired, rejected, withdrawn. *Migration must map old values* (shortlisted→shortlisted, interview→interview_scheduled, rejected→rejected, new→new).

**New tables:**
- `automation_rules` (tenant_id, job_id nullable, name, trigger_json, action_json, enabled, priority) — JSON-defined conditions/actions, evaluated by the engine.
- `hiring_rules` / extend `ScoringCriteria` with: `geo_allow[]`, `geo_block[]`, `min_degree`, `preferred_universities[]`, `min_experience`, `max_experience`, and a richer `weights{}` (skill→%, plus experience/education/culture/project importance).
- `rejection_reasons` can be an enum on Candidate rather than a table (simpler).
- (Later) `stage_events` (candidate_id, from_stage, to_stage, at, by_user, reason) — append-only history that powers **funnel + conversion + time-in-stage + recruiter metrics**. **This is the single most important new table** for the analytics asks.

**Migrations:** Alembic, additive first (new columns/tables), then the enum swap with explicit value mapping. Current head: `8dfbe6a35a72` (users).

---

## 3. Backend API changes

- **Candidates:** `PATCH /candidates/{id}` (edit fields incl. rejection_reason, assignment), `POST /candidates/bulk` (action: move_stage|reject|shortlist|export over an id list, tenant-checked), keep stage history via `stage_events` on every change.
- **Search:** `POST /candidates/search` (structured filters: skills, country, city, experience range, education, score range, stage, date range, salary, languages) returning a tenant-scoped, paginated result. **Semantic search:** reuse the existing embeddings tier (`llm.embed`) — embed the query + candidates, rank by cosine. Gated on `MODEL_EMBED` being set (degrades to keyword search otherwise).
- **Comparison:** `GET /candidates/compare?ids=...` returns the normalized fields for 2–4 candidates.
- **Analytics expansion:** new endpoints/params on `GET /jobs/{id}/analytics` and a new `GET /analytics/overview` (global). Add: funnel (counts per stage from `stage_events`), conversion rates (stage→stage), score distribution (histogram buckets), avg score by job, geography aggregates, recruiter metrics (jobs managed, candidates reviewed, avg response time from stage_events, hire rate), skills intelligence (common/missing/coverage). Accept filter params (job, stage, date range) and an `?format=csv` for export.
- **Automation:** `CRUD /automation-rules`; an evaluation hook in `pipeline.process_candidate` (after scoring) that applies matching auto-reject/auto-progress rules and writes a `stage_event` with reason. Auto-assign on candidate creation.
- **Settings:** `GET/PUT /jobs/{id}/hiring-rules` and global defaults; the AI ranking weights feed `cascade`/scoring.

---

## 4. Frontend architecture updates

- **Job workspace shell:** a `JobLayout` (nested route under `/app/jobs/:id`) with a tab bar; child routes = overview/candidates/analytics/skill-gaps/interviews/rejected/automation/settings. Expand `JobNav` accordingly.
- **Global dashboard** at `/app` (replace the current jobs-list-as-home or add above it): org KPIs + per-job cards.
- **State/data:** introduce a lightweight query layer (TanStack Query) to replace the ad-hoc `useEffect`+`useState`+polling pattern — needed once there are many filtered/paginated lists. (Currently no data-fetching library.)
- **New components:** DataTable (sortable, selectable, paginated), Kanban board, FilterBar, multi-select + BulkActionBar, comparison grid, funnel chart, treemap (recharts `Treemap`), heatmap. CSV export util (client-side first).
- Reuse `common.tsx` badges/meters; extend `StageSelect`/`StatusTag` for the 13 stages and rejection reasons.

---

## 5. ATS workflow implementation plan

1. Expand stage enum + `stage_events` history table + migration (with value mapping).
2. Rejection workflow: rejection_reason on candidate, dedicated Rejected view, rejection analytics — **replaces the current "filtered candidates disappear" behavior** (they already persist as `filtered_out`; surface them).
3. Bulk actions (API + BulkActionBar).
4. Candidate field enrichment (LLM extraction at scoring time + manual edit).
5. Per-job workspace tabs.

## 6. Analytics redesign plan

1. Fix Top Missing Skills first (table + bar + treemap toggle, filters, CSV) — the stated pain point.
2. Add funnel + conversion (needs `stage_events`).
3. Score distribution + skills intelligence.
4. Geography + recruiter metrics + global overview dashboard.
5. Export (CSV → Excel/PDF).

## 7. Recruiter settings architecture

A per-job **Hiring Rules** + **AI Ranking** config (stored on `ScoringCriteria`/`hiring_rules`), plus tenant-level defaults. Weighted skills + importance sliders feed the scoring prompt/criteria. Geography/education/experience filters feed both scoring and automation.

## 8. Automation engine architecture

Rules = `{trigger: conditions[], action}` stored as JSON. Evaluated (a) at scoring time in `pipeline.process_candidate` for auto-reject/auto-progress, (b) at creation for auto-assign. Each action writes a `stage_event` (auditable). Start with a small fixed condition vocabulary (score, experience, skills-missing-count, country, salary) and the actions reject/progress/shortlist/assign — not a general rules DSL.

---

## 9. Prioritized roadmap

### Phase 1 — Critical (foundation + the stated pain points)
- Expand `CandidateStage` (13) + add `rejection_reason`; migration with value mapping.
- **`stage_events` history table** (unlocks funnel/conversions/recruiter metrics later).
- **Rejected Candidates view** + rejection reasons + basic rejection analytics.
- **Redesign Top Missing Skills** → sortable table + bar/treemap toggle + filters (stage, date) + **CSV export**.
- **Bulk actions** (multi-select + move/reject/shortlist/export).
- Candidate enrichment: extract country/experience/education/etc. during scoring; manual edit endpoint.

### Phase 2 — Important (workspaces, funnel, config, search)
- **Dedicated job workspaces** (tabbed JobLayout: overview/candidates/analytics/skill-gaps/interviews/rejected/settings) + **global dashboard**.
- **Candidate funnel + pipeline conversion rates** + AI score distribution.
- **Recruiter Configuration Center**: hiring rules (geo/education/experience), weighted skills, AI ranking importance.
- **Advanced search** (structured multi-filter).
- TanStack Query + DataTable/Kanban refactor.

### Phase 3 — Advanced (intelligence, automation, semantic, comparison)
- **Automation engine** (auto-reject / auto-progress / auto-assign rules + UI).
- **Semantic search** (embeddings-backed).
- **Candidate comparison center** (side-by-side).
- **Skills intelligence** (trends/coverage) + **diversity & geography** insights + **recruiter performance** dashboards.
- Export to Excel/PDF.

---

## Notes & risks
- **Scope:** this is ~a quarter+ of engineering, not a single change. Recommend executing one Phase-1 item at a time, each as its own reviewed PR.
- **Multi-recruiter caveat:** "assign to recruiters" / "recruiter performance" imply **multiple users per tenant**. Today it's 1 user = 1 tenant. Supporting teams needs a membership model (users↔tenant many-to-many + roles) — a prerequisite to flag before Phase 2/3 recruiter features.
- **Data availability:** geography/salary/education/experience analytics are only as good as what's extracted from CVs; LLM extraction will be imperfect — allow manual correction.
- **g0i.ai semantic search** depends on an embeddings model being available on the plan (`MODEL_EMBED`); not yet verified.
