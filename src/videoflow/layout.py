"""Multi-panel canvas layout — compose multiple video streams onto one wide canvas."""

from __future__ import annotations

import dataclasses
import subprocess
import tempfile
from pathlib import Path

from videoflow.audio import AudioBeatMap


class LayoutError(RuntimeError):
    """Raised when canvas layout or rendering fails."""


_POSITIONS = ("outer_left", "inner_left", "inner_right", "outer_right")
_CROPS = ("full", "smart")


@dataclasses.dataclass
class Panel:
    """One panel in a multi-panel canvas.

    Args:
        input:    Source video file.
        speed:    Playback speed multiplier (2.0 = fast-forward, 0.5 = slow-mo).
        position: Panel position — ``"outer_left"``, ``"inner_left"``,
                  ``"inner_right"``, or ``"outer_right"``.
        crop:     ``"full"`` scales the source to fill the panel.
                  ``"smart"`` center-crops to 60% before scaling, giving a
                  zoomed-in view of the most active region (V1: centre;
                  V2: energy-histogram guided).
    """

    input: str | Path
    speed: float = 1.0
    position: str = "outer_left"
    crop: str = "full"

    def __post_init__(self) -> None:
        if self.position not in _POSITIONS:
            raise ValueError(
                f"position must be one of {list(_POSITIONS)!r}, got {self.position!r}"
            )
        if self.crop not in _CROPS:
            raise ValueError(
                f"crop must be one of {list(_CROPS)!r}, got {self.crop!r}"
            )
        if self.speed <= 0:
            raise ValueError(f"speed must be positive, got {self.speed}")


@dataclasses.dataclass
class FinaleClip:
    """A full-width clip pinned to the end of the canvas render."""

    input: str | Path
    beats: int = 8
    """Number of beats to hold the finale (requires beat_map to be set)."""

    mode: str = "full_width"
    """``"full_width"`` scales the clip to the entire canvas width."""


class MultiPanelCanvas:
    """Compose multiple video streams onto a single wide canvas.

    Standard layout: four panels side by side on a 4860×2160 canvas
    (four 9:16 portrait streams — wider than 4K).

    The two outer panels show the full frame at their respective speeds.
    The two inner panels show a zoomed crop of the adjacent outer source
    (``crop="smart"``), giving the eye detail while the outer panels
    provide context.

    The panel sizes are the edit language — ``crop="smart"`` on the inner
    panels creates a visual tension between the wide view and the close-up
    that plays on the beat.

    Example (DC Metro)::

        canvas = MultiPanelCanvas(
            panels=[
                Panel("tunnel.mp4",   speed=2.0, position="outer_left",  crop="full"),
                Panel("tunnel.mp4",   speed=2.0, position="inner_left",  crop="smart"),
                Panel("platform.mp4", speed=0.5, position="inner_right", crop="smart"),
                Panel("platform.mp4", speed=0.5, position="outer_right", crop="full"),
            ],
            canvas_size=(4860, 2160),
        )
        canvas.set_finale("capitol.mp4", beats=8)
        canvas.render("dc_metro.mp4")
    """

    def __init__(
        self,
        panels: list[Panel],
        *,
        canvas_size: tuple[int, int] = (4860, 2160),
        beat_map: AudioBeatMap | None = None,
    ) -> None:
        if not panels:
            raise ValueError("panels must not be empty")
        self.panels = panels
        self.canvas_size = canvas_size
        self.beat_map = beat_map  # reserved — used in V2 for beat-sync transitions
        self._finale: FinaleClip | None = None

    def set_finale(
        self,
        clip: str | Path,
        *,
        beats: int = 8,
        mode: str = "full_width",
    ) -> None:
        """Pin a full-width clip to the end of the render.

        The clip expands across the entire canvas — all four panel positions
        become one image. This is the reveal moment: the Capitol, the product,
        the CTA. Everything before it was panels; this is the payoff.

        Args:
            clip:  Path to the finale video file.
            beats: Number of beats to hold (requires ``beat_map`` to be set).
            mode:  Currently only ``"full_width"`` is supported.
        """
        if mode != "full_width":
            raise ValueError(f"mode must be 'full_width', got {mode!r}")
        self._finale = FinaleClip(input=Path(clip), beats=beats, mode=mode)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(
        self,
        output: str | Path,
        *,
        crf: int = 18,
        preset: str = "fast",
        timeout: float = 3600.0,
    ) -> Path:
        """Render the multi-panel canvas to *output*.

        Builds an FFmpeg ``filter_complex`` that:

        1. Applies per-panel speed (``setpts``) and crop.
        2. Scales each panel to its column width × canvas height.
        3. Stacks all panels horizontally (``hstack``).
        4. If a finale is set, appends it full-width via ``concat``.

        Args:
            output:  Destination video file.
            crf:     H.264 quality (lower = better, default 18).
            preset:  ffmpeg encoding preset (default ``"fast"``).
            timeout: ffmpeg timeout in seconds (default 3600).

        Returns:
            Path to the rendered output file.

        Raises:
            FileNotFoundError: If any panel input file does not exist.
            LayoutError: If ffmpeg is not on PATH, returns an error, or times out.
        """
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)

        for panel in self.panels:
            p = Path(panel.input)
            if not p.exists():
                raise FileNotFoundError(f"Panel input not found: {p}")

        if self._finale is not None:
            fp = Path(self._finale.input)
            if not fp.exists():
                raise FileNotFoundError(f"Finale input not found: {fp}")

        cmd = self._build_command(output, crf=crf, preset=preset)

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
        except FileNotFoundError:
            raise LayoutError(
                "ffmpeg not found — install ffmpeg and ensure it is on PATH"
            )
        except subprocess.TimeoutExpired:
            raise LayoutError(f"ffmpeg timed out after {timeout}s")

        if result.returncode != 0:
            raise LayoutError(f"ffmpeg error: {result.stderr[-500:]}")

        return output

    # ------------------------------------------------------------------
    # Internal — command and filter_complex construction
    # ------------------------------------------------------------------

    def _panel_width(self) -> int:
        """Width of each panel column in pixels."""
        return self.canvas_size[0] // len(self.panels)

    def _panel_filter(self, stream_idx: int, panel: Panel) -> tuple[str, str]:
        """Return ``(filter_chain, out_label)`` for one panel stream.

        The filter chain:
        - ``setpts`` to apply speed
        - optional center crop to 60% for ``smart`` mode
        - ``scale`` to panel_w × canvas_height
        """
        w = self._panel_width()
        h = self.canvas_size[1]
        pts = f"setpts={1.0 / panel.speed:.6f}*PTS"

        if panel.crop == "smart":
            # Center crop to 60% of the frame before scaling — zoomed-in view.
            # V2: replace with energy-histogram guided crop position.
            crop = "crop=iw*6/10:ih*6/10,"
        else:
            crop = ""

        label = f"p{stream_idx}"
        chain = f"[{stream_idx}:v]{pts},{crop}scale={w}:{h}[{label}]"
        return chain, label

    def _build_filter_complex(self) -> str:
        """Build the full FFmpeg filter_complex string."""
        parts: list[str] = []
        panel_labels: list[str] = []

        for i, panel in enumerate(self.panels):
            chain, label = self._panel_filter(i, panel)
            parts.append(chain)
            panel_labels.append(f"[{label}]")

        n = len(self.panels)
        hstack_inputs = "".join(panel_labels)

        if self._finale is not None:
            # hstack panels → [panels]; scale finale → [fin]; concat both
            finale_idx = n
            w, h = self.canvas_size
            parts.append(
                f"{hstack_inputs}hstack=inputs={n}[panels]"
            )
            parts.append(
                f"[{finale_idx}:v]scale={w}:{h}[fin]"
            )
            parts.append(
                "[panels][fin]concat=n=2:v=1:a=0[out]"
            )
        else:
            parts.append(f"{hstack_inputs}hstack=inputs={n}[out]")

        return ";".join(parts)

    def _build_command(
        self, output: Path, *, crf: int, preset: str
    ) -> list[str]:
        """Assemble the full ffmpeg command list."""
        cmd = ["ffmpeg", "-y"]

        # One -i per panel (files may repeat — FFmpeg handles this fine)
        for panel in self.panels:
            cmd += ["-i", str(Path(panel.input))]

        # Finale input (if set)
        if self._finale is not None:
            cmd += ["-i", str(Path(self._finale.input))]

        cmd += [
            "-filter_complex", self._build_filter_complex(),
            "-map", "[out]",
            "-c:v", "libx264",
            "-crf", str(crf),
            "-preset", preset,
            "-an",          # panels are silent by default — add audio mix in V2
            str(output),
        ]

        return cmd
