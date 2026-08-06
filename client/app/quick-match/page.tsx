"use client";
import { useEffect, useRef, useState } from "react";
import { api, type QuickMatchStatus, type QuickMatchFetchResult } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Label } from "@/components/ui/Label";

type Stage = "idle" | "fetching" | "reviewing" | "running" | "done";

export default function QuickMatchPage() {
  const [stage, setStage] = useState<Stage>("idle");
  const [url, setUrl] = useState("");
  const [jdText, setJdText] = useState("");
  const [company, setCompany] = useState("");
  const [title, setTitle] = useState("");
  const [possiblyClosed, setPossiblyClosed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<QuickMatchStatus | null>(null);
  const [extracted, setExtracted] = useState<QuickMatchFetchResult | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const doFetch = async () => {
    if (!url.trim()) return;
    setError(null);
    setStage("fetching");
    try {
      const res = await api.quickMatchFetchUrl(url.trim());
      setJdText(res.jd_text);
      setCompany(res.company);
      setTitle(res.title);
      setPossiblyClosed(res.possibly_closed);
      setExtracted(res);
      setStage("reviewing");
    } catch (e: any) {
      setError(e.message);
      setStage("idle");
    }
  };

  const startReviewFromPaste = () => {
    setError(null);
    setPossiblyClosed(false);
    setStage("reviewing");
  };

  const runMatch = async () => {
    if (!jdText.trim() || !company.trim() || !title.trim()) {
      setError("Company, title, and JD text are all required.");
      return;
    }
    setError(null);
    setStage("running");
    try {
      const res = await api.quickMatchSubmit(jdText.trim(), company.trim(), title.trim());
      pollRef.current = setInterval(async () => {
        const s = await api.quickMatchStatus(res.jd_id);
        setStatus(s);
        if (s.copy && (s.copy.status === "compiled" || s.copy.status === "failed")) {
          if (pollRef.current) clearInterval(pollRef.current);
          setStage("done");
        }
      }, 3000);
    } catch (e: any) {
      setError(e.message);
      setStage("reviewing");
    }
  };

  const reset = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    setStage("idle");
    setUrl("");
    setJdText("");
    setCompany("");
    setTitle("");
    setError(null);
    setStatus(null);
  };

  return (
    <div className="space-y-8 max-w-4xl">
      <PageHeader
        title="Quick"
        titleEmphasis="Match"
        description="Score your resume against one specific job — via its posting URL or pasted JD text — and get a tailored, compiled resume immediately."
      />

      {error && (
        <div className="bg-bad/10 border border-bad/30 rounded-xl p-4 text-sm text-bad">
          {error}
        </div>
      )}

      {(stage === "idle" || stage === "fetching") && (
        <Card>
          <CardHeader>
            <CardTitle>Start from a URL or paste the JD</CardTitle>
            <CardDescription>Either works — you&apos;ll review and can edit before running the match.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-1.5">
              <Label htmlFor="job-url">Job posting URL</Label>
              <div className="flex gap-2">
                <Input
                  id="job-url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://company.com/careers/job/123"
                />
                <Button onClick={doFetch} disabled={stage === "fetching" || !url.trim()}>
                  {stage === "fetching" ? "Fetching…" : "Fetch"}
                </Button>
              </div>
            </div>
            <div className="flex items-center gap-3 text-xs text-muted">
              <div className="h-px flex-1 bg-border" /> or <div className="h-px flex-1 bg-border" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="paste-jd">Paste JD text directly</Label>
              <Textarea
                id="paste-jd"
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                rows={8}
                placeholder="Paste the full job description here…"
              />
              <div className="flex justify-end">
                <Button variant="secondary" onClick={startReviewFromPaste} disabled={!jdText.trim()}>
                  Continue
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {stage === "reviewing" && (
        <Card>
          <CardHeader>
            <CardTitle>Review before running</CardTitle>
            <CardDescription>Correct anything that looks wrong, then run the match.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {possiblyClosed && (
              <div className="bg-warn/10 border border-warn/30 rounded-xl p-3 text-xs text-warn">
                This posting may have closed — the extracted text mentions the role being filled or expired.
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="qm-company">Company</Label>
                <Input id="qm-company" value={company} onChange={(e) => setCompany(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="qm-title">Job title</Label>
                <Input id="qm-title" value={title} onChange={(e) => setTitle(e.target.value)} />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="qm-jdtext">Job description</Label>
              <Textarea id="qm-jdtext" value={jdText} onChange={(e) => setJdText(e.target.value)} rows={14} />
            </div>
            {extracted && (extracted.must_have_skills?.length || extracted.tech_stack?.length || extracted.responsibilities?.length) ? (
              <div className="space-y-2 rounded-xl border border-border p-3">
                <div className="text-xs font-medium text-muted">Extracted from posting</div>
                {extracted.must_have_skills?.length ? (
                  <div>
                    <div className="text-xs text-muted">Must-have skills</div>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {extracted.must_have_skills.map((s) => <Badge key={s} tone="accent">{s}</Badge>)}
                    </div>
                  </div>
                ) : null}
                {extracted.tech_stack?.length ? (
                  <div>
                    <div className="text-xs text-muted">Tech stack</div>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {extracted.tech_stack.map((s) => <Badge key={s} tone="accent">{s}</Badge>)}
                    </div>
                  </div>
                ) : null}
                {extracted.responsibilities?.length ? (
                  <div>
                    <div className="text-xs text-muted">Responsibilities</div>
                    <ul className="list-disc list-inside text-xs text-text mt-1 space-y-0.5">
                      {extracted.responsibilities.slice(0, 6).map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                  </div>
                ) : null}
                {extracted.seniority ? (
                  <div className="text-xs text-muted">Seniority: {extracted.seniority}</div>
                ) : null}
              </div>
            ) : null}
            <div className="flex justify-between">
              <Button variant="ghost" onClick={reset}>Start over</Button>
              <Button onClick={runMatch}>Run Match</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {(stage === "running" || stage === "done") && (
        <Card>
          <CardHeader>
            <CardTitle>{company} — {title}</CardTitle>
            {stage === "running" && <CardDescription>Scoring, then rewriting and compiling your resume…</CardDescription>}
          </CardHeader>
          <CardContent className="space-y-5">
            {stage === "running" && !status?.match && (
              <div className="flex items-center gap-2 text-sm text-muted">
                <span className="w-3 h-3 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
                Working…
              </div>
            )}

            {status?.match && (
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <Badge tone="accent">{Math.round(status.match.composite_score * 100)}% match</Badge>
                  <span className="text-xs text-muted">
                    keyword {Math.round(status.match.keyword_score * 100)}% · semantic {Math.round(status.match.semantic_score * 100)}% · LLM {Math.round(status.match.llm_score * 100)}%
                  </span>
                </div>
                <div className="text-sm text-text whitespace-pre-wrap">{status.match.gap_analysis}</div>
                {status.match.matched_skills?.length ? (
                  <div>
                    <div className="text-xs text-muted">Matched skills</div>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {status.match.matched_skills.map((s) => <Badge key={s} tone="ok">{s}</Badge>)}
                    </div>
                  </div>
                ) : null}
                {status.match.missing_skills?.length ? (
                  <div>
                    <div className="text-xs text-muted">Missing skills</div>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {status.match.missing_skills.map((s) => <Badge key={s} tone="bad">{s}</Badge>)}
                    </div>
                  </div>
                ) : null}
              </div>
            )}

            {status?.copy && stage === "done" && (
              <div className="space-y-3">
                <Badge tone={status.copy.status === "compiled" ? "ok" : "bad"}>{status.copy.status}</Badge>
                {status.copy.status === "compiled" && status.copy.pdf_storage_path && (
                  <div className="space-y-3">
                    <div className="border border-border rounded-xl overflow-hidden h-[32rem] bg-bg">
                      <embed src={api.copyPdfUrl(status.copy.id)} type="application/pdf" className="w-full h-full" />
                    </div>
                    <a href={api.copyPdfUrl(status.copy.id)} download={`resume-${company}.pdf`}>
                      <Button>Download PDF</Button>
                    </a>
                  </div>
                )}
                {status.copy.status === "failed" && (
                  <div className="text-sm text-bad">
                    Compile failed after retries. Check the Observability page for the error log.
                  </div>
                )}
              </div>
            )}

            {stage === "done" && (
              <div className="pt-2">
                <Button variant="secondary" onClick={reset}>Start another</Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
