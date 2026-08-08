const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => res.statusText);
    throw new Error(`API ${path} → ${res.status}: ${body}`);
  }
  // 204 No Content
  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  db: boolean;
  user_email: string;
}

export interface Stats {
  total_jds: number;
  total_matches: number;
  total_copies: number;
  pending_checkpoints: number;
}

export interface JobActivity {
  stats: Stats;
  recent_jds: Array<{
    id: string;
    source: string;
    company: string | null;
    title: string;
    location: string | null;
    url: string | null;
    scraped_at: string;
  }>;
  recent_matches: Array<{
    id: string;
    composite_score: number;
    position_context: string;
    created_at: string;
    scraped_jds: { company: string | null; title: string; source: string } | null;
  }>;
  targets: Array<{
    id: string;
    company_name: string;
    role_title: string | null;
    status: string;
    created_at: string;
    updated_at: string | null;
  }>;
  drafts: Array<{
    id: string;
    subject: string;
    created_at: string;
    outreach_targets: { company_name: string; role_title: string | null; status: string };
  }>;
  traces: Array<{
    id: string;
    jd_id: string | null;
    agent_name: string;
    log: string | null;
    created_at: string;
  }>;
}

export interface Position {
  id: string;
  title: string;
  fuzzy_keywords: string[];
  is_active: boolean;
  created_at: string;
}

export interface JdMatch {
  id: string;
  jd_id: string;
  position_context: string;
  keyword_score: number;
  semantic_score: number;
  llm_score: number;
  composite_score: number;
  gap_analysis: string;
  matched_skills: string[];
  missing_skills: string[];
  created_at: string;
  scraped_jds: {
    company: string;
    title: string;
    location: string;
    url: string;
    source: string;
    raw_text?: string;
    role_title?: string | null;
    seniority?: string | null;
    responsibilities?: string[];
    must_have_skills?: string[];
    nice_to_have_skills?: string[];
    tech_stack?: string[];
  };
}

export interface Checkpoint {
  id: string;
  jd_id: string;
  planned_diff: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  scraped_jds: { company: string; title: string };
}

export interface ResumeCopy {
  id: string;
  jd_id: string;
  tex_content: string;
  diff_patch: string;
  pdf_storage_path: string | null;
  status: "pending_approval" | "approved" | "compiling" | "compiled" | "failed" | "stale";
  is_applied: boolean;
  created_at: string;
  master_resume_id: string;
  scraped_jds: { company: string; title: string };
}

export interface Trace {
  id: string;
  jd_id: string;
  agent_name: string;
  log: string;
  reasoning: string;
  created_at: string;
}

export interface OutreachTarget {
  id: string;
  company_name: string;
  company_domain: string | null;
  source: "career_page" | "linkedin" | "x" | "quick_match";
  jd_id: string | null;
  role_title: string | null;
  status: "drafted" | "approved" | "skipped" | "failed";
  failure_reason: string | null;
  attempts: number;
  created_at: string;
  updated_at: string;
}

export interface OutreachDraft {
  id: string;
  target_id: string;
  subject: string;
  body: string;
  edited_subject: string | null;
  edited_body: string | null;
  resume_copy_id: string | null;
  created_at: string;
  outreach_targets: OutreachTarget;
}

export interface ApplicationRun {
  id: string;
  user_id: string;
  status: "running" | "done" | "failed";
  career_urls: string[];
  linkedin_urls: string[];
  x_urls: string[];
  jds_found: number;
  jds_done: number;
  targets_drafted: number;
  targets_failed: number;
  error: string | null;
  percent: number;
  created_at: string;
  updated_at: string;
}

export interface ScrapeSources {
  career_urls?: string[];
  linkedin_urls?: string[];
  x_urls?: string[];
}

export interface MasterResumeUploadResult {
  id: string;
  version: number;
  created_at: string;
  plain_text_chars: number;
}

export interface MasterResumeLatest {
  id: string;
  version: number;
  created_at: string;
  tex_content: string;
  plain_text_chars: number;
}

export interface QuickMatchFetchResult {
  company: string;
  title: string;
  jd_text: string;
  source: "jsonld" | "llm_extracted";
  possibly_closed: boolean;
  role_title?: string | null;
  seniority?: string | null;
  responsibilities?: string[];
  must_have_skills?: string[];
  nice_to_have_skills?: string[];
  tech_stack?: string[];
}

export interface QuickMatchStatus {
  match: JdMatch | null;
  copy: ResumeCopy | null;
  draft: OutreachDraft | null;
}

// ── API client ─────────────────────────────────────────────────────────────

export const api = {
  health: () => req<HealthResponse>("/health"),
  stats: () => req<Stats>("/jobs/stats"),
  jobActivity: () => req<JobActivity>("/jobs/activity"),

  // Positions
  positions: () => req<Position[]>("/positions"),
  createPosition: (title: string, keywords: string[]) =>
    req<Position>("/positions", {
      method: "POST",
      body: JSON.stringify({ title, fuzzy_keywords: keywords }),
    }),
  togglePosition: (id: string) =>
    req<Position>(`/positions/${id}/toggle`, { method: "PATCH" }),
  deletePosition: (id: string) =>
    req<{ deleted: string }>(`/positions/${id}`, { method: "DELETE" }),

  // Jobs / scraping
  triggerScrape: (sources?: ScrapeSources) =>
    req<{ queued: boolean; user_id: string; queued_at: string; sources: Record<string, number> }>("/jobs/scrape", {
      method: "POST",
      body: JSON.stringify(sources ?? {}),
    }),
  jds: () => req<any[]>("/jobs"),

  // Matches
  matches: () => req<JdMatch[]>("/matches"),
  match: (id: string) => req<JdMatch>(`/matches/${id}`),

  // Resume copies
  copies: () => req<ResumeCopy[]>("/copies"),
  copy: (id: string) => req<ResumeCopy>(`/copies/${id}`),
  updateTex: (id: string, tex: string) =>
    req<{ status: string; log?: string }>(`/copies/${id}/tex`, {
      method: "PATCH",
      body: JSON.stringify({ tex_content: tex }),
    }),
  markApplied: (id: string) =>
    req<ResumeCopy>(`/copies/${id}/apply`, { method: "PATCH" }),
  copyPdfUrl: (id: string) => `${BASE}/copies/${id}/pdf`,

  // Checkpoints
  checkpoints: () => req<Checkpoint[]>("/checkpoints"),
  approveCheckpoint: (id: string) =>
    req<{ status: string }>(`/checkpoints/${id}/approve`, { method: "POST" }),
  rejectCheckpoint: (id: string) =>
    req<{ status: string }>(`/checkpoints/${id}/reject`, { method: "POST" }),

  // Master resume
  latestResume: () => req<MasterResumeLatest | null>("/master-resume"),
  uploadResume: (tex: string) =>
    req<MasterResumeUploadResult>("/master-resume", {
      method: "POST",
      body: JSON.stringify({ tex_content: tex }),
    }),

  // Traces
  traces: (jdId?: string) =>
    req<Trace[]>(`/traces${jdId ? `?jd_id=${encodeURIComponent(jdId)}` : ""}`),

  // Outreach
  outreachTargets: () => req<OutreachTarget[]>("/outreach/targets"),
  deleteTarget: (id: string) =>
    req<{ deleted: string }>(`/outreach/targets/${id}`, { method: "DELETE" }),
  retryTarget: (id: string) =>
    req<{ queued: boolean }>(`/outreach/targets/${id}/retry`, { method: "POST" }),
  outreachDrafts: () => req<OutreachDraft[]>("/outreach/drafts"),
  patchDraft: (id: string, subject?: string, body?: string) =>
    req<OutreachDraft>(`/outreach/drafts/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ subject, body }),
    }),
  approveDraft: (id: string) =>
    req<{ status: string }>(`/outreach/drafts/${id}/approve`, { method: "POST" }),
  rejectDraft: (id: string) =>
    req<{ status: string }>(`/outreach/drafts/${id}/reject`, { method: "POST" }),
  prepareApplication: (sources: ScrapeSources) =>
    req<{ run_id: string }>("/outreach/prepare", {
      method: "POST",
      body: JSON.stringify(sources),
    }),
  getApplicationRun: (runId: string) => req<ApplicationRun>(`/outreach/runs/${runId}`),

  // Quick Match
  quickMatchFetchUrl: (url: string) =>
    req<QuickMatchFetchResult>("/quick-match/fetch-url", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),
  quickMatchSubmit: (jd_text: string, company: string, title: string, source_url = "") =>
    req<{ jd_id: string; queued: boolean }>("/quick-match", {
      method: "POST",
      body: JSON.stringify({ jd_text, company, title, source_url }),
    }),
  quickMatchStatus: (jdId: string) =>
    req<QuickMatchStatus>(`/quick-match/${jdId}`),
};
