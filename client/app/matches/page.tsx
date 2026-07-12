"use client";
import { useEffect, useState } from "react";
import { api, type JdMatch } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import clsx from "clsx";

function ScoreBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="h-1.5 bg-border rounded-full overflow-hidden">
      <div
        className={clsx("h-full rounded-full transition-all duration-500", color)}
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  );
}

function ScoreChip({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <span
      className={clsx(
        "text-xl font-bold tabular-nums",
        pct >= 70 ? "text-ok" : pct >= 50 ? "text-warn" : "text-bad"
      )}
    >
      {pct}%
    </span>
  );
}

export default function MatchesPage() {
  const [matches, setMatches] = useState<JdMatch[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.matches()
      .then(setMatches)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-3xl space-y-8">
      <PageHeader
        title="Job Matches"
        description="JDs ranked by composite match score (BM25 30% + semantic 30% + Gemini LLM 40%)."
      />

      {loading && (
        <div className="text-center py-16 text-muted text-sm animate-pulse">Loading matches…</div>
      )}

      {!loading && matches.length === 0 && (
        <div className="text-center py-16 text-muted text-sm">
          No matches yet. Run a scraping batch from the{" "}
          <a href="/" className="text-accent hover:underline">Dashboard</a>.
        </div>
      )}

      <div className="space-y-4">
        {matches.map((m) => (
          <Card key={m.id} className="p-5 space-y-4">
            {/* Header */}
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="font-semibold text-text truncate">
                  {m.scraped_jds?.title ?? "Unknown Title"}
                </div>
                <div className="text-muted text-sm mt-0.5">
                  {m.scraped_jds?.company ?? "Unknown"}{" "}
                  {m.scraped_jds?.location && <span>· {m.scraped_jds.location}</span>}
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-[10px] text-muted bg-border px-2 py-0.5 rounded-full uppercase tracking-wide">
                    {m.scraped_jds?.source ?? "?"}
                  </span>
                  <span className="text-[10px] text-muted">{m.position_context}</span>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <ScoreChip value={m.composite_score} />
                <div className="text-[10px] text-muted mt-0.5">composite</div>
              </div>
            </div>

            {/* Score breakdown */}
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "Keywords (BM25)", score: m.keyword_score, color: "bg-accent" },
                { label: "Semantic", score: m.semantic_score, color: "bg-ok" },
                { label: "LLM (Gemini)", score: m.llm_score, color: "bg-warn" },
              ].map(({ label, score, color }) => (
                <div key={label}>
                  <div className="flex justify-between text-[11px] text-muted mb-1">
                    <span>{label}</span>
                    <span>{Math.round(score * 100)}%</span>
                  </div>
                  <ScoreBar value={score} color={color} />
                </div>
              ))}
            </div>

            {/* Gap analysis */}
            {m.gap_analysis && (
              <div className="bg-bg rounded-lg p-3 text-xs text-muted whitespace-pre-line border border-border">
                <div className="text-[10px] uppercase tracking-wider text-muted mb-1 font-medium">
                  Gap Analysis
                </div>
                {m.gap_analysis}
              </div>
            )}

            {/* Link */}
            {m.scraped_jds?.url && (
              <a
                href={m.scraped_jds.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block text-xs text-accent hover:underline"
              >
                View original JD →
              </a>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
