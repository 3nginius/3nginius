"""Keyframe extraction via ffmpeg.

Strategy:
  1. Try scene-change detection (`select='gt(scene,THRESH)'`).
  2. If too few frames, fall back to N evenly-spaced frames.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Frame:
    path: Path
    timestamp: float  # seconds; -1 if unknown


class FrameError(RuntimeError):
    pass


def extract_frames(
    video: Path,
    out_dir: Path,
    max_frames: int = 8,
    scene_threshold: float = 0.30,
) -> List[Frame]:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise FrameError("ffmpeg/ffprobe not found on PATH")

    out_dir.mkdir(parents=True, exist_ok=True)
    duration = _probe_duration(video)

    # Scene-detection pass.
    scene_dir = out_dir / "scene"
    scene_dir.mkdir(exist_ok=True)
    _ffmpeg_scene(video, scene_dir, scene_threshold)
    frames = sorted(scene_dir.glob("frame_*.jpg"))

    if len(frames) >= 2:
        # Cap at max_frames by uniform subsampling.
        frames = _subsample(frames, max_frames)
        return [Frame(path=p, timestamp=-1.0) for p in frames]

    # Fallback: evenly spaced frames.
    interval_dir = out_dir / "interval"
    interval_dir.mkdir(exist_ok=True)
    return _ffmpeg_interval(video, interval_dir, max_frames, duration)


def _probe_duration(video: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", str(video),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FrameError(f"ffprobe failed: {proc.stderr.strip()}")
    try:
        return float(json.loads(proc.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return 0.0


def _ffmpeg_scene(video: Path, out_dir: Path, threshold: float) -> None:
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video),
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr",
        "-q:v", "2",
        str(out_dir / "frame_%04d.jpg"),
    ]
    subprocess.run(cmd, capture_output=True, text=True)


def _ffmpeg_interval(video: Path, out_dir: Path, n: int, duration: float) -> List[Frame]:
    if n < 1:
        return []
    if duration <= 0:
        # Single mid-point grab.
        ts = [0.0]
    else:
        # Evenly spaced timestamps, avoiding the first/last 5%.
        margin = max(0.05 * duration, 0.1)
        usable = max(duration - 2 * margin, 0.1)
        ts = [margin + i * usable / max(n - 1, 1) for i in range(n)]

    out: List[Frame] = []
    for i, t in enumerate(ts):
        path = out_dir / f"frame_{i:04d}.jpg"
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{t:.3f}", "-i", str(video),
            "-frames:v", "1", "-q:v", "2",
            str(path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0 and path.exists():
            out.append(Frame(path=path, timestamp=t))
    return out


def _subsample(items, n):
    if len(items) <= n:
        return items
    step = len(items) / n
    return [items[int(i * step)] for i in range(n)]
