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
    from videoflow.analysis import DETECTOR_INFO, SceneError, detect_scenes

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

    info = DETECTOR_INFO[args.detector]
    t = args.threshold if args.threshold is not None else info.threshold_default

    data = {
        "input": str(args.input),
        "detector": args.detector,
        "threshold": t,
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
        print(f"detector:    {args.detector} — {info.name}")
        print(f"threshold:   {t}")
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


def cmd_detectors(args: argparse.Namespace) -> int:
    """List available detectors with guidance."""
    from videoflow.analysis import DETECTOR_INFO

    if args.human:
        for key, info in DETECTOR_INFO.items():
            print(f"\n{key}  —  {info.name}")
            print(f"  {info.description}")
            print(f"  Threshold ({info.threshold_label}): "
                  f"{info.threshold_min} – {info.threshold_max}, "
                  f"default {info.threshold_default}")
            print(f"  Lower:   {info.threshold_low_note}")
            print(f"  Higher:  {info.threshold_high_note}")
            print(f"  Tip:     {info.novice_tip}")
            print(f"  Best for:    {', '.join(info.best_for)}")
            print(f"  Not great for: {', '.join(info.not_great_for)}")
    else:
        data = {
            key: {
                "name": info.name,
                "description": info.description,
                "threshold_label": info.threshold_label,
                "threshold_default": info.threshold_default,
                "threshold_min": info.threshold_min,
                "threshold_max": info.threshold_max,
                "threshold_low_note": info.threshold_low_note,
                "threshold_high_note": info.threshold_high_note,
                "best_for": info.best_for,
                "not_great_for": info.not_great_for,
                "novice_tip": info.novice_tip,
            }
            for key, info in DETECTOR_INFO.items()
        }
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
        default=None,
        help=(
            "Detection sensitivity. Uses the detector's default if not set. "
            "adaptive default: 3.0 (scale 1–10). "
            "content default: 27.0 (scale 5–100). "
            "threshold default: 12.0 (brightness 1–255). "
            "Lower = more scenes. Run 'videoflow detectors' for full guidance."
        ),
    )
    p_scenes.add_argument(
        "--detector",
        choices=["adaptive", "content", "threshold"],
        default="adaptive",
        help=(
            "adaptive (default, handles mixed content), "
            "content (hard cuts), "
            "threshold (fade-to-black). "
            "Run 'videoflow detectors --human' for details."
        ),
    )
    p_scenes.set_defaults(func=cmd_detect_scenes)

    # detectors — list available detectors with guidance
    p_det = sub.add_parser(
        "detectors",
        help="List available detectors with threshold guidance.",
    )
    p_det.set_defaults(func=cmd_detectors)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))
