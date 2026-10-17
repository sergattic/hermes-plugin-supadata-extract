"""Supadata web scrape — https://docs.supadata.ai/web/scrape. GET /v1/web/scrape?url=...
returns {"url", "content" (Markdown), "name", "description", "urls"}; 1 credit per request.

Errors use {"error": code, "message", "details"} (https://docs.supadata.ai/errors): 401
unauthorized; 402 upgrade-required; 404 not-found; 429 limit-exceeded is EITHER the monthly plan
limit ("Plan usage limit was exceeded") OR a per-second rate limit ("...rate limit..."), told
apart by `details`; 5xx internal-error. Quota errors are phrased "quota exceeded" so
resilient-search marks the rung exhausted for the month; rate limits are not.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

import httpx

from agent.web_search_provider import WebSearchProvider, get_provider_env

URL = "https://api.supadata.ai/v1/web/scrape"
TIMEOUT = 90


def _neutral(text: str) -> str:
    # resilient-search parks a rung for the month on a bare "402"/"429"; only real quota errors may carry them
    return re.sub(r"\b(402|429)\b", "4xx", text)


def classify_error(status: int, body: Any, text: str) -> str:
    b = body if isinstance(body, dict) else {}
    code = str(b.get("error", ""))
    details = " ".join(str(b.get(k, "")) for k in ("message", "details")).strip() or text[:160]
    if status == 401 or code == "unauthorized":
        return f"auth failed: {details}"[:200]
    if status == 402 or code == "upgrade-required":
        return f"auth failed (feature not on plan): {details}"[:200]
    if status == 429 or code == "limit-exceeded":
        if "rate limit" in details.lower():
            return "rate limited, retry later"
        return f"quota exceeded: {details}"[:200]
    if status == 404 or code == "not-found":
        return _neutral(f"page not found or not reachable: {details}"[:200])
    if status >= 500:
        return _neutral(f"Supadata server error {status}: {details}"[:200])
    return _neutral(f"HTTP {status}: {details}"[:200])


class SupadataExtractProvider(WebSearchProvider):
    http = httpx

    @property
    def name(self) -> str:
        return "supadata"

    @property
    def display_name(self) -> str:
        return "Supadata web scrape (1 credit/page, 100/month shared with transcripts)"

    def is_available(self) -> bool:
        return bool(get_provider_env("SUPADATA_API_KEY"))

    def supports_search(self) -> bool:
        return False

    def supports_extract(self) -> bool:
        return True

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        return {"success": False, "error": "supadata is extract-only in this deployment"}

    def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        key = get_provider_env("SUPADATA_API_KEY")
        if not key:
            return [{"url": u, "title": "", "content": "", "error": "SUPADATA_API_KEY is not set"} for u in urls]
        out = []
        for url in urls:
            try:
                r = self.http.get(URL, params={"url": url}, headers={"x-api-key": key}, timeout=TIMEOUT)
            except httpx.TimeoutException:
                out.append({"url": url, "title": "", "content": "", "error": "timeout"})
                continue
            except httpx.RequestError as exc:
                out.append({"url": url, "title": "", "content": "", "error": f"connection error: {exc}"})
                continue
            try:
                body = r.json()
            except ValueError:
                body = None
            if r.status_code != 200:
                err = classify_error(r.status_code, body, (r.text or "").replace(key, "***"))
                out.append({"url": url, "title": "", "content": "", "error": err})
                continue
            content = (body or {}).get("content") or ""
            if not content.strip():
                out.append({"url": url, "title": "", "content": "", "error": "empty content"})
                continue
            out.append({"url": body.get("url") or url, "title": body.get("name") or "", "content": content,
                        "raw_content": content, "metadata": {"description": body.get("description") or ""}})
        return out
