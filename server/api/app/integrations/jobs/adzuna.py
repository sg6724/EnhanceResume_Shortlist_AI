from __future__ import annotations

import httpx

from ...domain.models import RawJd


class AdzunaSource:
    """Adzuna API job source (developer.adzuna.com). Returns [] when
    credentials are unset — Adzuna is an optional source."""

    def __init__(self, http: httpx.AsyncClient, app_id: str, api_key: str):
        self._http = http
        self._app_id = app_id
        self._api_key = api_key

    async def fetch(self, keywords: list[str]) -> list[RawJd]:
        if not self._app_id or not self._api_key:
            return []
        results: list[RawJd] = []
        for kw in keywords[:3]:
            try:
                resp = await self._http.get(
                    "https://api.adzuna.com/v1/api/jobs/in/search/1",
                    params={
                        "app_id": self._app_id,
                        "app_key": self._api_key,
                        "results_per_page": 20,
                        "what": kw,
                        "content-type": "application/json",
                    },
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for job in data.get("results", []):
                        results.append(RawJd(
                            source="adzuna",
                            company=job.get("company", {}).get("display_name", "Unknown"),
                            title=job.get("title", kw),
                            location=job.get("location", {}).get("display_name", ""),
                            url=job.get("redirect_url", ""),
                            raw_text=(
                                f"{job.get('title', '')} at "
                                f"{job.get('company', {}).get('display_name', '')}\n\n"
                                f"{job.get('description', '')}"
                            ),
                        ))
            except Exception:
                continue
        return results
