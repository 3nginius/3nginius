"""TinEye Commercial API provider.

Requires env vars:
  TINEYE_API_KEY (HTTP basic password; username is "api")
  TINEYE_API_URL (defaults to https://api.tineye.com/rest/search/)

Docs: https://services.tineye.com/developers/tineyeapi/
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

import requests

from revsearch.providers.base import Provider, SearchHit, SearchResult


class TinEyeProvider(Provider):
    name = "tineye"

    def __init__(self) -> None:
        self.api_key = os.environ.get("TINEYE_API_KEY", "")
        self.endpoint = os.environ.get(
            "TINEYE_API_URL", "https://api.tineye.com/rest/search/"
        )

    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(self, image_path: Path) -> SearchResult:
        result = SearchResult(provider=self.name, query_image=image_path)
        if not self.is_available():
            result.error = "TINEYE_API_KEY not set"
            return result
        try:
            with open(image_path, "rb") as fh:
                resp = requests.post(
                    self.endpoint,
                    files={"image_upload": (image_path.name, fh, "image/jpeg")},
                    auth=("api", self.api_key),
                    timeout=60,
                )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            result.error = f"request failed: {exc}"
            return result

        for match in (data.get("results", {}).get("matches") or [])[:25]:
            for backlink in match.get("backlinks", [])[:1]:
                result.hits.append(
                    SearchHit(
                        url=backlink.get("backlink") or backlink.get("url", ""),
                        source_domain=match.get("domain", ""),
                        score=match.get("score"),
                        thumbnail=match.get("image_url"),
                    )
                )
        return result
