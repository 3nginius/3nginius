"""Yandex reverse image search.

Two-step flow:
  1. Upload image to Yandex's CBIR (content-based image retrieval) endpoint;
     it returns a temporary image URL + cbir_id.
  2. Construct a results URL the user can open. We also attempt to fetch and
     parse the results page; Yandex frequently rate-limits headless requests,
     so on failure we still return the openable search_url.

No API key required. Fragile by design — meant as a free fallback.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List
from urllib.parse import quote

import requests

from revsearch.providers.base import Provider, SearchHit, SearchResult


YANDEX_SEARCH = "https://yandex.com/images/search"
YANDEX_REQUEST_BLOB = '{"blocks":[{"block":"b-page_type_search-by-image__link"}]}'

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class YandexProvider(Provider):
    name = "yandex"

    def is_available(self) -> bool:
        return True  # no key needed

    def search(self, image_path: Path) -> SearchResult:
        result = SearchResult(provider=self.name, query_image=image_path)
        try:
            cbir_url, cbir_id = self._upload(image_path)
        except Exception as exc:
            result.error = f"upload failed: {exc}"
            return result

        search_url = (
            f"{YANDEX_SEARCH}?rpt=imageview&url={quote(cbir_url)}"
            + (f"&cbir_id={quote(cbir_id)}" if cbir_id else "")
        )
        result.search_url = search_url

        try:
            result.hits = self._scrape(search_url)
        except Exception as exc:
            # Keep the openable URL even if scraping is blocked.
            result.error = f"scrape failed: {exc}"
        return result

    def _upload(self, image_path: Path):
        params = {
            "rpt": "imageview",
            "format": "json",
            "request": YANDEX_REQUEST_BLOB,
        }
        with open(image_path, "rb") as fh:
            files = {"upfile": (image_path.name, fh, "image/jpeg")}
            resp = requests.post(
                YANDEX_SEARCH,
                params=params,
                files=files,
                headers={"User-Agent": UA},
                timeout=30,
            )
        resp.raise_for_status()
        data = resp.json()
        try:
            block_params = data["blocks"][0]["params"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError(f"unexpected upload response shape: {str(data)[:300]}")
        url = block_params.get("originalImageUrl") or block_params.get("url") or ""
        if not url:
            raise RuntimeError(f"no image url in response: {block_params!r}")
        if url.startswith("//"):
            url = "https:" + url
        return url, block_params.get("cbirId", "")

    def _scrape(self, search_url: str) -> List[SearchHit]:
        resp = requests.get(
            search_url,
            headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
            timeout=30,
        )
        resp.raise_for_status()
        return _parse_yandex_results(resp.text)


_LINK_RE = re.compile(r'"url":"(https?://[^"]+)"')
_TITLE_RE = re.compile(r'"title":"([^"]+)"')


def _parse_yandex_results(html: str) -> List[SearchHit]:
    """Best-effort parse. Yandex embeds JSON-ish blobs in the page; pull plausible
    site URLs and dedupe by domain."""
    hits: List[SearchHit] = []
    seen = set()
    for m in _LINK_RE.finditer(html):
        url = m.group(1).encode("utf-8").decode("unicode_escape")
        if any(s in url for s in ("yandex.", "yastatic.", "ya.ru")):
            continue
        domain = url.split("/")[2] if "://" in url and "/" in url[8:] else url
        if domain in seen:
            continue
        seen.add(domain)
        hits.append(SearchHit(url=url, source_domain=domain))
        if len(hits) >= 25:
            break
    return hits
