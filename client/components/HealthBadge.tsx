"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Health = { status: string; db: boolean };

export default function HealthBadge() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then((data: Health) => setHealth(data))
      .catch(() => setError(true));
  }, []);

  if (error) return <span className="badge bad">API unreachable</span>;
  if (!health) return <span className="badge muted">checking…</span>;

  return (
    <span className={`badge ${health.db ? "ok" : "bad"}`}>
      API {health.status} · DB {health.db ? "connected" : "down"}
    </span>
  );
}
