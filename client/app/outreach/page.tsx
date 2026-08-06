"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type ApplicationRun, type OutreachDraft, type OutreachTarget } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge, type Tone } from "@/components/ui/Badge";
import { Textarea } from "@/components/ui/Textarea";
import { Label } from "@/components/ui/Label";
import { CoverLetterCard } from "@/components/CoverLetterCard";

const TARGET_STATUS_TONE: Record<string, Tone> = {
  drafted: "accent",
  approved: "ok",
  failed: "bad",
  skipped: "muted",
};

const RUN_ID_KEY = "application-prep-run-id";

function parseUrls(value: string): string[] {
  return value.split(/\n|,/).map((url) => url.trim()).filter(Boolean);
}

function runLabel(run: ApplicationRun): string {
  if (run.status === "failed") return run.error ? `Failed: ${run.error}` : "Failed";
  if (run.status === "done") {
    return `Done — ${run.targets_drafted} ready${run.targets_failed ? `, ${run.targets_failed} failed` : ""}`;
  }
  if (run.jds_found === 0) return "Scraping sources...";
  return `Tailoring and drafting ${run.jds_done} of ${run.jds_found}...`;
}

function ProgressCard({ run }: { run: ApplicationRun | null }) {
  if (!run) {
    return (
      <Card>
        <CardContent className="py-4">
          <div className="text-sm text-muted">Paste at least one URL below and click Prepare application.</div>
        </CardContent>
      </Card>
    );
  }
  const tone: Tone = run.status === "done" ? "ok" : run.status === "failed" ? "bad" : "accent";
  return (
    <Card>
      <CardContent className="py-4 space-y-2">
        <div className="flex items-center gap-2">
          <Badge tone={tone}>{run.status}</Badge>
          <span className="text-sm font-medium text-text">{runLabel(run)}</span>
        </div>
        <div className="h-2 rounded-full bg-border overflow-hidden">
          <div className="h-full bg-accent transition-all duration-500" style={{ width: `${run.percent}%` }} />
        </div>
      </CardContent>
    </Card>
  );
}

export default function OutreachPage() {
  const [targets, setTargets] = useState<OutreachTarget[]>([]);
  const [drafts, setDrafts] = useState<OutreachDraft[]>([]);
  const [careerUrls, setCareerUrls] = useState("");
  const [linkedinUrls, setLinkedinUrls] = useState("");
  const [xUrls, setXUrls] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [run, setRun] = useState<ApplicationRun | null>(null);

  const reload = useCallback(() => {
    api.outreachTargets().then(setTargets).catch(() => {});
    api.outreachDrafts().then(setDrafts).catch(() => {});
  }, []);

  useEffect(() => {
    reload();
    const savedId = window.localStorage.getItem(RUN_ID_KEY);
    if (savedId) {
      api.getApplicationRun(savedId).then(setRun).catch(() => {
        window.localStorage.removeItem(RUN_ID_KEY);
      });
    }
  }, [reload]);

  useEffect(() => {
    if (!run || run.status !== "running") return;
    const timer = window.setInterval(async () => {
      try {
        const r = await api.getApplicationRun(run.id);
        setRun(r);
        reload();
        if (r.status !== "running") window.clearInterval(timer);
      } catch {
        window.clearInterval(timer);
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [run?.id, run?.status, reload]);

  const prepareApplication = async () => {
    setMsg(null);
    try {
      const { run_id } = await api.prepareApplication({
        career_urls: parseUrls(careerUrls),
        linkedin_urls: parseUrls(linkedinUrls),
        x_urls: parseUrls(xUrls),
      });
      window.localStorage.setItem(RUN_ID_KEY, run_id);
      const r = await api.getApplicationRun(run_id);
      setRun(r);
    } catch (e) {
      setMsg(String(e));
    }
  };

  const retry = async (id: string) => {
    try {
      await api.retryTarget(id);
      setMsg("Retry queued.");
      window.setTimeout(reload, 2000);
    } catch (e) {
      setMsg(String(e));
    }
  };

  return (
    <div className="space-y-8 max-w-5xl">
      <PageHeader
        title="Application"
        titleEmphasis="Prep"
        description="Paste job sources; get a scored, tailored resume and cover letter for each."
      />

      {msg && <div className="text-xs text-accent">{msg}</div>}

      <ProgressCard run={run} />

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-text">Sources</h2>
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
              <Button variant="secondary" onClick={prepareApplication} disabled={run?.status === "running"}>
                {run?.status === "running" ? "Preparing..." : "Prepare application"}
              </Button>
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
                <span className="text-muted text-xs ml-2">{target.role_title || "Open role"}</span>
                {target.failure_reason && <div className="text-bad text-[11px] max-w-3xl">{target.failure_reason}</div>}
              </div>
              <div className="flex items-center gap-2">
                <Badge tone={TARGET_STATUS_TONE[target.status] ?? "muted"}>{target.status}</Badge>
                {target.status === "failed" && (
                  <button onClick={() => retry(target.id)} className="text-[11px] text-accent hover:underline">retry</button>
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
        {drafts.map((draft) => <CoverLetterCard key={draft.id} draft={draft} onDone={reload} />)}
      </section>
    </div>
  );
}
