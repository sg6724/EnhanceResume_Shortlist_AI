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
  status: "pending" | "approved" | "rejected" | "timed_out";
  expires_at: string;
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
};
