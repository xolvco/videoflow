"""Scene detection and video analysis functions."""

from __future__ import annotations

import dataclasses
from pathlib import Path

# Optional dependency — imported at module level so tests can patch it.
try:
    from scenedetect import detect, ContentDetector, ThresholdDetector  # type: ignore[import]

    _SCENEDETECT_AVAILABLE = True
except ImportError:
    detect = None  # type: ignore[assignment]
    ContentDetector = None  # type: ignore[assignment]
    ThresholdDetector = None  # type: ignore[assignment]
    _SCENEDETECT_AVAILABLE = False


class SceneError(RuntimeError):
    """Raised when scene detection fails."""


@dataclasses.dataclass
class Scene:
    """A detected scene boundary."""

    index: int
    """1-based scene number."""

    start_ms: int
    """Scene start time in milliseconds."""

    end_ms: int
    """Scene end time in milliseconds."""

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


_DETECTORS = ("content", "threshold")


def detect_scenes(
    input: str | Path,
    *,
    threshold: float = 27.0,
    detector: str = "content",
) -> list[Scene]:
    """Detect scene boundaries in a video file.

    Wraps PySceneDetect. Returns Scene objects with start/end timestamps in
    milliseconds. Install PySceneDetect with: ``pip install scenedetect[opencv]``

    Args:
        input: Path to the video file.
        threshold: Detection sensitivity. Lower = more scenes detected.
            Default 27.0 works well for live-action with ContentDetector.
            For ThresholdDetector, this is the brightness level (0–255).
        detector: ``"content"`` (frame-difference, good for cuts) or
            ``"threshold"`` (brightness level, good for fades to black).

    Returns:
        List of :class:`Scene` objects ordered by start time.

    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError: If *detector* is not ``"content"`` or ``"threshold"``.
        SceneError: If PySceneDetect is not installed or detection fails.
    """
    input = Path(input)
    if not input.exists():
        raise FileNotFoundError(f"Input file not found: {input}")

    if detector not in _DETECTORS:
        raise ValueError(
            f"detector must be one of {_DETECTORS!r}, got {detector!r}"
        )

    if detect is None:
        raise SceneError(
            "PySceneDetect is required for scene detection. "
            "Install it with: pip install scenedetect[opencv]"
        )

    try:
        if detector == "content":
            det = ContentDetector(threshold=threshold)
        else:
            det = ThresholdDetector(threshold=threshold)

        raw = detect(str(input), det)
    except Exception as exc:
        raise SceneError(f"Scene detection failed: {exc}") from exc

    return [
        Scene(
            index=i,
            start_ms=round(start_tc.get_seconds() * 1000),
            end_ms=round(end_tc.get_seconds() * 1000),
        )
        for i, (start_tc, end_tc) in enumerate(raw, start=1)
    ]
