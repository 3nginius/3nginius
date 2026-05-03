"""Video/image acquisition. Wraps yt-dlp for URLs; passes through local paths."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}


@dataclass
class Media:
    path: Path
    kind: str  # "image" or "video"
    source: str  # original URL or local path


class DownloadError(RuntimeError):
    pass


def acquire(source: str, out_dir: Path, video_index: int = 1) -> Media:
    """Resolve `source` (URL or local path) to a local Media file in `out_dir`.

    For tweets / posts with multiple videos, `video_index` (1-based) selects which one.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    if _looks_local(source):
        path = Path(source).expanduser().resolve()
        if not path.exists():
            raise DownloadError(f"Local file not found: {path}")
        return Media(path=path, kind=_classify(path), source=source)

    return _download_with_ytdlp(source, out_dir, video_index)


def _looks_local(s: str) -> bool:
    return not s.startswith(("http://", "https://"))


def _classify(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    raise DownloadError(f"Unrecognised media extension: {ext}")


def _download_with_ytdlp(url: str, out_dir: Path, video_index: int) -> Media:
    if shutil.which("yt-dlp") is None:
        raise DownloadError("yt-dlp not found on PATH. Install with: pip install yt-dlp")

    template = str(out_dir / "%(id)s_%(playlist_index|0)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "--no-check-certificates",
        "--no-playlist",
        "--no-warnings",
        "--restrict-filenames",
        "-f", "best[ext=mp4]/best",
        "--playlist-items", str(video_index),
        "-o", template,
        "--print", "after_move:filepath",
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise DownloadError(f"yt-dlp failed: {proc.stderr.strip() or proc.stdout.strip()}")

    filepath = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    if not filepath or not Path(filepath).exists():
        # Fall back to scanning out_dir for the freshest file.
        candidates = sorted(out_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            raise DownloadError("yt-dlp reported success but no file was produced")
        filepath = str(candidates[0])

    path = Path(filepath)
    return Media(path=path, kind=_classify(path), source=url)
