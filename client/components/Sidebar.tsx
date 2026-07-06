"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const NAV = [
  { href: "/", label: "Dashboard", icon: "◈" },
  { href: "/positions", label: "Positions", icon: "🎯" },
  { href: "/resume", label: "Master Resume", icon: "📄" },
  { href: "/matches", label: "Job Matches", icon: "🔍" },
  { href: "/checkpoints", label: "Checkpoints", icon: "✅" },
  { href: "/copies", label: "Resume Copies", icon: "📋" },
  { href: "/traces", label: "Observability", icon: "🔭" },
];

export default function Sidebar() {
  const path = usePathname();
  const [dbOk, setDbOk] = useState<boolean | null>(null);

  useEffect(() => {
    api.health()
      .then((h) => setDbOk(h.db))
      .catch(() => setDbOk(false));
    const t = setInterval(() => {
      api.health().then((h) => setDbOk(h.db)).catch(() => setDbOk(false));
    }, 30000);
    return () => clearInterval(t);
  }, []);

  return (
    <aside className="fixed left-0 top-0 h-screen w-56 bg-panel border-r border-border flex flex-col z-20 shadow-xl">
      {/* Logo */}
      <div className="p-5 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-accent/20 flex items-center justify-center text-accent text-sm font-bold">
            JH
          </div>
          <div>
            <div className="text-text font-bold text-sm leading-none">JobHunt AI</div>
            <div className="text-muted text-[10px] mt-0.5">Agentic platform</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
        {NAV.map((item) => {
          const active = path === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all duration-150",
                active
                  ? "bg-accent/15 text-accent font-semibold"
                  : "text-muted hover:text-text hover:bg-white/[0.04]"
              )}
            >
              <span className="text-[15px] w-5 text-center">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Status footer */}
      <div className="p-4 border-t border-border space-y-2">
        <div className="flex items-center gap-1.5">
          <span
            className={clsx(
              "w-1.5 h-1.5 rounded-full",
              dbOk === null ? "bg-muted animate-pulse" : dbOk ? "bg-ok" : "bg-bad"
            )}
          />
          <span className="text-[11px] text-muted">
            {dbOk === null ? "Connecting…" : dbOk ? "DB connected" : "DB offline"}
          </span>
        </div>
        <div className="text-[10px] text-muted truncate" title="tecmaths4mumbai@gmail.com">
          tecmaths4mumbai@gmail.com
        </div>
      </div>
    </aside>
  );
}
