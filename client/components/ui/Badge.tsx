import clsx from "clsx";
import type { ReactNode } from "react";

export type Tone = "ok" | "bad" | "warn" | "accent" | "muted";

const TONE_STYLE: Record<Tone, string> = {
  ok: "bg-ok/15 text-ok",
  bad: "bg-bad/15 text-bad",
  warn: "bg-warn/15 text-warn",
  accent: "bg-accent/15 text-accent",
  muted: "bg-muted/15 text-muted",
};

export function Badge({ tone = "muted", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={clsx("text-[11px] px-2 py-0.5 rounded-full font-medium", TONE_STYLE[tone])}>
      {children}
    </span>
  );
}
