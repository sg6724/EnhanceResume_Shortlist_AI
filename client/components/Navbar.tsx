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

function MobileMenu({ active }: { active: string }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [active]);

  return (
    <div className="md:hidden">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-border bg-secondary text-text transition-colors hover:bg-bg"
        aria-label={open ? "Close navigation menu" : "Open navigation menu"}
        aria-expanded={open}
      >
        <span className="sr-only">{open ? "Close navigation menu" : "Open navigation menu"}</span>
        <span className="flex w-5 flex-col gap-1.5">
          <span className={clsx("h-0.5 rounded-full bg-current transition-transform", open && "translate-y-2 rotate-45")} />
          <span className={clsx("h-0.5 rounded-full bg-current transition-opacity", open && "opacity-0")} />
          <span className={clsx("h-0.5 rounded-full bg-current transition-transform", open && "-translate-y-2 -rotate-45")} />
        </span>
      </button>

      {open && (
        <nav className="absolute left-4 right-4 top-full mt-2 rounded-lg border border-border bg-panel p-3 shadow-[0_12px_32px_rgba(20,20,20,0.12)]">
          {DROPDOWNS.map((dropdown) => (
            <div key={dropdown.label} className="py-2 first:pt-0 last:pb-0">
              <div className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
                {dropdown.label}
              </div>
              <div className="grid gap-1">
                {dropdown.items.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={clsx(
                      "rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                      active === item.href ? "bg-bg text-text" : "text-muted hover:bg-bg hover:text-text",
                    )}
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </nav>
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

        <MobileMenu active={path} />

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
