"use client";
import { useCallback, useEffect, useState } from "react";
import { api, OutreachDraft, OutreachTarget, OutreachQuota } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge, type Tone } from "@/components/ui/Badge";

const STATUS_TONE: Record<string, Tone> = {
  pending: "muted",
  contact_found: "accent",
  contact_not_found: "bad",
  drafted: "accent",
  approved: "ok",
  sent: "ok",
  failed: "bad",
  skipped: "muted",
};

function DraftCard({ draft, onDone }: { draft: OutreachDraft; onDone: () => void }) {
  const t = draft.outreach_targets;
  const [subject, setSubject] = useState(draft.edited_subject ?? draft.subject);
  const [body, setBody] = useState(draft.edited_body ?? draft.body);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const dirty = subject !== (draft.edited_subject ?? draft.subject) ||
    body !== (draft.edited_body ?? draft.body);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true); setErr(null);
    try { await fn(); onDone(); } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  };

  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <div className="text-text font-semibold text-sm">{t.company_name}</div>
          <div className="text-muted text-xs">
            {t.founder_name} — {t.founder_title} ·{" "}
            <span className="text-text">{t.founder_email}</span>{" "}
            {t.email_confidence === "verified"
              ? <span className="text-ok">verified</span>
              : <span className="text-bad" title="Pattern-guessed email — delivery not guaranteed">guessed</span>}
          </div>
          {t.role_title && <div className="text-muted text-xs">Role: {t.role_title}</div>}
        </div>
        <div className="text-[11px] text-muted">
          {draft.resume_copy_id ? "Tailored resume PDF attached" : "Master resume PDF attached"}
        </div>
      </div>
      <input
        value={subject}
        onChange={(e) => setSubject(e.target.value)}
        className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text"
        placeholder="Subject"
      />
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={8}
        className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text font-mono"
      />
      {draft.send_error && <div className="text-bad text-xs">Last send failed: {draft.send_error}</div>}
      {err && <div className="text-bad text-xs">{err}</div>}
      <div className="flex gap-2">
        {dirty && (
          <Button variant="secondary" disabled={busy}
            onClick={() => act(() => api.patchDraft(draft.id, subject, body))}>
            Save edits
          </Button>
        )}
        <Button variant="ok" disabled={busy || dirty}
          title={dirty ? "Save edits first" : undefined}
          onClick={() => act(() => api.approveDraft(draft.id))}>
          {draft.send_error ? "Retry send" : "Approve & Send"}
        </Button>
        <Button variant="danger" disabled={busy}
          onClick={() => act(() => api.rejectDraft(draft.id))}>
          Reject
        </Button>
      </div>
    </Card>
  );
}

export default function OutreachPage() {
  const [targets, setTargets] = useState<OutreachTarget[]>([]);
  const [drafts, setDrafts] = useState<OutreachDraft[]>([]);
  const [quota, setQuota] = useState<OutreachQuota | null>(null);
  const [company, setCompany] = useState("");
  const [domain, setDomain] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const reload = useCallback(() => {
    api.outreachTargets().then(setTargets).catch(() => {});
    api.outreachDrafts().then(setDrafts).catch(() => {});
    api.outreachQuota().then(setQuota).catch(() => {});
  }, []);
  useEffect(reload, [reload]);

  const add = async () => {
    if (!company.trim()) return;
    try {
      await api.addWatchlist(company.trim(), domain.trim() || undefined);
      setCompany(""); setDomain(""); reload();
    } catch (e) { setMsg(String(e)); }
  };

  const runNow = async () => {
    try { await api.runOutreach(); setMsg("Outreach cycle queued — refresh in a minute."); }
    catch (e) { setMsg(String(e)); }
  };

  return (
    <div className="space-y-8 max-w-5xl">
      <PageHeader
        title="Outreach"
        description="Founder discovery + direct cover letters, approved by you."
        action={
          <div className="flex items-center gap-3">
            {quota && (
              <span className="text-[11px] text-muted">
                Hunter quota: {quota.hunter_remaining}/{quota.hunter_limit} this month
              </span>
            )}
            <Button variant="secondary" onClick={runNow}>Run now</Button>
          </div>
        }
      />

      {msg && <div className="text-xs text-accent">{msg}</div>}

      {/* Watchlist */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-text">Company watchlist</h2>
        <div className="flex gap-2 flex-wrap">
          <input value={company} onChange={(e) => setCompany(e.target.value)}
            placeholder="Company name"
            className="bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text" />
          <input value={domain} onChange={(e) => setDomain(e.target.value)}
            placeholder="Domain (optional)"
            className="bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text" />
          <Button variant="secondary" onClick={add}>Add company</Button>
        </div>
        <Card className="divide-y divide-border">
          {targets.length === 0 && (
            <div className="p-4 text-muted text-sm">No targets yet — add a company or run the pipeline.</div>
          )}
          {targets.map((t) => (
            <div key={t.id} className="p-3 flex items-center justify-between gap-2 flex-wrap">
              <div>
                <span className="text-text text-sm font-medium">{t.company_name}</span>
                <span className="text-muted text-xs ml-2">
                  {t.source} {t.founder_email ? `· ${t.founder_email}` : ""}
                </span>
                {t.failure_reason && <div className="text-bad text-[11px]">{t.failure_reason}</div>}
              </div>
              <div className="flex items-center gap-2">
                <Badge tone={STATUS_TONE[t.status] ?? "muted"}>{t.status.replace(/_/g, " ")}</Badge>
                {t.status === "contact_not_found" && (
                  <button onClick={() => api.patchTarget(t.id, { retry: true }).then(reload)}
                    className="text-[11px] text-accent hover:underline">retry</button>
                )}
                <button onClick={() => api.deleteTarget(t.id).then(reload)}
                  className="text-[11px] text-bad hover:underline">remove</button>
              </div>
            </div>
          ))}
        </Card>
      </section>

      {/* Drafts */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-text">Drafts awaiting your approval</h2>
        {drafts.length === 0 && (
          <div className="text-muted text-sm">Nothing to review — drafts appear here after each cycle.</div>
        )}
        {drafts.map((d) => <DraftCard key={d.id} draft={d} onDone={reload} />)}
      </section>
    </div>
  );
}
