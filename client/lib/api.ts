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
  created_at: string;
  scraped_jds: {
    company: string;
    title: string;
    location: string;
    url: string;
    source: string;
    raw_text?: string;
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
  source: "pipeline" | "watchlist";
  jd_id: string | null;
  role_title: string | null;
  status:
    | "pending" | "contact_found" | "contact_not_found"
    | "drafted" | "approved" | "sent" | "failed" | "skipped";
  founder_name: string | null;
  founder_title: string | null;
  founder_email: string | null;
  email_confidence: "verified" | "guessed" | null;
  contact_method: string | null;
  failure_reason: string | null;
  created_at: string;
}

export interface OutreachDraft {
  id: string;
  target_id: string;
  subject: string;
  body: string;
  edited_subject: string | null;
  edited_body: string | null;
  resume_copy_id: string | null;
  sent_at: string | null;
  send_error: string | null;
  created_at: string;
  outreach_targets: OutreachTarget;
}

export interface OutreachQuota {
  hunter_remaining: number;
  hunter_limit: number;
}

export interface MasterResumeUploadResult {
  id: string;
  version: number;
  created_at: string;
  plain_text_chars: number;
}

// ── API client ─────────────────────────────────────────────────────────────

export const api = {
  health: () => req<HealthResponse>("/health"),
  stats: () => req<Stats>("/jobs/stats"),

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
  triggerScrape: () =>
    req<{ queued: boolean; user_id: string }>("/jobs/scrape", { method: "POST" }),
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
  addWatchlist: (company_name: string, company_domain?: string) =>
    req<OutreachTarget>("/outreach/watchlist", {
      method: "POST",
      body: JSON.stringify({ company_name, company_domain: company_domain || null }),
    }),
  patchTarget: (id: string, patch: Partial<Pick<OutreachTarget,
    "founder_name" | "founder_title" | "founder_email">> & { retry?: boolean }) =>
    req<OutreachTarget>(`/outreach/targets/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  deleteTarget: (id: string) =>
    req<{ deleted: string }>(`/outreach/targets/${id}`, { method: "DELETE" }),
  outreachDrafts: () => req<OutreachDraft[]>("/outreach/drafts"),
  patchDraft: (id: string, subject?: string, body?: string) =>
    req<OutreachDraft>(`/outreach/drafts/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ subject, body }),
    }),
  approveDraft: (id: string) =>
    req<{ queued: boolean }>(`/outreach/drafts/${id}/approve`, { method: "POST" }),
  rejectDraft: (id: string) =>
    req<{ status: string }>(`/outreach/drafts/${id}/reject`, { method: "POST" }),
  runOutreach: () => req<{ queued: boolean }>("/outreach/run", { method: "POST" }),
  outreachQuota: () => req<OutreachQuota>("/outreach/quota"),
};
