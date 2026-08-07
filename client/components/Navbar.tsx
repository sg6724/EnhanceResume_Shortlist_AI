"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { Button } from "@/components/ui/Button";

type NavItem = { href: string; label: string };

const DROPDOWNS: { label: string; items: NavItem[] }[] = [
  {
    label: "Product",
    items: [
      { href: "/positions", label: "Positions" },
      { href: "/resume", label: "Master Resume" },
      { href: "/quick-match", label: "Quick Match" },
    ],
  },
  {
    label: "Pipeline",
    items: [
      { href: "/matches", label: "Job Matches" },
      { href: "/checkpoints", label: "Checkpoints" },
      { href: "/traces", label: "Observability" },
    ],
  },
  {
    label: "Applications",
    items: [
      { href: "/outreach", label: "Application Prep" },
      { href: "/copies", label: "Resume Copies" },
    ],
  },
];

function NavDropdown({ label, items, active }: { label: string; items: NavItem[]; active: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const isActiveGroup = items.some((item) => active === item.href);

  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((value) => !value)}
        className={clsx(
          "flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
          isActiveGroup ? "text-text font-semibold" : "text-muted hover:text-text",
        )}
      >
        {label}
        <svg width="10" height="6" viewBox="0 0 10 6" fill="none" className={clsx("transition-transform", open && "rotate-180")}>
          <path d="M1 1l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-1 w-52 bg-panel border border-border rounded-xl shadow-[0_8px_30px_rgba(20,20,20,0.1)] overflow-hidden z-30">
          {items.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setOpen(false)}
              className={clsx(
                "block px-4 py-2.5 text-sm transition-colors",
                active === item.href ? "bg-bg text-text font-semibold" : "text-muted hover:text-text hover:bg-bg",
              )}
            >
              {item.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function Navbar() {
  const path = usePathname();
  const isLanding = path === "/";

  return (
    <header className="sticky top-0 z-20 bg-bg/80 backdrop-blur-md border-b border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-10 min-h-16 py-3 md:py-0 flex flex-wrap md:flex-nowrap items-center justify-between gap-3 md:gap-4">
        <Link href="/" className="font-display text-lg font-semibold text-text flex-shrink-0">
          GetHired AI
        </Link>

        <nav className="hidden md:flex items-center gap-1 flex-1 justify-center">
          {DROPDOWNS.map((dropdown) => (
            <NavDropdown key={dropdown.label} label={dropdown.label} items={dropdown.items} active={path} />
          ))}
        </nav>

        {isLanding ? (
          <div className="grid grid-cols-2 gap-2 sm:flex sm:items-center sm:gap-3 w-full sm:w-auto flex-shrink-0">
            <Button variant="secondary" pill asChild className="px-4 sm:px-6">
              <Link href="/quick-match">Quick Match</Link>
            </Button>
            <Button variant="primary" pill asChild className="px-4 sm:px-6">
              <Link href="/outreach">Application Prep</Link>
            </Button>
          </div>
        ) : (
          <div className="w-32 flex-shrink-0" />
        )}
      </div>
    </header>
  );
}
