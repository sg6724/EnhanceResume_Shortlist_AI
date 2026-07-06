"use client";
import { useEffect, useState } from "react";
import { api, type Trace } from "@/lib/api";
import clsx from "clsx";

const AGENT_STYLE: Record<string, string> = {
  orchestrator: "bg-accent/10 text-accent border-accent/20",
  scraper:      "bg-ok/10 text-ok border-ok/20",
  filter:       "bg-warn/10 text-warn border-warn/20",
  matcher:      "bg-purple-400/10 text-purple-400 border-purple-400/20",
  rewriter:     "bg-pink-400/10 text-pink-400 border-pink-400/20",
  compiler:     "bg-bad/10 text-bad border-bad/20",
};

function AgentBadge({ name }: { name: string }) {
  return (
    <span
      className={clsx(
        "inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase tracking-wide",
        AGENT_STYLE[name] ?? "bg-muted/10 text-muted border-muted/20"
      )}
    >
      {name}
    </span>
  );
}

export default function TracesPage() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    const load = () =>
      api.traces()
        .then(setTraces)
        .finally(() => setLoading(false));
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Observability</h1>
        <p className="text-muted text-sm mt-1">
          Real-time agent trace log. Auto-refreshes every 5 s.
        </p>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(AGENT_STYLE).map(([name, style]) => (
          <span
            key={name}
            className={clsx("text-[10px] font-semibold px-2 py-1 rounded-full border uppercase", style)}
          >
            {name}
          </span>
        ))}
      </div>

      {loading && (
        <div className="text-center py-16 text-muted text-sm animate-pulse">Loading…</div>
      )}

      {!loading && traces.length === 0 && (
        <div className="text-center py-16 text-muted text-sm">
          <div className="text-4xl mb-3">🔭</div>
          No traces yet. Run the pipeline to see agent activity here.
        </div>
      )}

      <div className="space-y-2">
        {traces.map((t) => {
          const isOpen = expanded === t.id;
          return (
            <div
              key={t.id}
              className="bg-panel border border-border rounded-xl overflow-hidden"
            >
              <button
                onClick={() => setExpanded(isOpen ? null : t.id)}
                className="w-full text-left px-4 py-3 flex items-center gap-3"
              >
                <AgentBadge name={t.agent_name} />
                <span className="text-sm text-text flex-1 truncate">{t.log}</span>
                <span className="text-[10px] text-muted flex-shrink-0">
                  {new Date(t.created_at).toLocaleTimeString()}
                </span>
                <span className="text-muted text-xs">
                  {isOpen ? "▲" : "▼"}
                </span>
              </button>
              {isOpen && t.reasoning && (
                <div className="px-4 pb-4">
                  <pre className="bg-bg border border-border rounded-lg p-3 text-xs text-muted whitespace-pre-wrap max-h-64 overflow-y-auto font-mono">
                    {t.reasoning}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
