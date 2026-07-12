import clsx from "clsx";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ok" | "danger" | "ghost";

export function Button({
  variant = "primary", pill = false, className, children, ...props
}: {
  variant?: Variant; pill?: boolean; className?: string;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={clsx(
        "font-semibold text-sm transition-all active:scale-95",
        "disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100",
        pill ? "rounded-full px-6 py-2.5" : "rounded-lg px-4 py-2",
        variant === "primary" && "bg-accent text-bg hover:bg-accent/90 shadow-[0_0_24px_rgba(110,168,254,0.35)]",
        variant === "secondary" && "bg-white/[0.06] text-text hover:bg-white/[0.1]",
        variant === "ok" && "bg-ok text-bg hover:bg-ok/90 shadow-[0_0_24px_rgba(52,211,153,0.3)]",
        variant === "danger" && "bg-bad/10 text-bad border border-bad/30 hover:bg-bad/20",
        variant === "ghost" && "text-muted hover:text-text",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
