"""videoflow CLI — composable video workflow pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _out(data: dict, human: bool) -> None:
    if human:
        for k, v in data.items():
            print(f"{k}: {v}")
    else:
        print(json.dumps(data, indent=2))


def _err(message: str, human: bool) -> None:
    if human:
        print(f"error: {message}", file=sys.stderr)
    else:
        print(json.dumps({"error": message}), file=sys.stderr)


# ---------------------------------------------------------------------------
# detect-scenes
# ---------------------------------------------------------------------------

def cmd_detect_scenes(args: argparse.Namespace) -> int:
    from videoflow.analysis import SceneError, detect_scenes

    try:
        scenes = detect_scenes(
            args.input,
            threshold=args.threshold,
            detector=args.detector,
        )
    except FileNotFoundError as exc:
        _err(str(exc), args.human)
        return 1
    except ValueError as exc:
        _err(str(exc), args.human)
        return 1
    except SceneError as exc:
        _err(str(exc), args.human)
        return 1

    data = {
        "input": str(args.input),
        "scene_count": len(scenes),
        "scenes": [
            {
                "index": s.index,
                "start_ms": s.start_ms,
                "end_ms": s.end_ms,
                "duration_ms": s.duration_ms,
            }
            for s in scenes
        ],
    }

    if args.human:
        print(f"input:       {args.input}")
        print(f"scene_count: {len(scenes)}")
        for s in scenes:
            print(
                f"  scene {s.index:>3}: "
                f"{s.start_ms / 1000:.2f}s — {s.end_ms / 1000:.2f}s "
                f"({s.duration_ms / 1000:.2f}s)"
            )
    else:
        print(json.dumps(data, indent=2))

    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="videoflow",
        description="Composable video workflow pipeline.",
    )
    parser.add_argument(
        "--human", action="store_true", help="Human-readable output instead of JSON."
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # detect-scenes
    p_scenes = sub.add_parser(
        "detect-scenes",
        help="Detect scene boundaries in a video file.",
    )
    p_scenes.add_argument("input", type=Path, help="Input video file.")
    p_scenes.add_argument(
        "--threshold",
        type=float,
        default=27.0,
        help="Detection sensitivity. Lower = more scenes. Default: 27.0.",
    )
    p_scenes.add_argument(
        "--detector",
        choices=["content", "threshold"],
        default="content",
        help="content (frame-difference cuts) or threshold (fade-to-black). Default: content.",
    )
    p_scenes.set_defaults(func=cmd_detect_scenes)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))
