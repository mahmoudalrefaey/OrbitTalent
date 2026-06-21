// Typed client for the OrbitTalent backend. Calls go through the Vite /api proxy.

const BASE = "/api";

export type JobStatus = "draft" | "ready" | "archived";
export type CandidateStage = "new" | "shortlisted" | "interview" | "rejected";
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
}

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
  score_status: ScoreStatus;
  error: string;
  created_at: string;
  // Cascade telemetry.
  tier_reached: number;
  cache_hit: boolean;
  est_cost_usd: number;
}

export interface CandidateDetail extends Candidate {
  parsed_text: string;
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
  tier_distribution: Record<string, number>;
  cache_hit_rate: number;
  est_total_cost_usd: number;
}

export interface UsagePerDay {
  date: string;
  cost_usd: number;
  calls: number;
  cached_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
}

export interface Usage {
  provider: string;
  today_cost_usd: number;
  last_7_days_cost_usd: number;
  total_calls: number;
  cache_hit_rate: number;
  by_day: UsagePerDay[];
  by_tier: Record<string, number>;
  by_model: Record<string, number>;
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
  usage: () => req<Usage>("/usage"),

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
  extractCriteria: (id: number, jd_text?: string) =>
    req<Criteria>(`/jobs/${id}/extract-criteria`, {
      method: "POST",
      body: JSON.stringify({ jd_text: jd_text ?? null }),
    }),
  updateCriteria: (id: number, c: Omit<Criteria, "id" | "job_id">) =>
    req<Criteria>(`/jobs/${id}/criteria`, { method: "PUT", body: JSON.stringify(c) }),

  listCandidates: (jobId: number) => req<Candidate[]>(`/jobs/${jobId}/candidates`),
  getCandidate: (id: number) => req<CandidateDetail>(`/candidates/${id}`),
  updateStage: (id: number, stage: CandidateStage) =>
    req<Candidate>(`/candidates/${id}/stage`, {
      method: "PATCH",
      body: JSON.stringify({ stage }),
    }),

  analytics: (jobId: number) => req<Analytics>(`/jobs/${jobId}/analytics`),

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
