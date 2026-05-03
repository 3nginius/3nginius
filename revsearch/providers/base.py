"""Provider interface for reverse-image search backends."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class SearchHit:
    url: str
    title: str = ""
    source_domain: str = ""
    thumbnail: Optional[str] = None
    score: Optional[float] = None  # provider-specific


@dataclass
class SearchResult:
    provider: str
    query_image: Path
    hits: List[SearchHit] = field(default_factory=list)
    search_url: Optional[str] = None  # human-openable fallback URL
    error: Optional[str] = None


class Provider:
    name: str = "base"

    def is_available(self) -> bool:
        """Return True if this provider has the credentials/network it needs."""
        return False

    def search(self, image_path: Path) -> SearchResult:
        raise NotImplementedError
