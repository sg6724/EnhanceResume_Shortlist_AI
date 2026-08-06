"use client";
import { useEffect, useState } from "react";
import { api, type Checkpoint } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { SketchArrow } from "@/components/ui/Doodles";

export default function CheckpointsPage() {
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState<string | null>(null);

  const load = () =>
    api.checkpoints()
      .then(setCheckpoints)
      .finally(() => setLoading(false));

  useEffect(() => {
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, []);

  const act = async (id: string, action: "approve" | "reject") => {
    setActing(id + action);
    try {
      if (action === "approve") await api.approveCheckpoint(id);
      else await api.rejectCheckpoint(id);
      await load();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setActing(null);
    }
  };

  const pending = checkpoints.filter((c) => c.status === "pending");
  const history = checkpoints.filter((c) => c.status !== "pending");

  return (
    <div className="max-w-3xl space-y-8">
      <PageHeader
        title="Checkpoints"
        description="Review planned diffs before the Rewriter Agent acts. Approve to queue the rewrite; reject to skip."
      />

      {loading && (
        <div className="text-center py-16 text-muted text-sm animate-pulse">Loading…</div>
      )}

      {/* Pending */}
      {pending.length > 0 && (
        <div className="space-y-4">
          <div className="text-sm font-semibold text-warn flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-warn animate-pulse" />
            Awaiting Approval ({pending.length})
          </div>
          {pending.map((cp) => {
            return (
              <div key={cp.id} className="bg-panel border border-warn/40 rounded-xl p-5 space-y-4">
                <div>
                  <div className="font-semibold text-text">
                    {cp.scraped_jds?.title ?? "Unknown"}
                  </div>
                  <div className="text-muted text-sm">
                    {cp.scraped_jds?.company ?? "Unknown"}
                  </div>
                </div>

                <pre className="bg-bg border border-border rounded-lg p-3 text-xs text-muted whitespace-pre-wrap max-h-48 overflow-y-auto font-mono">
                  {cp.planned_diff}
                </pre>

                <div className="flex gap-2">
                  <Button variant="ok" pill onClick={() => act(cp.id, "approve")} disabled={!!acting}>
                    {acting === cp.id + "approve" ? "…" : "Approve & Rewrite"}
                  </Button>
                  <Button variant="danger" pill onClick={() => act(cp.id, "reject")} disabled={!!acting}>
                    {acting === cp.id + "reject" ? "…" : "Skip"}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <div className="space-y-2">
          <div className="text-sm font-semibold text-muted">History</div>
          {history.map((cp) => (
            <Card key={cp.id} className="px-5 py-3 flex items-center justify-between">
              <div>
                <span className="text-sm font-medium text-text">
                  {cp.scraped_jds?.title ?? "Unknown"}
                </span>
                <span className="text-muted text-sm"> · {cp.scraped_jds?.company ?? "Unknown"}</span>
              </div>
              <Badge tone={cp.status === "approved" ? "ok" : cp.status === "rejected" ? "bad" : "muted"}>
                {cp.status}
              </Badge>
            </Card>
          ))}
        </div>
      )}

      {!loading && checkpoints.length === 0 && (
        <div className="text-center py-16 text-muted text-sm flex flex-col items-center gap-2">
          <SketchArrow className="w-16 h-8 text-muted/50 -scale-y-100" />
          No checkpoints yet. Run a scraping batch to generate some.
        </div>
      )}
    </div>
  );
}
