"use client";

import { useState } from "react";
import { api, type OutreachDraft } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge, type Tone } from "@/components/ui/Badge";
import { Textarea } from "@/components/ui/Textarea";
import { Label } from "@/components/ui/Label";

const STATUS_TONE: Record<string, Tone> = {
  drafted: "accent",
  approved: "ok",
  failed: "bad",
  skipped: "muted",
};

export function CoverLetterCard({ draft, onDone }: { draft: OutreachDraft; onDone: () => void }) {
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
        <Badge tone={STATUS_TONE[target.status] ?? "muted"}>{target.status}</Badge>
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
