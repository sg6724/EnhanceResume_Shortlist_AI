FROM debian:bookworm-slim

# Minimal TeX Live via apt (Debian mirrors) instead of the ~7GB texlive/texlive
# scheme-full image (whose own installer pulls from slow CTAN mirrors). Covers
# article/moderncv-style resumes: geometry, enumitem, titlesec, hyperref, xcolor.
# If a specific resume template needs a package outside this set, the compile
# error log will name it — add it here.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        texlive-latex-base \
        texlive-latex-recommended \
        texlive-latex-extra \
        texlive-fonts-recommended \
        latexmk \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml .
RUN uv sync --no-dev

COPY main.py .

EXPOSE 8001
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
