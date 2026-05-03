"""Perceptual hashing + near-duplicate dedup for frames."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import imagehash
from PIL import Image


@dataclass
class HashedFrame:
    path: Path
    phash: imagehash.ImageHash

    def hex(self) -> str:
        return str(self.phash)


def hash_frames(paths: List[Path]) -> List[HashedFrame]:
    out: List[HashedFrame] = []
    for p in paths:
        try:
            with Image.open(p) as im:
                out.append(HashedFrame(path=p, phash=imagehash.phash(im)))
        except Exception:
            continue
    return out


def dedupe(frames: List[HashedFrame], hamming_threshold: int = 6) -> List[HashedFrame]:
    """Drop near-duplicates within `hamming_threshold` bits of an already-kept frame."""
    kept: List[HashedFrame] = []
    for f in frames:
        if all((f.phash - k.phash) > hamming_threshold for k in kept):
            kept.append(f)
    return kept
