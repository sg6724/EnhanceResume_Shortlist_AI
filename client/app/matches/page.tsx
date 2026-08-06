"use client";
import { useEffect, useRef, useState } from "react";
import { api, type JdMatch } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { GlassCard } from "@/components/ui/GlassCard";
import { Badge } from "@/components/ui/Badge";
import { SketchArrow } from "@/components/ui/Doodles";
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

function ScoreRing({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const tone = pct >= 70 ? "text-ok" : pct >= 50 ? "text-warn" : "text-bad";
  const circumference = 2 * Math.PI * 26;
  const offset = circumference * (1 - value);
  return (
    <div className="relative w-16 h-16 flex-shrink-0">
      <svg viewBox="0 0 60 60" className="w-16 h-16 -rotate-90">
        <circle cx="30" cy="30" r="26" fill="none" stroke="currentColor" strokeWidth="5" className="text-border" />
        <circle
          cx="30" cy="30" r="26" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          className={clsx("transition-all duration-700", tone)}
        />
      </svg>
      <div className={clsx("absolute inset-0 flex items-center justify-center text-sm font-bold tabular-nums", tone)}>
        {pct}%
      </div>
    </div>
  );
}

function NavButton({ direction, onClick, disabled }: { direction: "prev" | "next"; onClick: () => void; disabled: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={direction === "prev" ? "Previous match" : "Next match"}
      className={clsx(
        "w-9 h-9 rounded-full border border-border bg-panel flex items-center justify-center transition-all",
        disabled ? "opacity-30 cursor-not-allowed" : "hover:border-text/30 hover:shadow-[0_4px_14px_rgba(20,20,20,0.08)]",
      )}
    >
      <svg width="7" height="12" viewBox="0 0 7 12" fill="none" className={clsx("text-text", direction === "next" && "rotate-180")}>
        <path d="M6 1L1 6l5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  );
}

const CARD_WIDTH_CLASS = "w-[min(90vw,480px)] snap-start flex-shrink-0";

export default function MatchesPage() {
  const [matches, setMatches] = useState<JdMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(0);
  const trackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.matches()
      .then(setMatches)
      .finally(() => setLoading(false));
  }, []);

  const scrollToIndex = (index: number) => {
    const track = trackRef.current;
    if (!track) return;
    const card = track.children[index] as HTMLElement | undefined;
    if (card) track.scrollTo({ left: card.offsetLeft - track.offsetLeft, behavior: "smooth" });
  };

  const onScroll = () => {
    const track = trackRef.current;
    if (!track) return;
    let closest = 0;
    let closestDist = Infinity;
    Array.from(track.children).forEach((child, i) => {
      const el = child as HTMLElement;
      const dist = Math.abs(el.offsetLeft - track.offsetLeft - track.scrollLeft);
      if (dist < closestDist) {
        closestDist = dist;
        closest = i;
      }
    });
    setActive(closest);
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Job"
        titleEmphasis="Matches"
        description="Most recent first. Each card shows how your resume scores against that job."
        action={
          matches.length > 1 ? (
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted tabular-nums">{active + 1} / {matches.length}</span>
              <div className="flex items-center gap-2">
                <NavButton direction="prev" disabled={active === 0} onClick={() => scrollToIndex(active - 1)} />
                <NavButton direction="next" disabled={active === matches.length - 1} onClick={() => scrollToIndex(active + 1)} />
              </div>
            </div>
          ) : undefined
        }
      />

      {loading && (
        <div className="text-center py-16 text-muted text-sm animate-pulse">Loading matches…</div>
      )}

      {!loading && matches.length === 0 && (
        <div className="text-center py-16 text-muted text-sm flex flex-col items-center gap-2">
          <SketchArrow className="w-16 h-8 text-muted/50 -scale-y-100" />
          No matches yet. Run Quick Match or Application Prep to score your resume against a job.
        </div>
      )}

      {!loading && matches.length > 0 && (
        <div
          ref={trackRef}
          onScroll={onScroll}
          className="flex gap-5 overflow-x-auto snap-x snap-mandatory pb-4 -mx-1 px-1 scroll-smooth"
          style={{ scrollbarWidth: "none" }}
        >
          {matches.map((m) => (
            <GlassCard key={m.id} chrome={false} className={clsx(CARD_WIDTH_CLASS, "p-6 space-y-5")}>
              {/* Header */}
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="font-semibold text-text truncate text-lg">
                    {m.scraped_jds?.title ?? "Unknown Title"}
                  </div>
                  <div className="text-muted text-sm mt-0.5 truncate">
                    {m.scraped_jds?.company ?? "Unknown"}{" "}
                    {m.scraped_jds?.location && <span>· {m.scraped_jds.location}</span>}
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-[10px] text-muted bg-bg border border-border px-2 py-0.5 rounded-full uppercase tracking-wide">
                      {m.scraped_jds?.source ?? "?"}
                    </span>
                    <span className="text-[10px] text-muted">{m.position_context}</span>
                  </div>
                </div>
                <ScoreRing value={m.composite_score} />
              </div>

              {/* Score breakdown */}
              <div className="grid grid-cols-3 gap-4">
                {[
                  { label: "Keywords", score: m.keyword_score, color: "bg-accent" },
                  { label: "Semantic", score: m.semantic_score, color: "bg-ok" },
                  { label: "LLM", score: m.llm_score, color: "bg-warn" },
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
                <div className="bg-bg rounded-xl p-3.5 text-xs text-muted whitespace-pre-line border border-border max-h-32 overflow-y-auto">
                  <div className="text-[10px] uppercase tracking-wider text-muted mb-1 font-medium">
                    Gap Analysis
                  </div>
                  {m.gap_analysis}
                </div>
              )}

              {/* Matched / Missing skills */}
              {Boolean(m.matched_skills?.length || m.missing_skills?.length) && (
                <div className="space-y-3">
                  {m.matched_skills?.length ? (
                    <div>
                      <div className="text-[10px] uppercase tracking-wider text-ok mb-1.5 font-medium">Matched</div>
                      <div className="flex flex-wrap gap-1.5">
                        {m.matched_skills.map((s) => <Badge key={s} tone="ok">{s}</Badge>)}
                      </div>
                    </div>
                  ) : null}
                  {m.missing_skills?.length ? (
                    <div>
                      <div className="text-[10px] uppercase tracking-wider text-bad mb-1.5 font-medium">Missing</div>
                      <div className="flex flex-wrap gap-1.5">
                        {m.missing_skills.map((s) => <Badge key={s} tone="bad">{s}</Badge>)}
                      </div>
                    </div>
                  ) : null}
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
            </GlassCard>
          ))}
        </div>
      )}

      {!loading && matches.length > 1 && (
        <div className="flex items-center justify-center gap-1.5">
          {matches.map((_, i) => (
            <button
              key={i}
              onClick={() => scrollToIndex(i)}
              aria-label={`Go to match ${i + 1}`}
              className={clsx(
                "h-1.5 rounded-full transition-all",
                i === active ? "w-6 bg-text" : "w-1.5 bg-border hover:bg-muted",
              )}
            />
          ))}
        </div>
      )}
    </div>
  );
}
