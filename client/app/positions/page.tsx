"use client";
import { useEffect, useState } from "react";
import { api, type Position } from "@/lib/api";
import clsx from "clsx";

export default function PositionsPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [title, setTitle] = useState("");
  const [keywords, setKeywords] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = () => api.positions().then(setPositions).catch(() => {});
  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!title.trim()) return;
    setSaving(true);
    setError("");
    try {
      await api.createPosition(
        title.trim(),
        keywords.split(",").map((k) => k.trim()).filter(Boolean)
      );
      setTitle("");
      setKeywords("");
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Target Positions</h1>
        <p className="text-muted text-sm mt-1">
          The job titles the scraper searches for. Add fuzzy keywords to catch
          semantically related roles.
        </p>
      </div>

      {/* Add form */}
      <div className="bg-panel border border-border rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-text">Add Position</h2>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          placeholder="Position title (e.g. AI Engineer)"
          className="w-full bg-bg border border-border rounded-lg px-3 py-2.5 text-sm text-text placeholder:text-muted focus:outline-none focus:border-accent transition-colors"
        />
        <input
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          placeholder="Fuzzy keywords, comma-separated (e.g. ML Engineer, LLM Engineer)"
          className="w-full bg-bg border border-border rounded-lg px-3 py-2.5 text-sm text-text placeholder:text-muted focus:outline-none focus:border-accent transition-colors"
        />
        {error && <div className="text-bad text-xs">{error}</div>}
        <button
          onClick={add}
          disabled={saving || !title.trim()}
          className="bg-accent text-bg font-semibold px-5 py-2 rounded-lg text-sm hover:bg-accent/90 disabled:opacity-40 transition-all"
        >
          {saving ? "Adding…" : "+ Add Position"}
        </button>
      </div>

      {/* List */}
      <div className="space-y-2">
        {positions.length === 0 && (
          <div className="text-center py-16 text-muted text-sm">
            No positions yet. Add one above to start scraping.
          </div>
        )}
        {positions.map((p) => (
          <div
            key={p.id}
            className="bg-panel border border-border rounded-xl px-5 py-4 flex items-center justify-between gap-4"
          >
            <div className="min-w-0">
              <div className="font-medium text-sm text-text">{p.title}</div>
              {p.fuzzy_keywords.length > 0 && (
                <div className="text-muted text-xs mt-0.5 truncate">
                  {p.fuzzy_keywords.join(", ")}
                </div>
              )}
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span
                className={clsx(
                  "text-[11px] px-2 py-0.5 rounded-full font-medium",
                  p.is_active
                    ? "bg-ok/15 text-ok"
                    : "bg-muted/15 text-muted"
                )}
              >
                {p.is_active ? "Active" : "Paused"}
              </span>
              <button
                onClick={() => api.togglePosition(p.id).then(load)}
                className="text-xs text-muted hover:text-accent px-2 py-1 rounded transition-colors"
              >
                {p.is_active ? "Pause" : "Activate"}
              </button>
              <button
                onClick={() => api.deletePosition(p.id).then(load)}
                className="text-xs text-bad hover:text-bad/70 px-2 py-1 rounded transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
