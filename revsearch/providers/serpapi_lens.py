"""Google Lens via SerpAPI.

Requires env var:
  SERPAPI_API_KEY

SerpAPI's Google Lens engine accepts an `url=` parameter, so we first need a
publicly accessible image URL. We try in order:
  1. REVSEARCH_PUBLIC_BASE_URL (user-provided base; we just append the filename)
  2. 0x0.st (anonymous file host)

If neither is reachable, the provider returns an error with guidance.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import requests

from revsearch.providers.base import Provider, SearchHit, SearchResult


class SerpAPIGoogleLensProvider(Provider):
    name = "google_lens_serpapi"

    def __init__(self) -> None:
        self.api_key = os.environ.get("SERPAPI_API_KEY", "")
        self.public_base = os.environ.get("REVSEARCH_PUBLIC_BASE_URL", "").rstrip("/")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(self, image_path: Path) -> SearchResult:
        result = SearchResult(provider=self.name, query_image=image_path)
        if not self.is_available():
            result.error = "SERPAPI_API_KEY not set"
            return result

        public_url = self._publicize(image_path)
        if not public_url:
            result.error = (
                "no public URL for image; set REVSEARCH_PUBLIC_BASE_URL "
                "or ensure 0x0.st is reachable"
            )
            return result

        try:
            resp = requests.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google_lens",
                    "url": public_url,
                    "api_key": self.api_key,
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            result.error = f"request failed: {exc}"
            return result

        for m in (data.get("visual_matches") or [])[:25]:
            result.hits.append(
                SearchHit(
                    url=m.get("link", ""),
                    title=m.get("title", ""),
                    source_domain=m.get("source", ""),
                    thumbnail=m.get("thumbnail"),
                )
            )
        result.search_url = data.get("search_metadata", {}).get("google_lens_url")
        return result

    def _publicize(self, image_path: Path) -> Optional[str]:
        if self.public_base:
            return f"{self.public_base}/{image_path.name}"
        try:
            with open(image_path, "rb") as fh:
                resp = requests.post(
                    "https://0x0.st",
                    files={"file": (image_path.name, fh, "image/jpeg")},
                    headers={"User-Agent": "revsearch/0.1"},
                    timeout=30,
                )
            if resp.ok and resp.text.strip().startswith("http"):
                return resp.text.strip()
        except Exception:
            return None
        return None
