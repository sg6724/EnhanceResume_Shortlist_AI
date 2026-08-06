"use client";

import { useCallback, useEffect, useState } from "react";
import { api, JobActivity, OutreachDraft, OutreachTarget } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge, type Tone } from "@/components/ui/Badge";
import { Textarea } from "@/components/ui/Textarea";
import { Label } from "@/components/ui/Label";

const STATUS_TONE: Record<string, Tone> = {
  pending: "muted",
  drafted: "accent",
  approved: "ok",
  failed: "bad",
  skipped: "muted",
};

type ScrapeRun = {
  queuedAt: string;
  sourceCount: number;
  baselineJds: number;
  baselineMatches: number;
};

function parseUrls(value: string): string[] {
  return value.split(/\n|,/).map((url) => url.trim()).filter(Boolean);
}

function parseTime(value: string | null | undefined): number {
  if (!value) return 0;
  const time = Date.parse(value);
  return Number.isFinite(time) ? time : 0;
}

function summarizeLog(value: string | null | undefined): string {
  const text = (value || "").replace(/\s+/g, " ").trim();
  if (!text) return "No details yet.";
  const lower = text.toLowerCase();
  if (lower.includes("quota") || lower.includes("rate limit") || lower.includes("429") || lower.includes("resource_exhausted")) {
    return "LLM quota/rate limit hit. Retry after provider reset or switch capacity.";
  }
  if (lower.includes("finished scrape")) return text;
  if (lower.includes("started scrape")) return text;
  if (lower.includes("returned") && lower.includes("candidate")) return text;
  if (lower.includes("raw jobs")) return text;
  if (lower.includes("score:")) return text;
  if (lower.includes("passed filter")) return "A job passed relevance filtering.";
  if (lower.includes("rejected")) return "A job was rejected by relevance filtering.";
  return text.length > 140 ? `${text.slice(0, 140)}...` : text;
}

function DraftCard({ draft, onDone }: { draft: OutreachDraft; onDone: () => void }) {
  const target = draft.outreach_targets;
  const [subject, setSubject] = useState(draft.edited_subject ?? draft.subject);
  const [body, setBody] = useState(draft.edited_body ?? draft.body);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const dirty = subject !== (draft.edited_subject ?? draft.subject) ||
    body !== (draft.edited_body ?? draft.body);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setErr(null);
    try {
      await fn();
      onDone();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardHeader className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <CardTitle>{target.company_name}</CardTitle>
          <CardDescription>
            {target.role_title || "Open role"}
            {draft.resume_copy_id ? " - tailored resume ready" : " - cover letter draft"}
          </CardDescription>
        </div>
        <Badge tone={STATUS_TONE[target.status] ?? "muted"}>{target.status.replace(/_/g, " ")}</Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor={`subject-${draft.id}`}>Title</Label>
          <Textarea id={`subject-${draft.id}`} value={subject} onChange={(e) => setSubject(e.target.value)} rows={2} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor={`body-${draft.id}`}>Cover letter</Label>
          <Textarea
            id={`body-${draft.id}`}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={12}
            className="font-mono"
          />
        </div>
        {err && <div className="text-bad text-xs">{err}</div>}
        <div className="flex gap-2 flex-wrap">
          {dirty && (
            <Button variant="secondary" disabled={busy} onClick={() => act(() => api.patchDraft(draft.id, subject, body))}>
              Save edits
            </Button>
          )}
          <Button variant="ok" disabled={busy || dirty} onClick={() => act(() => api.approveDraft(draft.id))}>
            Mark ready
          </Button>
          <Button variant="danger" disabled={busy} onClick={() => act(() => api.rejectDraft(draft.id))}>
            Skip
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ActivityPanel({ activity, run }: { activity: JobActivity | null; run: ScrapeRun | null }) {
  const traces = activity?.traces ?? [];
  const recentJobs = activity?.recent_jds ?? [];
  const runStart = run ? parseTime(run.queuedAt) - 5000 : 0;
  const scopedTraces = run ? traces.filter((trace) => parseTime(trace.created_at) >= runStart) : traces;
  const scopedJobs = run ? recentJobs.filter((job) => parseTime(job.scraped_at) >= runStart) : recentJobs;
  const importantTraces = scopedTraces
    .map((trace) => ({ ...trace, shortLog: summarizeLog(trace.log) }))
    .filter((trace) => !trace.shortLog.startsWith("LLM quota") && !trace.shortLog.includes("Passed filter"))
    .slice(0, 4);

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold text-text">Run activity</h2>
      <Card>
        <CardContent className="space-y-4 pt-4">
          <div className="grid gap-3 sm:grid-cols-4">
            <div>
              <div className="text-2xl font-semibold text-text">{activity?.stats.total_jds ?? 0}</div>
              <div className="text-xs text-muted">jobs scraped</div>
            </div>
            <div>
              <div className="text-2xl font-semibold text-text">{activity?.stats.total_matches ?? 0}</div>
              <div className="text-xs text-muted">matches scored</div>
            </div>
            <div>
              <div className="text-2xl font-semibold text-text">{activity?.targets.length ?? 0}</div>
              <div className="text-xs text-muted">recent targets</div>
            </div>
            <div>
              <div className="text-2xl font-semibold text-text">{activity?.drafts.length ?? 0}</div>
              <div className="text-xs text-muted">recent letters</div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <div className="text-xs font-semibold uppercase tracking-wide text-muted">Latest worker events</div>
              {importantTraces.map((trace) => (
                <div key={trace.id} className="text-xs text-muted">
                  <span className="text-text">{trace.agent_name}</span>: {trace.shortLog}
                </div>
              ))}
              {activity && traces.length === 0 && <div className="text-sm text-muted">No worker activity recorded yet.</div>}
              {!activity && <div className="text-sm text-muted">Loading activity...</div>}
            </div>
            <div className="space-y-2">
              <div className="text-xs font-semibold uppercase tracking-wide text-muted">Latest scraped jobs</div>
              {scopedJobs.slice(0, 5).map((job) => (
                <div key={job.id} className="text-xs text-muted">
                  <span className="text-text">{job.title}</span> at {job.company || "Unknown"} ({job.source})
                </div>
              ))}
              {activity && scopedJobs.length === 0 && (
                <div className="text-sm text-muted">
                  {run ? "No jobs from this run have been saved yet." : "No jobs scraped yet."}
                </div>
              )}
              {!activity && <div className="text-sm text-muted">Loading jobs...</div>}
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

function RunStatusCard({ run, activity }: { run: ScrapeRun | null; activity: JobActivity | null }) {
  if (!run) {
    return (
      <Card>
        <CardContent className="py-4">
          <div className="text-sm font-medium text-text">No scrape queued in this browser session.</div>
          <div className="text-xs text-muted mt-1">Queue a source below. This panel will track worker progress automatically.</div>
        </CardContent>
      </Card>
    );
  }

  const queuedAt = parseTime(run.queuedAt);
  const traces = (activity?.traces ?? []).filter((trace) => parseTime(trace.created_at) >= queuedAt - 5000);
  const latestTrace = traces[0];
  const finishedTrace = traces.find((trace) => (trace.log ?? "").toLowerCase().includes("finished scrape"));
  const currentJds = activity?.stats.total_jds ?? run.baselineJds;
  const currentMatches = activity?.stats.total_matches ?? run.baselineMatches;
  const newJds = Math.max(0, currentJds - run.baselineJds);
  const newMatches = Math.max(0, currentMatches - run.baselineMatches);
  const hasWorkerEvent = traces.length > 0 || newJds > 0 || newMatches > 0;
  const elapsedMs = Date.now() - queuedAt;
  const staleQueued = !hasWorkerEvent && elapsedMs > 90_000;
  const staleRunning = hasWorkerEvent && !finishedTrace && elapsedMs > 15 * 60_000;
  const state = finishedTrace ? "Done" : staleQueued || staleRunning ? "Needs attention" : hasWorkerEvent ? "Running" : "Queued";
  const tone: Tone = state === "Done" ? "ok" : state === "Running" ? "accent" : state === "Needs attention" ? "bad" : "muted";
  const detail = state === "Needs attention"
    ? "The worker has not reported completion. Check the latest worker events or retry the scrape."
    : latestTrace
      ? `${latestTrace.agent_name}: ${summarizeLog(latestTrace.log)}`
      : "Waiting for the worker to pick up the job.";

  return (
    <Card>
      <CardContent className="py-4 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2">
            <Badge tone={tone}>{state}</Badge>
            <span className="text-sm font-medium text-text">Latest scrape</span>
          </div>
          <div className="text-xs text-muted mt-2">
            {run.sourceCount} source(s) queued. {newJds} new jobs scraped, {newMatches} new matches scored since this run started.
          </div>
          <div className="text-xs text-muted mt-1">{detail}</div>
        </div>
        <div className="text-xs text-muted">
          Started {new Date(run.queuedAt).toLocaleTimeString()}
        </div>
      </CardContent>
    </Card>
  );
}

export default function OutreachPage() {
  const [targets, setTargets] = useState<OutreachTarget[]>([]);
  const [drafts, setDrafts] = useState<OutreachDraft[]>([]);
  const [activity, setActivity] = useState<JobActivity | null>(null);
  const [careerUrls, setCareerUrls] = useState("");
  const [linkedinUrls, setLinkedinUrls] = useState("");
  const [xUrls, setXUrls] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [run, setRun] = useState<ScrapeRun | null>(null);

  const reload = useCallback(() => {
    api.outreachTargets().then(setTargets).catch(() => {});
    api.outreachDrafts().then(setDrafts).catch(() => {});
    api.jobActivity().then(setActivity).catch(() => {});
  }, []);

  useEffect(() => {
    const saved = window.localStorage.getItem("application-prep-last-run");
    if (saved) {
      try {
        setRun(JSON.parse(saved) as ScrapeRun);
      } catch {
        window.localStorage.removeItem("application-prep-last-run");
      }
    }
    reload();
    const timer = window.setInterval(reload, 5000);
    return () => window.clearInterval(timer);
  }, [reload]);

  const runScrape = async () => {
    try {
      const res = await api.triggerScrape({
        career_urls: parseUrls(careerUrls),
        linkedin_urls: parseUrls(linkedinUrls),
        x_urls: parseUrls(xUrls),
      });
      const total = res.sources.career_urls + res.sources.linkedin_urls + res.sources.x_urls;
      const nextRun = {
        queuedAt: res.queued_at,
        sourceCount: total,
        baselineJds: activity?.stats.total_jds ?? 0,
        baselineMatches: activity?.stats.total_matches ?? 0,
      };
      setRun(nextRun);
      window.localStorage.setItem("application-prep-last-run", JSON.stringify(nextRun));
      setMsg(null);
      window.setTimeout(reload, 1500);
    } catch (e) {
      setMsg(String(e));
    }
  };

  const prepareLetters = async () => {
    try {
      await api.runOutreach();
      setMsg("Application prep queued. Activity refreshes automatically while the worker runs.");
      window.setTimeout(reload, 1500);
    } catch (e) {
      setMsg(String(e));
    }
  };

  return (
    <div className="space-y-8 max-w-5xl">
      <PageHeader
        title="Application"
        titleEmphasis="Prep"
        description="Scrape job sources, score fit, and prepare tailored cover letters."
        action={<Button variant="secondary" onClick={prepareLetters}>Prepare letters</Button>}
      />

      {msg && <div className="text-xs text-accent">{msg}</div>}

      <RunStatusCard run={run} activity={activity} />

      <ActivityPanel activity={activity} run={run} />

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-text">Scrape sources</h2>
        <Card>
          <CardContent className="grid gap-3 pt-4 md:grid-cols-3">
            <div className="space-y-1.5">
              <Label htmlFor="career-urls">Career pages</Label>
              <Textarea id="career-urls" value={careerUrls} onChange={(e) => setCareerUrls(e.target.value)} rows={6} placeholder="https://company.com/careers" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="linkedin-urls">LinkedIn URLs</Label>
              <Textarea id="linkedin-urls" value={linkedinUrls} onChange={(e) => setLinkedinUrls(e.target.value)} rows={6} placeholder="https://www.linkedin.com/company/..." />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="x-urls">X URLs</Label>
              <Textarea id="x-urls" value={xUrls} onChange={(e) => setXUrls(e.target.value)} rows={6} placeholder="https://x.com/company" />
            </div>
            <div className="md:col-span-3">
              <Button variant="secondary" onClick={runScrape}>Queue scrape and match</Button>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-text">Application targets</h2>
        <Card className="divide-y divide-border">
          {targets.length === 0 && <div className="p-4 text-muted text-sm">No targets yet.</div>}
          {targets.map((target) => (
            <div key={target.id} className="p-3 flex items-center justify-between gap-2 flex-wrap">
              <div>
                <span className="text-text text-sm font-medium">{target.company_name}</span>
                <span className="text-muted text-xs ml-2">{target.role_title || "Open role"} - {target.source}</span>
                {target.failure_reason && <div className="text-bad text-[11px] max-w-3xl">{summarizeLog(target.failure_reason)}</div>}
              </div>
              <div className="flex items-center gap-2">
                <Badge tone={STATUS_TONE[target.status] ?? "muted"}>{target.status.replace(/_/g, " ")}</Badge>
                {target.status === "failed" && (
                  <button onClick={() => api.patchTarget(target.id, { retry: true }).then(reload)} className="text-[11px] text-accent hover:underline">retry</button>
                )}
                <button onClick={() => api.deleteTarget(target.id).then(reload)} className="text-[11px] text-bad hover:underline">remove</button>
              </div>
            </div>
          ))}
        </Card>
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-text">Cover letters</h2>
        {drafts.length === 0 && <div className="text-muted text-sm">No cover letters waiting for review.</div>}
        {drafts.map((draft) => <DraftCard key={draft.id} draft={draft} onDone={reload} />)}
      </section>
    </div>
  );
}
