import clsx from "clsx";
import type { ReactNode } from "react";

export function GlassCard({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div
      className={clsx(
        "bg-panel/60 backdrop-blur-xl border border-white/10 rounded-2xl",
        "shadow-[0_8px_32px_rgba(0,0,0,0.35)]",
        className
      )}
    >
      {children}
    </div>
  );
}
