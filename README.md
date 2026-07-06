# Enhance_and_shortlist_AI

A personal, single-user agentic platform that automates tailoring a LaTeX master resume to job
descriptions. You paste company career-page URLs (or direct JD URLs) into a dashboard and set your
target position titles; the backend agent pipeline scrapes JDs, filters, scores, rewrites a **fork**
of your master resume for each role, compiles it to PDF, and surfaces the results for review.

Core mental model: the master `.tex` is the **"real DOM"** (never mutated); each JD-specific copy is a
**"virtual DOM"** fork — patched, rendered, diffed against the master.

## Status

🚧 **Phase 0 — skeleton & infra.** See the full design and phased roadmap in
[`docs/superpowers/specs/2026-06-29-job-hunt-agent-design.md`](docs/superpowers/specs/2026-06-29-job-hunt-agent-design.md).

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js + React + TypeScript (`apps/web`) → Vercel |
| Backend | Python + FastAPI + Agno agent team (`apps/api`) |
| LLMs | Google Gemini Flash (free tier) |
| Database + storage | Supabase (Postgres + Storage) |
| Queue | BullMQ (Python `bullmq`) on Redis / Upstash |
| LaTeX compile | Separate TeX Live + latexmk compile API (`services/compile`) |
| Scraping | Playwright + ATS APIs (Greenhouse / Lever / Ashby) |
| Containers | Docker + docker-compose |

## Repository layout

```
apps/
  web/        Next.js dashboard
  api/        FastAPI backend + Agno agent pipeline
services/
  compile/    TeX Live + latexmk LaTeX-compile microservice (POST /compile -> PDF)
supabase/
  migrations/ SQL schema migrations
docs/         design specs
docker-compose.yml   local dev: api + compile + postgres + redis
```

## Local development

```bash
cp .env.example .env   # fill in values
docker compose up --build
```

- API: http://localhost:8000  (health: `/health`)
- Compile service: http://localhost:8001 (health: `/health`)
- Web: http://localhost:3000

See per-package READMEs under `apps/` and `services/` for details.
