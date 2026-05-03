"""revsearch CLI."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from revsearch.pipeline import report_to_dict, run
from revsearch.providers import all_providers


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="revsearch",
        description="Reverse video/image search: download -> keyframes -> reverse-search providers.",
    )
    p.add_argument(
        "source", nargs="?",
        help="URL (any yt-dlp supported site) or local image/video path",
    )
    p.add_argument(
        "-o", "--workdir",
        default="./revsearch_out",
        help="Working directory for downloads and frames (default: ./revsearch_out)",
    )
    p.add_argument(
        "--video-index", type=int, default=1,
        help="1-based index when a post contains multiple videos (default: 1)",
    )
    p.add_argument(
        "--max-frames", type=int, default=6,
        help="Max keyframes per video to reverse-search (default: 6)",
    )
    p.add_argument(
        "--scene-threshold", type=float, default=0.30,
        help="ffmpeg scene-change sensitivity, lower = more frames (default: 0.30)",
    )
    p.add_argument(
        "--providers", nargs="+",
        choices=[p.name for p in all_providers()],
        help="Restrict to specific providers (default: all available)",
    )
    p.add_argument(
        "--format", choices=["json", "text"], default="text",
        help="Output format (default: text)",
    )
    p.add_argument(
        "-v", "--verbose", action="store_true",
        help="Verbose logging",
    )
    p.add_argument(
        "--list-providers", action="store_true",
        help="Print provider availability and exit",
    )
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.list_providers:
        for p in all_providers():
            status = "available" if p.is_available() else "missing-credentials"
            print(f"{p.name:24s} {status}")
        return 0

    if not args.source:
        build_parser().error("source is required (or use --list-providers)")

    selected = None
    if args.providers:
        wanted = set(args.providers)
        selected = [p for p in all_providers() if p.name in wanted]

    report = run(
        args.source,
        Path(args.workdir),
        video_index=args.video_index,
        max_frames=args.max_frames,
        scene_threshold=args.scene_threshold,
        providers=selected,
    )

    if args.format == "json":
        print(json.dumps(report_to_dict(report), indent=2, default=str))
    else:
        _print_text(report)
    return 0


def _print_text(report) -> None:
    print(f"Source: {report.source}")
    print(f"Media:  {report.media_path}  ({report.media_kind})")
    print(f"Frames analysed: {len(report.frames)}")
    print()
    for i, fr in enumerate(report.frames, 1):
        print(f"--- frame {i}  {fr.path}  pHash={fr.phash}")
        for res in fr.results:
            header = f"  [{res.provider}]"
            if res.error:
                print(f"{header} error: {res.error}")
            if res.search_url:
                print(f"{header} open: {res.search_url}")
            for hit in res.hits[:10]:
                title = f" - {hit.title}" if hit.title else ""
                print(f"{header} {hit.url}{title}")
            if not res.hits and not res.error and not res.search_url:
                print(f"{header} (no results)")
        print()


if __name__ == "__main__":
    sys.exit(main())
