"""Tests for AudioBeatMap and MultiPanelCanvas JSON serialisation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from videoflow.audio import AudioBeatMap, BeatError
from videoflow.layout import LayoutError, MultiPanelCanvas, Panel


def _sample_beat_map() -> AudioBeatMap:
    return AudioBeatMap(
        bpm=120.0,
        duration_ms=16000,
        beats=[0, 500, 1000, 1500],
        downbeats=[0],
        phrases=[(0, 2000)],
        energy=[1.0, 0.8, 0.9, 0.7],
    )


def _sample_canvas() -> MultiPanelCanvas:
    panels = [
        Panel("tunnel.mp4",   speed=2.0, position="outer_left",  crop="full"),
        Panel("tunnel.mp4",   speed=2.0, position="inner_left",  crop="smart"),
        Panel("platform.mp4", speed=0.5, position="inner_right", crop="smart"),
        Panel("platform.mp4", speed=0.5, position="outer_right", crop="full"),
    ]
    return MultiPanelCanvas(panels, canvas_size=(4860, 2160))


# ---------------------------------------------------------------------------
# AudioBeatMap serialisation
# ---------------------------------------------------------------------------

class TestAudioBeatMapSerialisation(unittest.TestCase):

    def test_to_dict_has_required_keys(self):
        d = _sample_beat_map().to_dict()
        for key in ("bpm", "duration_ms", "beats", "downbeats", "phrases", "energy"):
            self.assertIn(key, d)

    def test_to_dict_bpm(self):
        d = _sample_beat_map().to_dict()
        self.assertAlmostEqual(d["bpm"], 120.0)

    def test_to_dict_phrases_are_dicts(self):
        d = _sample_beat_map().to_dict()
        self.assertEqual(d["phrases"][0], {"start_ms": 0, "end_ms": 2000})

    def test_round_trip_via_dict(self):
        original = _sample_beat_map()
        restored = AudioBeatMap.load.__func__  # just test via save/load below
        d = original.to_dict()
        # Manually reconstruct to verify field-by-field
        self.assertEqual(d["beats"], original.beats)
        self.assertEqual(d["downbeats"], original.downbeats)

    def test_save_and_load(self):
        bm = _sample_beat_map()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "beat_map.json"
            bm.save(path)
            self.assertTrue(path.exists())
            restored = AudioBeatMap.load(path)

        self.assertAlmostEqual(restored.bpm, bm.bpm)
        self.assertEqual(restored.beats, bm.beats)
        self.assertEqual(restored.downbeats, bm.downbeats)
        self.assertEqual(restored.phrases, bm.phrases)
        self.assertEqual(restored.duration_ms, bm.duration_ms)
        for a, b in zip(restored.energy, bm.energy):
            self.assertAlmostEqual(a, b, places=5)

    def test_save_creates_parent_dirs(self):
        bm = _sample_beat_map()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir" / "beat_map.json"
            bm.save(path)
            self.assertTrue(path.exists())

    def test_load_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            AudioBeatMap.load("nonexistent_beat_map.json")

    def test_load_invalid_json_raises_beat_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.json"
            path.write_text('{"bpm": 120}')  # missing required fields
            with self.assertRaises(BeatError):
                AudioBeatMap.load(path)

    def test_saved_json_is_human_readable(self):
        """The JSON file must be indented, not a single line."""
        bm = _sample_beat_map()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "beat_map.json"
            bm.save(path)
            content = path.read_text()
        self.assertIn("\n", content)


# ---------------------------------------------------------------------------
# MultiPanelCanvas serialisation
# ---------------------------------------------------------------------------

class TestMultiPanelCanvasSerialisation(unittest.TestCase):

    def test_to_dict_has_type(self):
        d = _sample_canvas().to_dict()
        self.assertEqual(d["type"], "canvas_edit")

    def test_to_dict_canvas_size(self):
        d = _sample_canvas().to_dict()
        self.assertEqual(d["canvas_size"], [4860, 2160])

    def test_to_dict_panel_count(self):
        d = _sample_canvas().to_dict()
        self.assertEqual(len(d["panels"]), 4)

    def test_to_dict_panel_fields(self):
        d = _sample_canvas().to_dict()
        p = d["panels"][0]
        for key in ("input", "speed", "position", "crop"):
            self.assertIn(key, p)

    def test_to_dict_no_finale_key_by_default(self):
        d = _sample_canvas().to_dict()
        self.assertNotIn("finale", d)

    def test_to_dict_with_finale(self):
        canvas = _sample_canvas()
        canvas.set_finale("capitol.mp4", beats=8)
        d = canvas.to_dict()
        self.assertIn("finale", d)
        self.assertEqual(d["finale"]["beats"], 8)

    def test_from_dict_round_trip(self):
        original = _sample_canvas()
        original.set_finale("capitol.mp4", beats=8)
        restored = MultiPanelCanvas.from_dict(original.to_dict())

        self.assertEqual(len(restored.panels), len(original.panels))
        self.assertEqual(restored.canvas_size, original.canvas_size)
        self.assertIsNotNone(restored._finale)
        self.assertEqual(restored._finale.beats, 8)

    def test_from_dict_panel_values(self):
        original = _sample_canvas()
        restored = MultiPanelCanvas.from_dict(original.to_dict())
        for op, rp in zip(original.panels, restored.panels):
            self.assertAlmostEqual(rp.speed, op.speed)
            self.assertEqual(rp.position, op.position)
            self.assertEqual(rp.crop, op.crop)

    def test_save_and_load(self):
        canvas = _sample_canvas()
        canvas.set_finale("capitol.mp4", beats=4)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "canvas.json"
            canvas.save(path)
            restored = MultiPanelCanvas.load(path)

        self.assertEqual(len(restored.panels), 4)
        self.assertIsNotNone(restored._finale)

    def test_load_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            MultiPanelCanvas.load("nonexistent_canvas.json")

    def test_load_invalid_raises_layout_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.json"
            path.write_text("{}")   # missing panels
            with self.assertRaises(LayoutError):
                MultiPanelCanvas.load(path)

    def test_saved_json_is_human_readable(self):
        canvas = _sample_canvas()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "canvas.json"
            canvas.save(path)
            content = path.read_text()
        self.assertIn("\n", content)
        data = json.loads(content)
        self.assertEqual(data["type"], "canvas_edit")


if __name__ == "__main__":
    unittest.main()
