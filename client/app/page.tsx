"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Stats } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { GlowBackground } from "@/components/ui/GlowBackground";
import { Button } from "@/components/ui/Button";
import { SquiggleUnderline } from "@/components/ui/Doodles";
import clsx from "clsx";

const PIPELINE_STEPS = [
  { label: "Scraper Agent", desc: "Fetches JDs from RemoteOK & Adzuna" },
  { label: "LLM Filter", desc: "Removes irrelevant roles before scoring" },
  { label: "Matcher Agent", desc: "BM25 + embeddings + Gemini scoring" },
  { label: "Checkpoint", desc: "You approve the planned diff" },
  { label: "Rewriter Agent", desc: "Forks & tailors your master resume" },
  { label: "Compiler Agent", desc: "Produces the final PDF via pdflatex" },
];

function RocketIllustration({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 220" fill="none" className={className}>
      <g stroke="currentColor" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
        {/* motion lines */}
        <path d="M10,80 L30,85" opacity={0.5} />
        <path d="M5,110 L28,112" opacity={0.5} />
        <path d="M10,140 L30,136" opacity={0.5} />
        {/* paper airplane (resume page folded) */}
        <path d="M40,150 L180,110 L40,70 L80,110 Z" />
        <path d="M180,110 L80,110" opacity={0.6} />
        {/* text lines on the wing, suggesting resume content */}
        <path d="M55,85 L95,80" opacity={0.4} strokeWidth={2} />
        <path d="M50,95 L100,92" opacity={0.4} strokeWidth={2} />
        {/* rider */}
        <circle cx="90" cy="95" r="8" />
        <path d="M90,103 L90,120" />
        <path d="M90,107 L75,90" />
        <path d="M90,107 L105,90" />
        <path d="M90,120 L80,132" />
        <path d="M90,120 L100,132" />
      </g>
    </svg>
  );
}

function MiniStat({ label, value, color = "text-text" }: { label: string; value: number | string; color?: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <div className="text-muted text-[10px] uppercase tracking-wider font-medium">{label}</div>
      <div className={clsx("text-xl font-bold tabular-nums", color)}>{value}</div>
    </div>
  );
}

export default function LandingPage() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    api.stats().then(setStats).catch(() => {});
  }, []);

  return (
    <div className="space-y-24 pb-16">
      {/* Hero */}
      <section className="relative pt-8">
        <GlowBackground />
        <div className="relative grid md:grid-cols-[1fr_auto] gap-10 items-start">
          <div className="max-w-2xl">
            <h1 className="font-display text-5xl md:text-6xl leading-[1.05] tracking-tight text-text">
              One resume.
              <br />
              Endless{" "}
              <span className="relative inline-block">
                <em className="italic">tailored</em>
                <SquiggleUnderline className="absolute left-0 -bottom-2 w-full h-2.5 text-coral" />
              </span>{" "}
              copies.
            </h1>
            <p className="text-muted text-lg mt-6 max-w-lg">
              Fork your master resume for every job description, score the match with
              BM25 + embeddings + Gemini, and let agents rewrite, compile, and reach out —
              you just approve the checkpoints.
            </p>
            <div className="mt-8 flex items-center gap-4">
              <Button variant="primary" pill asChild>
                <Link href="/dashboard">Open Dashboard →</Link>
              </Button>
            </div>
            <div className="mt-6 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
              <span>{stats?.total_jds ?? "—"} JDs scraped</span>
              <span>·</span>
              <span>{stats?.total_copies ?? "—"} tailored resumes</span>
              <span>·</span>
              <span>{stats?.pending_checkpoints ?? "—"} pending review</span>
            </div>
          </div>
          <RocketIllustration className="hidden md:block w-56 h-56 text-text/70 flex-shrink-0 justify-self-end" />
        </div>

        {/* Mockup panel */}
        <GlassCard className="p-6 mt-16" chromeLabel="dashboard.gethired.ai">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pb-6 mb-6 border-b border-border">
            <MiniStat label="JDs Scraped" value={stats?.total_jds ?? "—"} />
            <MiniStat label="Matches" value={stats?.total_matches ?? "—"} color="text-accent" />
            <MiniStat label="Copies Made" value={stats?.total_copies ?? "—"} color="text-ok" />
            <MiniStat label="Pending" value={stats?.pending_checkpoints ?? "—"} color="text-warn" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {PIPELINE_STEPS.map((step, i) => (
              <div key={i} className="bg-bg rounded-xl p-4 border border-border">
                <div className="text-xs font-semibold text-text">{step.label}</div>
                <div className="text-[11px] text-muted mt-0.5">{step.desc}</div>
              </div>
            ))}
          </div>
        </GlassCard>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="scroll-mt-24">
        <h2 className="font-display text-3xl text-text">
          How it <em className="italic">works</em>
        </h2>
        <p className="text-muted text-sm mt-2 max-w-xl">
          Six agents, sequenced by one orchestrator — no agent calls another.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-8">
          {PIPELINE_STEPS.map((step, i) => (
            <GlassCard key={i} chrome={false} className="p-5">
              <div className="text-[10px] text-muted uppercase tracking-widest font-medium mb-1">
                Step {i + 1}
              </div>
              <div className="text-sm font-semibold text-text">{step.label}</div>
              <div className="text-xs text-muted mt-1">{step.desc}</div>
            </GlassCard>
          ))}
        </div>
      </section>

      {/* Status */}
      <section id="status" className="scroll-mt-24">
        <h2 className="font-display text-3xl text-text">
          Live <em className="italic">status</em>
        </h2>
        <p className="text-muted text-sm mt-2 max-w-xl">
          Real numbers from your pipeline, not a sales deck.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
          <GlassCard chrome={false} className="p-5 flex flex-col gap-1">
            <div className="text-muted text-xs uppercase tracking-widest font-medium">JDs Scraped</div>
            <div className="text-3xl font-bold tabular-nums text-text">{stats?.total_jds ?? "—"}</div>
          </GlassCard>
          <GlassCard chrome={false} className="p-5 flex flex-col gap-1">
            <div className="text-muted text-xs uppercase tracking-widest font-medium">Matches</div>
            <div className="text-3xl font-bold tabular-nums text-accent">{stats?.total_matches ?? "—"}</div>
            <div className="text-muted text-xs">above threshold</div>
          </GlassCard>
          <GlassCard chrome={false} className="p-5 flex flex-col gap-1">
            <div className="text-muted text-xs uppercase tracking-widest font-medium">Copies Made</div>
            <div className="text-3xl font-bold tabular-nums text-ok">{stats?.total_copies ?? "—"}</div>
            <div className="text-muted text-xs">tailored resumes</div>
          </GlassCard>
          <GlassCard chrome={false} className="p-5 flex flex-col gap-1">
            <div className="text-muted text-xs uppercase tracking-widest font-medium">Pending</div>
            <div className={clsx("text-3xl font-bold tabular-nums", stats?.pending_checkpoints ? "text-warn" : "text-text")}>
              {stats?.pending_checkpoints ?? "—"}
            </div>
            <div className="text-muted text-xs">need approval</div>
          </GlassCard>
        </div>
      </section>
    </div>
  );
}
