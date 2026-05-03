"""Bing Visual Search via Azure Cognitive Services.

Requires env var:
  BING_VISUAL_SEARCH_KEY

Optional:
  BING_VISUAL_SEARCH_ENDPOINT
    (defaults to https://api.bing.microsoft.com/v7.0/images/visualsearch)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests

from revsearch.providers.base import Provider, SearchHit, SearchResult


class BingVisualProvider(Provider):
    name = "bing_visual"

    def __init__(self) -> None:
        self.api_key = os.environ.get("BING_VISUAL_SEARCH_KEY", "")
        self.endpoint = os.environ.get(
            "BING_VISUAL_SEARCH_ENDPOINT",
            "https://api.bing.microsoft.com/v7.0/images/visualsearch",
        )

    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(self, image_path: Path) -> SearchResult:
        result = SearchResult(provider=self.name, query_image=image_path)
        if not self.is_available():
            result.error = "BING_VISUAL_SEARCH_KEY not set"
            return result
        try:
            with open(image_path, "rb") as fh:
                resp = requests.post(
                    self.endpoint,
                    headers={"Ocp-Apim-Subscription-Key": self.api_key},
                    files={"image": (image_path.name, fh, "image/jpeg")},
                    timeout=60,
                )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            result.error = f"request failed: {exc}"
            return result

        for tag in data.get("tags", []):
            for action in tag.get("actions", []):
                if action.get("actionType") == "PagesIncluding":
                    for page in action.get("data", {}).get("value", [])[:25]:
                        result.hits.append(
                            SearchHit(
                                url=page.get("hostPageUrl", ""),
                                title=page.get("name", ""),
                                source_domain=page.get("hostPageDisplayUrl", ""),
                                thumbnail=page.get("thumbnailUrl"),
                            )
                        )
                    break
            if result.hits:
                break
        return result
