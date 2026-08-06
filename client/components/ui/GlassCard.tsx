import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export function GlassCard({
  className, chrome = true, chromeLabel, children,
}: { className?: string; chrome?: boolean; chromeLabel?: string; children: ReactNode }) {
  return (
    <div
      className={cn(
        "relative bg-panel border border-border rounded-2xl overflow-hidden",
        "shadow-[0_8px_30px_rgba(20,20,20,0.06)]"
      )}
    >
      {chrome && (
        <div className="flex items-center gap-1.5 px-4 py-2.5 border-b border-border bg-bg/40">
          <span className="w-2.5 h-2.5 rounded-full bg-coral/70" />
          <span className="w-2.5 h-2.5 rounded-full bg-warn/70" />
          <span className="w-2.5 h-2.5 rounded-full bg-ok/70" />
          {chromeLabel && <span className="ml-2 text-[11px] text-muted">{chromeLabel}</span>}
        </div>
      )}
      <div className={cn("relative", className)}>{children}</div>
    </div>
  );
}
