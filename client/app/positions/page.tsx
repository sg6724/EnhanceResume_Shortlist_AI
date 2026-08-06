"use client";
import { useEffect, useState } from "react";
import { api, type Position } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { SketchArrow } from "@/components/ui/Doodles";

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
        title="Target"
        titleEmphasis="Positions"
        description="The job titles the scraper searches for. Add fuzzy keywords to catch semantically related roles."
      />

      {/* Add form */}
      <Card>
        <CardHeader>
          <CardTitle>Add Position</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="position-title">Position title</Label>
            <Input
              id="position-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && add()}
              placeholder="e.g. AI Engineer"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="position-keywords">Fuzzy keywords</Label>
            <Input
              id="position-keywords"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="Comma-separated, e.g. ML Engineer, LLM Engineer"
            />
          </div>
          {error && <div className="text-bad text-xs">{error}</div>}
          <Button onClick={add} disabled={saving || !title.trim()}>
            {saving ? "Adding…" : "Add Position"}
          </Button>
        </CardContent>
      </Card>

      {/* List */}
      <div className="space-y-2">
        {positions.length === 0 && (
          <div className="text-center py-16 text-muted text-sm flex flex-col items-center gap-2">
            <SketchArrow className="w-16 h-8 text-muted/50 -scale-y-100" />
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
