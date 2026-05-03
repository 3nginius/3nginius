"""End-to-end pipeline: source -> media -> frames -> hashes -> reverse search."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

from revsearch.downloader import Media, acquire
from revsearch.frames import Frame, extract_frames
from revsearch.hashing import HashedFrame, dedupe, hash_frames
from revsearch.providers import all_providers
from revsearch.providers.base import Provider, SearchResult


log = logging.getLogger("revsearch")


@dataclass
class FrameReport:
    path: str
    phash: str
    results: List[SearchResult] = field(default_factory=list)


@dataclass
class PipelineReport:
    source: str
    media_path: str
    media_kind: str
    frames: List[FrameReport] = field(default_factory=list)


def run(
    source: str,
    work_dir: Path,
    *,
    video_index: int = 1,
    max_frames: int = 6,
    scene_threshold: float = 0.30,
    providers: Optional[Iterable[Provider]] = None,
) -> PipelineReport:
    work_dir = Path(work_dir).expanduser().resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    media = acquire(source, work_dir / "media", video_index=video_index)
    log.info("acquired %s (%s)", media.path, media.kind)

    if media.kind == "image":
        frame_paths = [media.path]
    else:
        frames: List[Frame] = extract_frames(
            media.path,
            work_dir / "frames",
            max_frames=max_frames,
            scene_threshold=scene_threshold,
        )
        frame_paths = [f.path for f in frames]
        log.info("extracted %d frames", len(frame_paths))

    hashed = dedupe(hash_frames(frame_paths))
    log.info("kept %d unique frames after dedup", len(hashed))

    chosen = list(providers) if providers is not None else _available(all_providers())
    if not chosen:
        log.warning("no providers available; results will be empty")

    report = PipelineReport(
        source=source,
        media_path=str(media.path),
        media_kind=media.kind,
    )
    for hf in hashed:
        fr = FrameReport(path=str(hf.path), phash=hf.hex())
        with ThreadPoolExecutor(max_workers=max(1, len(chosen))) as pool:
            fr.results = list(pool.map(lambda p, hf=hf: p.search(hf.path), chosen))
        report.frames.append(fr)
    return report


def _available(providers):
    return [p for p in providers if p.is_available()]


def report_to_dict(report: PipelineReport) -> dict:
    out = asdict(report)
    return out
