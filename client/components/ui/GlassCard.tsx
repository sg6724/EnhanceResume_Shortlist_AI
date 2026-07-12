import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export function GlassCard({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div
      className={cn(
        "relative bg-panel/40 backdrop-blur-xl border border-white/15 rounded-2xl overflow-hidden",
        "shadow-[0_8px_32px_rgba(0,0,0,0.45)]",
        "before:absolute before:inset-0 before:pointer-events-none",
        "before:bg-gradient-to-b before:from-white/[0.07] before:to-transparent",
        className
      )}
    >
      <div className="relative">{children}</div>
    </div>
  );
}
