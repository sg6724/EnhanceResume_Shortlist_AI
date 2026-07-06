"use client";
import { useEffect, useState } from "react";
import { api, type ResumeCopy } from "@/lib/api";
import dynamic from "next/dynamic";
import clsx from "clsx";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

const STATUS_STYLE: Record<string, string> = {
  compiled: "bg-ok/15 text-ok",
  failed: "bg-bad/15 text-bad",
  compiling: "bg-warn/15 text-warn",
  pending_approval: "bg-muted/15 text-muted",
  approved: "bg-accent/15 text-accent",
  stale: "bg-muted/15 text-muted",
};

export default function CopiesPage() {
  const [copies, setCopies] = useState<ResumeCopy[]>([]);
  const [selected, setSelected] = useState<ResumeCopy | null>(null);
  const [tex, setTex] = useState("");
  const [compiling, setCompiling] = useState(false);
  const [compileMsg, setCompileMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => api.copies().then(setCopies).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const select = async (copy: ResumeCopy) => {
    const full = await api.copy(copy.id);
    setSelected(full);
    setTex(full.tex_content ?? "");
    setCompileMsg(null);
  };

  const recompile = async () => {
    if (!selected) return;
    setCompiling(true);
    setCompileMsg(null);
    try {
      const res = await api.updateTex(selected.id, tex);
      setCompileMsg({
        text: res.status === "compiled"
          ? "Compiled successfully!"
          : `Compile failed: ${(res.log ?? "").slice(0, 200)}`,
        ok: res.status === "compiled",
      });
      await load();
    } catch (e: any) {
      setCompileMsg({ text: e.message, ok: false });
    } finally {
      setCompiling(false);
    }
  };

  return (
    <div className="flex gap-5 h-[calc(100vh-4rem)]">
      {/* Sidebar list */}
      <div className="w-68 flex-shrink-0 overflow-y-auto space-y-1">
        <div className="mb-4">
          <h1 className="text-xl font-bold">Resume Copies</h1>
          <p className="text-muted text-xs mt-0.5">Select to view or edit.</p>
        </div>

        {loading && (
          <div className="text-muted text-xs animate-pulse text-center py-8">Loading…</div>
        )}
        {!loading && copies.length === 0 && (
          <div className="text-muted text-xs text-center py-8">
            No copies yet. Approve a checkpoint to generate one.
          </div>
        )}
        {copies.map((c) => (
          <button
            key={c.id}
            onClick={() => select(c)}
            className={clsx(
              "w-full text-left rounded-xl px-4 py-3 border transition-all",
              selected?.id === c.id
                ? "bg-panel border-accent"
                : "bg-panel border-border hover:border-muted"
            )}
          >
            <div className="text-sm font-medium text-text truncate">
              {c.scraped_jds?.title ?? "—"}
            </div>
            <div className="text-xs text-muted truncate">
              {c.scraped_jds?.company ?? "—"}
            </div>
            <span
              className={clsx(
                "inline-block mt-1.5 text-[10px] px-2 py-0.5 rounded-full font-medium",
                STATUS_STYLE[c.status] ?? "bg-muted/15 text-muted"
              )}
            >
              {c.status}
            </span>
          </button>
        ))}
      </div>

      {/* Editor panel */}
      <div className="flex-1 flex flex-col min-w-0">
        {selected ? (
          <>
            {/* Toolbar */}
            <div className="flex items-center justify-between mb-3 flex-shrink-0 gap-4">
              <div className="min-w-0">
                <div className="font-semibold text-text truncate">
                  {selected.scraped_jds?.title} — {selected.scraped_jds?.company}
                </div>
                {selected.diff_patch && (
                  <div className="text-xs text-muted mt-0.5 truncate">
                    {selected.diff_patch.slice(0, 100)}
                  </div>
                )}
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <button
                  onClick={recompile}
                  disabled={compiling}
                  className={clsx(
                    "text-sm font-semibold px-4 py-2 rounded-lg transition-all",
                    compiling
                      ? "bg-accent/30 text-accent/50 cursor-not-allowed"
                      : "bg-accent text-bg hover:bg-accent/90 active:scale-95"
                  )}
                >
                  {compiling ? (
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-3 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
                      Compiling…
                    </span>
                  ) : (
                    "⟳ Recompile"
                  )}
                </button>
                <button
                  onClick={() => api.markApplied(selected.id).then(load)}
                  className="text-sm px-4 py-2 rounded-lg bg-ok/10 text-ok border border-ok/30 hover:bg-ok/20 transition-colors"
                >
                  ✓ Mark Applied
                </button>
              </div>
            </div>

            {/* Compile message */}
            {compileMsg && (
              <div
                className={clsx(
                  "text-xs mb-2 px-3 py-2 rounded-lg border",
                  compileMsg.ok
                    ? "bg-ok/10 text-ok border-ok/20"
                    : "bg-bad/10 text-bad border-bad/20"
                )}
              >
                {compileMsg.text}
              </div>
            )}

            {/* Monaco Editor */}
            <div className="flex-1 border border-border rounded-xl overflow-hidden">
              <MonacoEditor
                height="100%"
                language="latex"
                theme="vs-dark"
                value={tex}
                onChange={(v) => setTex(v ?? "")}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  lineHeight: 20,
                  wordWrap: "on",
                  scrollBeyondLastLine: false,
                  padding: { top: 12, bottom: 12 },
                }}
              />
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-muted gap-3">
            <div className="text-5xl">📋</div>
            <div className="text-sm">Select a resume copy from the left to edit.</div>
          </div>
        )}
      </div>
    </div>
  );
}
