"use client";
import { useEffect, useState } from "react";
import { api, type Stats } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { GlassCard } from "@/components/ui/GlassCard";
import { GlowBackground } from "@/components/ui/GlowBackground";
import { Button } from "@/components/ui/Button";
import clsx from "clsx";

function StatTile({
  label, value, sub, color = "text-text",
}: { label: string; value: number | string; sub?: string; color?: string }) {
  return (
    <GlassCard className="p-5 flex flex-col gap-1">
      <div className="text-muted text-xs uppercase tracking-widest font-medium">{label}</div>
      <div className={clsx("text-3xl font-bold tabular-nums", color)}>{value}</div>
      {sub && <div className="text-muted text-xs">{sub}</div>}
    </GlassCard>
  );
}

const PIPELINE_STEPS = [
  { label: "Scraper Agent", desc: "Fetches JDs from RemoteOK & Adzuna" },
  { label: "LLM Filter", desc: "Removes irrelevant roles before scoring" },
  { label: "Matcher Agent", desc: "BM25 + embeddings + Gemini scoring" },
  { label: "Checkpoint", desc: "You approve the planned diff" },
  { label: "Rewriter Agent", desc: "Forks & tailors your master resume" },
  { label: "Compiler Agent", desc: "Produces the final PDF via pdflatex" },
];

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [scraping, setScraping] = useState(false);
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

  useEffect(() => {
    const load = () => api.stats().then(setStats).catch(() => {});
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, []);

  const handleScrape = async () => {
    setScraping(true);
    setMsg(null);
    try {
      await api.triggerScrape();
      setMsg({ text: "Scraping batch queued! The worker will process it in the background.", ok: true });
    } catch (e: any) {
      setMsg({ text: e.message ?? "Failed to queue scrape.", ok: false });
    } finally {
      setScraping(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-8">
      <div className="relative">
        <GlowBackground />

        <PageHeader
          title="Dashboard"
          description="Your agentic job-hunting pipeline — set positions, run batches, review results."
        />

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
          <StatTile label="JDs Scraped" value={stats?.total_jds ?? "—"} />
          <StatTile
            label="Matches" value={stats?.total_matches ?? "—"}
            color="text-accent" sub="above threshold"
          />
          <StatTile
            label="Copies Made" value={stats?.total_copies ?? "—"}
            color="text-ok" sub="tailored resumes"
          />
          <StatTile
            label="Pending" value={stats?.pending_checkpoints ?? "—"}
            color={stats?.pending_checkpoints ? "text-warn" : "text-text"} sub="need approval"
          />
        </div>

        {/* Run pipeline */}
        <GlassCard className="p-6 mt-8">
          <div className="flex items-start justify-between gap-6">
            <div>
              <h2 className="font-semibold text-text mb-1">Run Scraping Batch</h2>
              <p className="text-muted text-sm max-w-md">
                Scrapes job listings for your active target positions, scores them
                against your master resume, and queues tailored copies for your review.
              </p>
            </div>
            <Button pill onClick={handleScrape} disabled={scraping} className="flex-shrink-0">
              {scraping ? (
                <span className="flex items-center gap-2">
                  <span className="w-3.5 h-3.5 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
                  Queuing…
                </span>
              ) : (
                "Run Batch"
              )}
            </Button>
          </div>
          {msg && (
            <div
              className={clsx(
                "mt-4 text-sm px-4 py-3 rounded-lg",
                msg.ok ? "bg-ok/10 text-ok border border-ok/20" : "bg-bad/10 text-bad border border-bad/20"
              )}
            >
              {msg.text}
            </div>
          )}
        </GlassCard>

        {/* Pipeline overview */}
        <GlassCard className="p-6 mt-8">
          <h2 className="font-semibold text-text mb-4">Pipeline Architecture</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {PIPELINE_STEPS.map((step, i) => (
              <div key={i} className="bg-bg rounded-xl p-4 border border-border">
                <div className="text-xs font-semibold text-text">{step.label}</div>
                <div className="text-[11px] text-muted mt-0.5">{step.desc}</div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* Quick links */}
      {(stats?.pending_checkpoints ?? 0) > 0 && (
        <div className="bg-warn/10 border border-warn/30 rounded-xl px-5 py-4 flex items-center justify-between">
          <div>
            <div className="text-warn font-semibold text-sm">
              {stats!.pending_checkpoints} checkpoint{stats!.pending_checkpoints !== 1 ? "s" : ""} awaiting approval
            </div>
            <div className="text-muted text-xs mt-0.5">
              Review the planned diffs and approve to start rewriting.
            </div>
          </div>
          <a href="/checkpoints" className="text-sm text-warn font-semibold hover:underline">
            Review →
          </a>
        </div>
      )}
    </div>
  );
}
