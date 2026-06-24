// Typed client for the OrbitTalent backend. Calls go through the Vite /api proxy.

const BASE = "/api";

export type JobStatus = "draft" | "ready" | "archived";

export type CandidateStage =
  | "new"
  | "ai_screened"
  | "qualified"
  | "shortlisted"
  | "assessment_pending"
  | "assessment_passed"
  | "interview_scheduled"
  | "interview_passed"
  | "final_review"
  | "offer_sent"
  | "hired"
  | "rejected"
  | "withdrawn";

export const CANDIDATE_STAGES: CandidateStage[] = [
  "new", "ai_screened", "qualified", "shortlisted", "assessment_pending",
  "assessment_passed", "interview_scheduled", "interview_passed",
  "final_review", "offer_sent", "hired", "rejected", "withdrawn",
];

// Ordered "happy path" (excludes rejected/withdrawn) — for funnel/board.
export const FUNNEL_STAGES: CandidateStage[] = [
  "new", "ai_screened", "qualified", "shortlisted", "assessment_pending",
  "assessment_passed", "interview_scheduled", "interview_passed",
  "final_review", "offer_sent", "hired",
];

export type RejectionReason =
  | "low_ai_score"
  | "missing_required_skills"
  | "wrong_experience_level"
  | "wrong_location"
  | "country_restriction"
  | "duplicate_application"
  | "recruiter_decision";

export const REJECTION_REASONS: RejectionReason[] = [
  "low_ai_score", "missing_required_skills", "wrong_experience_level",
  "wrong_location", "country_restriction", "duplicate_application",
  "recruiter_decision",
];

export type ScoreStatus =
  | "pending"
  | "processing"
  | "scored"
  | "failed"
  | "filtered_out";

export interface Criteria {
  id: number;
  job_id: number;
  required_skills: string[];
  preferred_skills: string[];
  min_years: number;
  must_haves: string[];
  weights: Record<string, number>;
  // Hiring rules (V2).
  geo_allow: string[];
  geo_block: string[];
  min_degree: string | null;
  preferred_universities: string[];
  min_experience: number | null;
  max_experience: number | null;
  ranking_weights: Record<string, number>;
}

export type EditableCriteria = Omit<Criteria, "id" | "job_id">;

/** Default criteria payload — includes the V2 hiring-rule fields. */
export const EMPTY_CRITERIA: EditableCriteria = {
  required_skills: [],
  preferred_skills: [],
  min_years: 0,
  must_haves: [],
  weights: { required_skills: 0.5, preferred_skills: 0.2, min_years: 0.15, must_haves: 0.15 },
  geo_allow: [],
  geo_block: [],
  min_degree: null,
  preferred_universities: [],
  min_experience: null,
  max_experience: null,
  ranking_weights: {},
};

export interface Job {
  id: number;
  title: string;
  jd_text: string;
  status: JobStatus;
  created_at: string;
  candidate_count: number;
}

export interface JobDetail extends Job {
  criteria: Criteria | null;
}

export interface Candidate {
  id: number;
  job_id: number;
  filename: string;
  ats_score: number | null;
  job_match_pct: number | null;
  overall_score: number | null;
  ats_issues: string[];
  matched_keywords: string[];
  missing_keywords: string[];
  reasoning: string;
  stage: CandidateStage;
  rejection_reason: RejectionReason | null;
  assigned_recruiter_id: number | null;
  score_status: ScoreStatus;
  error: string;
  created_at: string;
  applied_at: string | null;
  // ATS profile (V2).
  country: string | null;
  city: string | null;
  experience_years: number | null;
  education: string | null;
  certifications: string[];
  languages: string[];
  expected_salary: number | null;
  // Cascade telemetry.
  tier_reached: number;
  cache_hit: boolean;
  est_cost_usd: number;
}

export interface CandidateDetail extends Candidate {
  parsed_text: string;
}

export interface StageEvent {
  id: number;
  from_stage: CandidateStage | null;
  to_stage: CandidateStage;
  reason: string;
  by_user_id: number | null;
  at: string;
}

export interface SkillGap {
  keyword: string;
  count: number;
  pct: number;
  example_candidate_ids: number[];
}

export interface FunnelStage {
  stage: string;
  count: number;
  conversion_from_prev: number | null;
}

export interface AutomationRule {
  id: number;
  name: string;
  job_id: number | null;
  trigger_json: Array<Record<string, unknown>>;
  action_json: Record<string, unknown>;
  enabled: boolean;
  priority: number;
}

export interface JobSummary {
  id: number;
  title: string;
  status: JobStatus;
  total_candidates: number;
  hired: number;
  rejected: number;
  avg_overall_score: number | null;
}

export interface Overview {
  total_jobs: number;
  active_jobs: number;
  total_candidates: number;
  total_hired: number;
  total_rejected: number;
  avg_overall_score: number | null;
  top_missing_skills: SkillGap[];
  by_country: Record<string, number>;
  jobs: JobSummary[];
}

export interface CandidateSearchRequest {
  query?: string;
  job_id?: number | null;
  skills?: string[];
  country?: string | null;
  city?: string | null;
  min_experience?: number | null;
  max_experience?: number | null;
  education?: string | null;
  min_score?: number | null;
  max_score?: number | null;
  stage?: CandidateStage | null;
  applied_after?: string | null;
  applied_before?: string | null;
  max_salary?: number | null;
  languages?: string[];
  limit?: number;
  offset?: number;
}

export interface Analytics {
  job_id: number;
  total: number;
  scored: number;
  pending: number;
  filtered_out: number;
  failed: number;
  avg_overall_score: number | null;
  avg_ats_score: number | null;
  avg_job_match_pct: number | null;
  stage_counts: Record<string, number>;
  top_missing_keywords: { keyword: string; count: number }[];
  skill_gaps: SkillGap[];
  funnel: FunnelStage[];
  score_distribution: Record<string, number>;
  by_country: Record<string, number>;
  by_city: Record<string, number>;
  rejection_reasons: Record<string, number>;
  tier_distribution: Record<string, number>;
  cache_hit_rate: number;
  est_total_cost_usd: number;
}

export interface Health {
  status: string;
  llm_enabled: boolean;
  provider: string;
  today_cost_usd: number;
}

export interface User {
  id: number;
  email: string;
  name: string;
  tenant_id: number;
  created_at: string;
}

/** Error carrying the HTTP status so callers can react to 401 etc. */
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include", // send/receive the session cookie
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const api = {
  health: () => req<Health>("/health"),

  // --- Auth ---
  register: (email: string, password: string, name: string) =>
    req<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),
  login: (email: string, password: string) =>
    req<User>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => req<void>("/auth/logout", { method: "POST" }),
  me: () => req<User>("/auth/me"),

  listJobs: () => req<Job[]>("/jobs"),
  createJob: (title: string, jd_text: string) =>
    req<Job>("/jobs", { method: "POST", body: JSON.stringify({ title, jd_text }) }),
  getJob: (id: number) => req<JobDetail>(`/jobs/${id}`),
  deleteJob: (id: number) => req<void>(`/jobs/${id}`, { method: "DELETE" }),
  extractCriteria: (id: number, jd_text?: string) =>
    req<Criteria>(`/jobs/${id}/extract-criteria`, {
      method: "POST",
      body: JSON.stringify({ jd_text: jd_text ?? null }),
    }),
  updateCriteria: (id: number, c: Omit<Criteria, "id" | "job_id">) =>
    req<Criteria>(`/jobs/${id}/criteria`, { method: "PUT", body: JSON.stringify(c) }),

  listCandidates: (jobId: number, stage?: CandidateStage) =>
    req<Candidate[]>(
      `/jobs/${jobId}/candidates${stage ? `?stage=${stage}` : ""}`
    ),
  getCandidate: (id: number) => req<CandidateDetail>(`/candidates/${id}`),
  candidateHistory: (id: number) =>
    req<StageEvent[]>(`/candidates/${id}/history`),
  updateStage: (
    id: number,
    stage: CandidateStage,
    opts?: { reason?: string; rejection_reason?: RejectionReason | null }
  ) =>
    req<Candidate>(`/candidates/${id}/stage`, {
      method: "PATCH",
      body: JSON.stringify({ stage, ...opts }),
    }),
  patchCandidate: (id: number, patch: Partial<Candidate>) =>
    req<Candidate>(`/candidates/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  bulkAction: (body: {
    candidate_ids: number[];
    action: "move_stage" | "reject" | "shortlist" | "export";
    stage?: CandidateStage;
    rejection_reason?: RejectionReason;
    reason?: string;
  }) =>
    req<{ action: string; updated?: number; skipped?: number[]; candidates?: Candidate[] }>(
      "/candidates/bulk",
      { method: "POST", body: JSON.stringify(body) }
    ),

  searchCandidates: (body: CandidateSearchRequest) =>
    req<{ total: number; results: Candidate[] }>("/candidates/search", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  compareCandidates: (ids: number[]) =>
    req<Candidate[]>(`/candidates/compare?ids=${ids.join(",")}`),

  analytics: (jobId: number) => req<Analytics>(`/jobs/${jobId}/analytics`),
  overview: () => req<Overview>("/analytics/overview"),
  exportCsvUrl: (jobId: number) => `${BASE}/jobs/${jobId}/analytics/export`,

  listAutomationRules: (jobId?: number) =>
    req<AutomationRule[]>(`/automation-rules${jobId ? `?job_id=${jobId}` : ""}`),
  createAutomationRule: (body: Omit<AutomationRule, "id">) =>
    req<AutomationRule>("/automation-rules", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateAutomationRule: (id: number, body: Omit<AutomationRule, "id">) =>
    req<AutomationRule>(`/automation-rules/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  deleteAutomationRule: (id: number) =>
    req<void>(`/automation-rules/${id}`, { method: "DELETE" }),
  // Apply rules to a job's existing candidates (rules are not removed).
  applyAutomationRules: (job_id: number, rule_ids?: number[]) =>
    req<{ applied: number; matched_candidate_ids: number[] }>(
      "/automation-rules/apply",
      { method: "POST", body: JSON.stringify({ job_id, rule_ids: rule_ids ?? null }) }
    ),

  // Multipart upload — no JSON Content-Type header.
  uploadCandidates: async (jobId: number, files: FileList): Promise<Candidate[]> => {
    const form = new FormData();
    Array.from(files).forEach((f) => form.append("files", f));
    const res = await fetch(`${BASE}/jobs/${jobId}/candidates`, {
      method: "POST",
      body: form,
      credentials: "include",
    });
    if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
    return res.json();
  },
};
