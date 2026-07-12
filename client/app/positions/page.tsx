"use client";
import { useEffect, useState } from "react";
import { api, type Position } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

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
    <div className="max-w-2xl space-y-8">
      <PageHeader
        title="Target Positions"
        description="The job titles the scraper searches for. Add fuzzy keywords to catch semantically related roles."
      />

      {/* Add form */}
      <Card className="p-5 space-y-3">
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
        <Button onClick={add} disabled={saving || !title.trim()}>
          {saving ? "Adding…" : "Add Position"}
        </Button>
      </Card>

      {/* List */}
      <div className="space-y-2">
        {positions.length === 0 && (
          <div className="text-center py-16 text-muted text-sm">
            No positions yet. Add one above to start scraping.
          </div>
        )}
        {positions.map((p) => (
          <Card key={p.id} className="px-5 py-4 flex items-center justify-between gap-4">
            <div className="min-w-0">
              <div className="font-medium text-sm text-text">{p.title}</div>
              {p.fuzzy_keywords.length > 0 && (
                <div className="text-muted text-xs mt-0.5 truncate">
                  {p.fuzzy_keywords.join(", ")}
                </div>
              )}
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <Badge tone={p.is_active ? "ok" : "muted"}>
                {p.is_active ? "Active" : "Paused"}
              </Badge>
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
          </Card>
        ))}
      </div>
    </div>
  );
}
