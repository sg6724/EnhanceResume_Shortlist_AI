"use client";
import { useEffect, useState, type ComponentType } from "react";
import { api, type Stats } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { GlowBackground } from "@/components/ui/GlowBackground";
import { SquiggleUnderline, DocumentStackIcon, TargetIcon, CopyStackIcon, ClockIcon } from "@/components/ui/Doodles";
import clsx from "clsx";

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

function StatTile({
  icon: Icon, label, value, color, chipClass,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: number | string;
  color: string;
  chipClass: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-bg/50 p-4 sm:p-5">
      <div className={clsx("w-9 h-9 rounded-xl flex items-center justify-center mb-4", chipClass)}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="text-muted text-[11px] uppercase tracking-wider font-medium">{label}</div>
      <div className={clsx("text-3xl font-bold tabular-nums mt-1", color)}>{value}</div>
    </div>
  );
}

export default function LandingPage() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    api.stats().then(setStats).catch(() => {});
  }, []);

  return (
    <div className="space-y-16 md:space-y-24 pb-16">
      {/* Hero */}
      <section className="relative pt-4 md:pt-8">
        <GlowBackground />
        <div className="relative grid md:grid-cols-[1fr_auto] gap-10 items-start">
          <div className="max-w-2xl">
            <h1 className="font-display text-[clamp(3.25rem,15vw,4.5rem)] md:text-6xl leading-[1.05] tracking-tight text-text">
              One resume.
              <br />
              Endless{" "}
              <span className="relative inline-block">
                <em className="italic">tailored</em>
                <SquiggleUnderline className="absolute left-0 -bottom-2 w-full h-2.5 text-coral" />
              </span>{" "}
              copies.
            </h1>
            <p className="text-muted text-base sm:text-lg mt-6 max-w-lg leading-8">
              Paste a job posting or a company&apos;s career page and get back a resume tailored
              to that role, scored against it, and a cover letter ready to review — no manual
              reformatting, no generic templates.
            </p>
          </div>
          <RocketIllustration className="hidden md:block w-56 h-56 text-text/70 flex-shrink-0 justify-self-end" />
        </div>

        {/* Mockup panel */}
        <div className="mt-12 md:mt-16">
          <GlassCard className="p-5 sm:p-8 md:p-10" chromeLabel="dashboard.gethired.ai">
            <div className="flex items-start justify-between gap-4 mb-8">
              <div>
                <div className="text-[11px] uppercase tracking-widest text-muted font-medium">Pipeline overview</div>
                <div className="text-xl font-display text-text mt-0.5">Your dashboard</div>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-ok font-medium">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-ok opacity-60" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-ok" />
                </span>
                Live
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
              <StatTile icon={DocumentStackIcon} label="JDs Scraped" value={stats?.total_jds ?? "—"}
                color="text-text" chipClass="bg-text/5 text-text" />
              <StatTile icon={TargetIcon} label="Matches" value={stats?.total_matches ?? "—"}
                color="text-accent" chipClass="bg-accent/10 text-accent" />
              <StatTile icon={CopyStackIcon} label="Copies Made" value={stats?.total_copies ?? "—"}
                color="text-ok" chipClass="bg-ok/10 text-ok" />
              <StatTile icon={ClockIcon} label="Pending" value={stats?.pending_checkpoints ?? "—"}
                color="text-warn" chipClass="bg-warn/10 text-warn" />
            </div>
          </GlassCard>
        </div>
      </section>
    </div>
  );
}
