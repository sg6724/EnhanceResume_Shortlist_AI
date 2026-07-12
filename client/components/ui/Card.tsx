import clsx from "clsx";
import type { ReactNode } from "react";

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={clsx("bg-panel border border-border rounded-xl", className)}>{children}</div>;
}
