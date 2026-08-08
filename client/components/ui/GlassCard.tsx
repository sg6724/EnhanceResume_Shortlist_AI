import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export function GlassCard({
  className, containerClassName, chrome = true, chromeLabel, children,
}: { className?: string; containerClassName?: string; chrome?: boolean; chromeLabel?: string; children: ReactNode }) {
  return (
    <div
      className={cn(
        "relative w-full max-w-full bg-panel border border-border rounded-2xl overflow-hidden",
        "shadow-[0_8px_30px_rgba(20,20,20,0.06)]",
        containerClassName
      )}
    >
      {chrome && (
        <div className="relative flex items-center px-4 py-3 border-b border-border bg-bg/60">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#FF5F57]" />
            <span className="w-3 h-3 rounded-full bg-[#FEBC2E]" />
            <span className="w-3 h-3 rounded-full bg-[#28C840]" />
          </div>
          {chromeLabel && (
            <div className="absolute left-1/2 -translate-x-1/2 flex max-w-[56%] items-center gap-1.5 truncate px-3 py-1 rounded-full bg-panel border border-border text-[11px] text-muted">
              <svg width="9" height="10" viewBox="0 0 9 10" fill="none" className="text-muted/70">
                <rect x="1" y="4" width="7" height="5" rx="1" stroke="currentColor" strokeWidth="1" />
                <path d="M2.5 4V2.5a2 2 0 0 1 4 0V4" stroke="currentColor" strokeWidth="1" />
              </svg>
              <span className="truncate">{chromeLabel}</span>
            </div>
          )}
        </div>
      )}
      <div className={cn("relative", className)}>{children}</div>
    </div>
  );
}
