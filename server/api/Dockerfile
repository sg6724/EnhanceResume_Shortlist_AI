FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_HTTP_TIMEOUT=120

COPY pyproject.toml .
RUN uv sync --no-dev

COPY app ./app

EXPOSE 8000
CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
