"""Tests for videoflow.layout — MultiPanelCanvas and Panel."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from videoflow.layout import FinaleClip, LayoutError, MultiPanelCanvas, Panel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_run(returncode=0):
    r = MagicMock()
    r.returncode = returncode
    r.stderr = "err" if returncode != 0 else ""
    return r


def _four_panels():
    return [
        Panel("tunnel.mp4",   speed=2.0, position="outer_left",  crop="full"),
        Panel("tunnel.mp4",   speed=2.0, position="inner_left",  crop="smart"),
        Panel("platform.mp4", speed=0.5, position="inner_right", crop="smart"),
        Panel("platform.mp4", speed=0.5, position="outer_right", crop="full"),
    ]


def _canvas(panels=None, canvas_size=(4860, 2160)):
    return MultiPanelCanvas(panels or _four_panels(), canvas_size=canvas_size)


def _render(canvas, returncode=0, side_effect=None):
    run_kw = (
        {"side_effect": side_effect}
        if side_effect
        else {"return_value": _mock_run(returncode=returncode)}
    )
    with patch("videoflow.layout.subprocess.run", **run_kw), \
         patch.object(Path, "exists", return_value=True), \
         patch.object(Path, "mkdir"):
        return canvas.render("output.mp4")


# ---------------------------------------------------------------------------
# Panel validation
# ---------------------------------------------------------------------------

class TestPanel(unittest.TestCase):

    def test_valid_panel(self):
        p = Panel("clip.mp4", speed=2.0, position="outer_left", crop="full")
        self.assertEqual(p.position, "outer_left")

    def test_invalid_position(self):
        with self.assertRaises(ValueError):
            Panel("clip.mp4", position="centre")

    def test_invalid_crop(self):
        with self.assertRaises(ValueError):
            Panel("clip.mp4", crop="energy")

    def test_zero_speed_raises(self):
        with self.assertRaises(ValueError):
            Panel("clip.mp4", speed=0.0)

    def test_negative_speed_raises(self):
        with self.assertRaises(ValueError):
            Panel("clip.mp4", speed=-1.0)


# ---------------------------------------------------------------------------
# MultiPanelCanvas construction
# ---------------------------------------------------------------------------

class TestMultiPanelCanvasConstruction(unittest.TestCase):

    def test_empty_panels_raises(self):
        with self.assertRaises(ValueError):
            MultiPanelCanvas([])

    def test_panel_width_four_panels(self):
        canvas = _canvas(canvas_size=(4860, 2160))
        self.assertEqual(canvas._panel_width(), 1215)

    def test_panel_width_two_panels(self):
        panels = [
            Panel("a.mp4", position="outer_left"),
            Panel("b.mp4", position="outer_right"),
        ]
        canvas = MultiPanelCanvas(panels, canvas_size=(2430, 2160))
        self.assertEqual(canvas._panel_width(), 1215)

    def test_set_finale_stores_clip(self):
        canvas = _canvas()
        canvas.set_finale("capitol.mp4", beats=8)
        self.assertIsNotNone(canvas._finale)
        self.assertEqual(canvas._finale.beats, 8)

    def test_set_finale_invalid_mode(self):
        canvas = _canvas()
        with self.assertRaises(ValueError):
            canvas.set_finale("capitol.mp4", mode="split")


# ---------------------------------------------------------------------------
# filter_complex structure
# ---------------------------------------------------------------------------

class TestFilterComplex(unittest.TestCase):

    def test_contains_setpts_for_each_panel(self):
        canvas = _canvas()
        fc = canvas._build_filter_complex()
        # panel 0 and 1: speed=2.0 → setpts=0.5
        self.assertIn("setpts=0.500000*PTS", fc)
        # panel 2 and 3: speed=0.5 → setpts=2.0
        self.assertIn("setpts=2.000000*PTS", fc)

    def test_smart_crop_applied_to_inner_panels(self):
        canvas = _canvas()
        fc = canvas._build_filter_complex()
        # panels 1 and 2 are smart-crop
        self.assertIn("crop=iw*6/10:ih*6/10", fc)

    def test_full_crop_does_not_include_crop_filter(self):
        panels = [Panel("a.mp4", position="outer_left", crop="full")]
        canvas = MultiPanelCanvas(panels, canvas_size=(1215, 2160))
        chain, _ = canvas._panel_filter(0, panels[0])
        self.assertNotIn("crop=", chain)

    def test_scale_uses_panel_width_and_canvas_height(self):
        canvas = _canvas(canvas_size=(4860, 2160))  # panel_w=1215
        fc = canvas._build_filter_complex()
        self.assertIn("scale=1215:2160", fc)

    def test_hstack_inputs_count(self):
        canvas = _canvas()
        fc = canvas._build_filter_complex()
        self.assertIn("hstack=inputs=4", fc)

    def test_output_label_present(self):
        canvas = _canvas()
        fc = canvas._build_filter_complex()
        self.assertIn("[out]", fc)

    def test_finale_adds_concat(self):
        canvas = _canvas()
        canvas.set_finale("capitol.mp4")
        fc = canvas._build_filter_complex()
        self.assertIn("concat=n=2", fc)
        self.assertIn("[panels]", fc)
        self.assertIn("[fin]", fc)

    def test_no_finale_no_concat(self):
        canvas = _canvas()
        fc = canvas._build_filter_complex()
        self.assertNotIn("concat", fc)

    def test_finale_scales_to_full_canvas(self):
        canvas = _canvas(canvas_size=(4860, 2160))
        canvas.set_finale("capitol.mp4")
        fc = canvas._build_filter_complex()
        self.assertIn("scale=4860:2160", fc)

    def test_panels_have_sequential_stream_indices(self):
        canvas = _canvas()
        fc = canvas._build_filter_complex()
        for i in range(4):
            self.assertIn(f"[{i}:v]", fc)


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------

class TestBuildCommand(unittest.TestCase):

    def test_one_input_per_panel(self):
        canvas = _canvas()
        cmd = canvas._build_command(Path("out.mp4"), crf=18, preset="fast")
        input_count = cmd.count("-i")
        self.assertEqual(input_count, len(canvas.panels))

    def test_finale_adds_extra_input(self):
        canvas = _canvas()
        canvas.set_finale("capitol.mp4")
        cmd = canvas._build_command(Path("out.mp4"), crf=18, preset="fast")
        self.assertEqual(cmd.count("-i"), len(canvas.panels) + 1)

    def test_filter_complex_in_command(self):
        canvas = _canvas()
        cmd = canvas._build_command(Path("out.mp4"), crf=18, preset="fast")
        self.assertIn("-filter_complex", cmd)

    def test_map_out_in_command(self):
        canvas = _canvas()
        cmd = canvas._build_command(Path("out.mp4"), crf=18, preset="fast")
        map_idx = cmd.index("-map") + 1
        self.assertEqual(cmd[map_idx], "[out]")

    def test_crf_in_command(self):
        canvas = _canvas()
        cmd = canvas._build_command(Path("out.mp4"), crf=23, preset="fast")
        crf_idx = cmd.index("-crf") + 1
        self.assertEqual(cmd[crf_idx], "23")


# ---------------------------------------------------------------------------
# Render — happy path and errors
# ---------------------------------------------------------------------------

class TestRender(unittest.TestCase):

    def test_returns_output_path(self):
        result = _render(_canvas())
        self.assertEqual(result, Path("output.mp4"))

    def test_panel_file_not_found(self):
        canvas = _canvas()
        with patch.object(Path, "exists", return_value=False):
            with self.assertRaises(FileNotFoundError):
                canvas.render("output.mp4")

    def test_finale_file_not_found(self):
        canvas = _canvas()
        canvas.set_finale("capitol.mp4")
        # panels exist, finale does not
        def exists_side_effect(self):
            return self.name != "capitol.mp4"
        with patch.object(Path, "exists", exists_side_effect), \
             patch.object(Path, "mkdir"):
            with self.assertRaises(FileNotFoundError):
                canvas.render("output.mp4")

    def test_ffmpeg_not_found(self):
        with self.assertRaises(LayoutError) as ctx:
            _render(_canvas(), side_effect=FileNotFoundError)
        self.assertIn("ffmpeg not found", str(ctx.exception))

    def test_ffmpeg_timeout(self):
        with self.assertRaises(LayoutError) as ctx:
            _render(_canvas(),
                    side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=3600))
        self.assertIn("timed out", str(ctx.exception))

    def test_ffmpeg_nonzero_exit(self):
        with self.assertRaises(LayoutError):
            _render(_canvas(), returncode=1)

    def test_single_panel_renders(self):
        canvas = MultiPanelCanvas(
            [Panel("a.mp4", position="outer_left")],
            canvas_size=(1215, 2160),
        )
        result = _render(canvas)
        self.assertEqual(result, Path("output.mp4"))


if __name__ == "__main__":
    unittest.main()
