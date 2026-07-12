"use client";
import { useState } from "react";
import { api, type MasterResumeUploadResult } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Textarea";
import { Label } from "@/components/ui/Label";

const EXAMPLE_TEX = `\\documentclass[11pt,a4paper]{article}
\\usepackage[margin=1in]{geometry}
\\usepackage{enumitem}
\\begin{document}

\\begin{center}
  {\\Large\\bfseries Your Name}\\\\[4pt]
  your@email.com \\quad | \\quad github.com/yourname
\\end{center}

\\section*{Summary}
Experienced AI Engineer with 3+ years building production LLM systems,
RAG pipelines, and scalable ML infrastructure.

\\section*{Experience}
\\begin{itemize}[leftmargin=*]
  \\item Led development of an LLM-powered document Q\\&A system at Acme Corp (2022--2024)
  \\item Built ML pipelines processing 1M+ records daily with PyTorch and FastAPI
  \\item Reduced inference latency by 40\\% via model quantisation and caching
\\end{itemize}

\\section*{Skills}
Python, PyTorch, FastAPI, LangChain, RAG, LLM fine-tuning, Docker, PostgreSQL

\\end{document}`;

export default function ResumePage() {
  const [tex, setTex] = useState("");
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<MasterResumeUploadResult | null>(null);
  const [error, setError] = useState("");

  const upload = async () => {
    if (!tex.trim()) return;
    setUploading(true);
    setError("");
    setResult(null);
    try {
      const r = await api.uploadResume(tex);
      setResult(r);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-8">
      <PageHeader
        title="Master Resume"
        description="Your LaTeX source of truth. Agents fork from this — they never modify it directly. Uploading a new version marks existing copies as stale."
      />

      <Card>
        <CardHeader className="flex items-center justify-between">
          <Label htmlFor="tex-source">LaTeX Source (.tex)</Label>
          {!tex && (
            <button
              onClick={() => setTex(EXAMPLE_TEX)}
              className="text-xs text-accent hover:underline"
            >
              Load example
            </button>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            id="tex-source"
            value={tex}
            onChange={(e) => setTex(e.target.value)}
            placeholder={EXAMPLE_TEX}
            rows={22}
            spellCheck={false}
            className="font-mono"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted">{tex.length.toLocaleString()} chars</span>
            <Button pill onClick={upload} disabled={uploading || !tex.trim()}>
              {uploading ? "Uploading…" : "Upload Master Resume"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {result && (
        <div className="bg-ok/10 border border-ok/30 rounded-xl p-4 text-sm">
          <div className="font-semibold text-ok mb-1">Uploaded successfully</div>
          <div className="text-muted space-y-0.5 text-xs">
            <div>Version: <span className="text-text">{result.version}</span></div>
            <div>Plain text extracted: <span className="text-text">{result.plain_text_chars.toLocaleString()} chars</span></div>
            <div>ID: <span className="text-text font-mono">{result.id}</span></div>
          </div>
        </div>
      )}
      {error && (
        <div className="bg-bad/10 border border-bad/30 rounded-xl p-4 text-sm text-bad">
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Rules the agents follow</CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-muted space-y-1.5">
          <div>• Only edit content inside existing <code className="bg-bg px-1 rounded">\begin{"{}"}...\end{"{}"}</code> blocks</div>
          <div>• Never add or delete LaTeX environments</div>
          <div>• Never modify your preamble or packages</div>
          <div>• Return the full .tex + a diff of every change made</div>
        </CardContent>
      </Card>
    </div>
  );
}
