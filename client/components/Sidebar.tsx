"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/positions", label: "Positions" },
  { href: "/resume", label: "Master Resume" },
  { href: "/matches", label: "Job Matches" },
  { href: "/checkpoints", label: "Checkpoints" },
  { href: "/outreach", label: "Outreach" },
  { href: "/copies", label: "Resume Copies" },
  { href: "/traces", label: "Observability" },
];

export default function Sidebar() {
  const path = usePathname();
  const [dbOk, setDbOk] = useState<boolean | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    const check = () =>
      api.health()
        .then((h) => { setDbOk(h.db); setUserEmail(h.user_email); })
        .catch(() => setDbOk(false));
    check();
    const t = setInterval(check, 30000);
    return () => clearInterval(t);
  }, []);

  return (
    <aside className="fixed left-0 top-0 h-screen w-56 bg-panel border-r border-border flex flex-col z-20 shadow-xl">
      {/* Logo */}
      <div className="p-5 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-accent/20 flex items-center justify-center text-accent text-sm font-bold">
            GH
          </div>
          <div>
            <div className="text-text font-bold text-sm leading-none">GetHired AI</div>
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
                "block px-3 py-2 rounded-lg text-sm transition-all duration-150",
                active
                  ? "bg-accent/15 text-accent font-semibold"
                  : "text-muted hover:text-text hover:bg-white/[0.04]"
              )}
            >
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
        {userEmail && (
          <div className="text-[10px] text-muted truncate" title={userEmail}>
            {userEmail}
          </div>
        )}
      </div>
    </aside>
  );
}
