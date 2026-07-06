"use client";
import { useEffect, useState } from "react";
import { api, type Checkpoint } from "@/lib/api";
import clsx from "clsx";

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
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Checkpoints</h1>
        <p className="text-muted text-sm mt-1">
          Review planned diffs before the Rewriter Agent acts. Approve to queue
          the rewrite; reject to skip.
        </p>
      </div>

      {loading && (
        <div className="text-center py-16 text-muted text-sm animate-pulse">
          Loading…
        </div>
      )}

      {/* Pending */}
      {pending.length > 0 && (
        <div className="space-y-4">
          <div className="text-sm font-semibold text-warn flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-warn animate-pulse" />
            Awaiting Approval ({pending.length})
          </div>
          {pending.map((cp) => {
            const expiresAt = new Date(cp.expires_at);
            const minutesLeft = Math.max(
              0,
              Math.round((expiresAt.getTime() - Date.now()) / 60000)
            );
            return (
              <div
                key={cp.id}
                className="bg-panel border border-warn/40 rounded-xl p-5 space-y-4"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-semibold text-text">
                      {cp.scraped_jds?.title ?? "Unknown"}
                    </div>
                    <div className="text-muted text-sm">
                      {cp.scraped_jds?.company ?? "Unknown"}
                    </div>
                  </div>
                  <div className="text-xs text-warn text-right flex-shrink-0">
                    Auto-approves in {minutesLeft}m
                  </div>
                </div>

                <pre className="bg-bg border border-border rounded-lg p-3 text-xs text-muted whitespace-pre-wrap max-h-48 overflow-y-auto font-mono">
                  {cp.planned_diff}
                </pre>

                <div className="flex gap-2">
                  <button
                    onClick={() => act(cp.id, "approve")}
                    disabled={!!acting}
                    className="bg-ok text-bg font-semibold px-5 py-2 rounded-lg text-sm hover:bg-ok/90 disabled:opacity-40 transition-all active:scale-95"
                  >
                    {acting === cp.id + "approve" ? "…" : "✓ Approve & Rewrite"}
                  </button>
                  <button
                    onClick={() => act(cp.id, "reject")}
                    disabled={!!acting}
                    className="bg-bad/10 text-bad border border-bad/30 font-semibold px-5 py-2 rounded-lg text-sm hover:bg-bad/20 disabled:opacity-40 transition-all"
                  >
                    {acting === cp.id + "reject" ? "…" : "✕ Skip"}
                  </button>
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
            <div
              key={cp.id}
              className="bg-panel border border-border rounded-xl px-5 py-3 flex items-center justify-between"
            >
              <div>
                <span className="text-sm font-medium text-text">
                  {cp.scraped_jds?.title ?? "Unknown"}
                </span>
                <span className="text-muted text-sm">
                  {" "}· {cp.scraped_jds?.company ?? "Unknown"}
                </span>
              </div>
              <span
                className={clsx(
                  "text-xs px-2 py-0.5 rounded-full font-medium",
                  cp.status === "approved" && "bg-ok/15 text-ok",
                  cp.status === "rejected" && "bg-bad/15 text-bad",
                  cp.status === "timed_out" && "bg-muted/15 text-muted"
                )}
              >
                {cp.status}
              </span>
            </div>
          ))}
        </div>
      )}

      {!loading && checkpoints.length === 0 && (
        <div className="text-center py-16 text-muted text-sm">
          <div className="text-4xl mb-3">✅</div>
          No checkpoints yet. Run a scraping batch to generate some.
        </div>
      )}
    </div>
  );
}
