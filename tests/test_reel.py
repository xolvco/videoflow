"""Tests for videoflow.reel — ReelClip, Reel."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from videoflow.reel import Reel, ReelClip, ReelError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_run(returncode=0, stdout=""):
    r = MagicMock()
    r.returncode = returncode
    r.stdout = stdout
    r.stderr = "err" if returncode != 0 else ""
    return r


def _ffprobe_response(duration_s: float) -> str:
    return json.dumps({"format": {"duration": str(duration_s)}})


def _three_clips() -> list[ReelClip]:
    return [
        ReelClip("a.mp4", title="Alpha"),
        ReelClip("b.mp4", title="Beta"),
        ReelClip("c.mp4", title="Gamma"),
    ]


def _reel(clips=None, **kw) -> Reel:
    return Reel(clips or _three_clips(), **kw)


def _render(reel, returncode=0, side_effect=None, ffprobe_duration=10.0):
    ffprobe_resp = _mock_run(stdout=_ffprobe_response(ffprobe_duration))
    ffmpeg_resp = (
        {"side_effect": side_effect}
        if side_effect
        else {"return_value": _mock_run(returncode=returncode)}
    )

    def run_side_effect(cmd, **_kw):
        if cmd[0] == "ffprobe":
            return ffprobe_resp
        return ffmpeg_resp.get("return_value", MagicMock(returncode=0, stderr=""))

    with patch("videoflow.reel.subprocess.run", side_effect=run_side_effect), \
         patch.object(Path, "exists", return_value=True), \
         patch.object(Path, "mkdir"), \
         patch.object(Path, "unlink"):
        if side_effect:
            with patch("videoflow.reel.subprocess.run", side_effect=side_effect):
                return reel.render("output.mp4")
        return reel.render("output.mp4")


# ---------------------------------------------------------------------------
# ReelClip validation
# ---------------------------------------------------------------------------

class TestReelClip(unittest.TestCase):

    def test_valid_clip(self):
        c = ReelClip("clip.mp4", title="My Clip")
        self.assertEqual(c.title, "My Clip")

    def test_defaults(self):
        c = ReelClip("clip.mp4")
        self.assertEqual(c.title, "")
        self.assertEqual(c.start_ms, 0)
        self.assertIsNone(c.end_ms)

    def test_negative_start_ms_raises(self):
        with self.assertRaises(ValueError):
            ReelClip("clip.mp4", start_ms=-1)

    def test_end_ms_equal_to_start_raises(self):
        with self.assertRaises(ValueError):
            ReelClip("clip.mp4", start_ms=1000, end_ms=1000)

    def test_end_ms_less_than_start_raises(self):
        with self.assertRaises(ValueError):
            ReelClip("clip.mp4", start_ms=2000, end_ms=1000)

    def test_valid_trim(self):
        c = ReelClip("clip.mp4", start_ms=1000, end_ms=5000)
        self.assertEqual(c.end_ms, 5000)


# ---------------------------------------------------------------------------
# Reel construction
# ---------------------------------------------------------------------------

class TestReelConstruction(unittest.TestCase):

    def test_empty_clips_raises(self):
        with self.assertRaises(ValueError):
            Reel([])

    def test_negative_gap_raises(self):
        with self.assertRaises(ValueError):
            Reel(_three_clips(), gap_ms=-1)

    def test_zero_gap_is_valid(self):
        reel = Reel(_three_clips(), gap_ms=0)
        self.assertEqual(reel.gap_ms, 0)

    def test_default_gap(self):
        reel = _reel()
        self.assertEqual(reel.gap_ms, 2000)

    def test_default_canvas_size(self):
        reel = _reel()
        self.assertEqual(reel.canvas_size, (1920, 1080))

    def test_single_clip_is_valid(self):
        reel = Reel([ReelClip("a.mp4")])
        self.assertEqual(len(reel.clips), 1)


# ---------------------------------------------------------------------------
# from_folder
# ---------------------------------------------------------------------------

class TestFromFolder(unittest.TestCase):

    def test_loads_sorted_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            (p / "c.mp4").write_text("fake")
            (p / "a.mp4").write_text("fake")
            (p / "b.mp4").write_text("fake")
            reel = Reel.from_folder(tmpdir)

        names = [Path(c.input).name for c in reel.clips]
        self.assertEqual(names, ["a.mp4", "b.mp4", "c.mp4"])

    def test_title_is_stem(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "intro.mp4").write_text("fake")
            reel = Reel.from_folder(tmpdir)
        self.assertEqual(reel.clips[0].title, "intro")

    def test_folder_not_found_raises(self):
        with self.assertRaises(FileNotFoundError):
            Reel.from_folder("/nonexistent/folder")

    def test_no_matching_files_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "video.mov").write_text("fake")
            with self.assertRaises(ValueError):
                Reel.from_folder(tmpdir, pattern="*.mp4")

    def test_custom_pattern(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "clip.mov").write_text("fake")
            reel = Reel.from_folder(tmpdir, pattern="*.mov")
        self.assertEqual(len(reel.clips), 1)

    def test_gap_ms_forwarded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.mp4").write_text("fake")
            reel = Reel.from_folder(tmpdir, gap_ms=3000)
        self.assertEqual(reel.gap_ms, 3000)

    def test_sort_name_is_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            (p / "c.mp4").write_text("fake")
            (p / "a.mp4").write_text("fake")
            (p / "b.mp4").write_text("fake")
            reel = Reel.from_folder(tmpdir)
        names = [Path(c.input).name for c in reel.clips]
        self.assertEqual(names, ["a.mp4", "b.mp4", "c.mp4"])

    def test_sort_date_orders_by_mtime(self):
        import time
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            # Write files with deliberate mtime ordering: b before a before c
            (p / "b.mp4").write_text("fake")
            time.sleep(0.02)
            (p / "a.mp4").write_text("fake")
            time.sleep(0.02)
            (p / "c.mp4").write_text("fake")
            reel = Reel.from_folder(tmpdir, sort="date")
        names = [Path(c.input).name for c in reel.clips]
        self.assertEqual(names, ["b.mp4", "a.mp4", "c.mp4"])

    def test_sort_invalid_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.mp4").write_text("fake")
            with self.assertRaises(ValueError):
                Reel.from_folder(tmpdir, sort="random")


# ---------------------------------------------------------------------------
# clip_duration_ms
# ---------------------------------------------------------------------------

class TestClipDurationMs(unittest.TestCase):

    def test_returns_end_minus_start_when_end_set(self):
        reel = _reel()
        clip = ReelClip("a.mp4", start_ms=1000, end_ms=6000)
        self.assertEqual(reel._clip_duration_ms(clip), 5000)

    def test_probes_file_when_end_not_set(self):
        reel = _reel()
        clip = ReelClip("a.mp4")
        mock_result = _mock_run(stdout=_ffprobe_response(10.5))
        with patch("videoflow.reel.subprocess.run", return_value=mock_result):
            dur = reel._clip_duration_ms(clip)
        self.assertEqual(dur, 10500)

    def test_probe_subtracts_start_ms(self):
        reel = _reel()
        clip = ReelClip("a.mp4", start_ms=2000)
        mock_result = _mock_run(stdout=_ffprobe_response(10.0))
        with patch("videoflow.reel.subprocess.run", return_value=mock_result):
            dur = reel._clip_duration_ms(clip)
        self.assertEqual(dur, 8000)

    def test_ffprobe_not_found_raises_reel_error(self):
        reel = _reel()
        clip = ReelClip("a.mp4")
        with patch("videoflow.reel.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaises(ReelError) as ctx:
                reel._clip_duration_ms(clip)
        self.assertIn("ffprobe not found", str(ctx.exception))

    def test_ffprobe_nonzero_raises_reel_error(self):
        reel = _reel()
        clip = ReelClip("a.mp4")
        with patch("videoflow.reel.subprocess.run", return_value=_mock_run(returncode=1)):
            with self.assertRaises(ReelError):
                reel._clip_duration_ms(clip)


# ---------------------------------------------------------------------------
# ffmetadata
# ---------------------------------------------------------------------------

class TestBuildFfmetadata(unittest.TestCase):

    def test_starts_with_ffmetadata_header(self):
        reel = _reel()
        meta = reel._build_ffmetadata([10000, 8000, 5000])
        self.assertTrue(meta.startswith(";FFMETADATA1"))

    def test_chapter_count(self):
        reel = _reel()
        meta = reel._build_ffmetadata([10000, 8000, 5000])
        self.assertEqual(meta.count("[CHAPTER]"), 3)

    def test_first_chapter_starts_at_zero(self):
        reel = _reel()
        meta = reel._build_ffmetadata([10000, 8000, 5000])
        self.assertIn("START=0", meta)

    def test_second_chapter_starts_after_gap(self):
        reel = Reel(_three_clips(), gap_ms=2000)
        meta = reel._build_ffmetadata([10000, 8000, 5000])
        # clip 0 ends at 10000ms, gap=2000ms → clip 1 starts at 12000ms
        self.assertIn("START=12000", meta)

    def test_chapter_titles_present(self):
        reel = _reel()
        meta = reel._build_ffmetadata([10000, 8000, 5000])
        self.assertIn("title=Alpha", meta)
        self.assertIn("title=Beta", meta)
        self.assertIn("title=Gamma", meta)

    def test_title_defaults_to_stem_when_empty(self):
        reel = Reel([ReelClip("my_video.mp4", title="")])
        meta = reel._build_ffmetadata([10000])
        self.assertIn("title=my_video", meta)

    def test_timebase_is_ms(self):
        reel = _reel()
        meta = reel._build_ffmetadata([10000, 8000, 5000])
        self.assertIn("TIMEBASE=1/1000", meta)

    def test_chapter_end_equals_clip_duration(self):
        reel = Reel([ReelClip("a.mp4", title="A")])
        meta = reel._build_ffmetadata([15000])
        self.assertIn("END=15000", meta)

    def test_zero_gap_chapters_are_contiguous(self):
        reel = Reel(_three_clips(), gap_ms=0)
        meta = reel._build_ffmetadata([10000, 8000, 5000])
        # clip 1 starts immediately after clip 0 ends
        self.assertIn("START=10000", meta)


# ---------------------------------------------------------------------------
# Filter complex structure
# ---------------------------------------------------------------------------

class TestBuildFilterComplex(unittest.TestCase):

    def test_returns_three_tuple(self):
        reel = _reel()
        result = reel._build_filter_complex()
        self.assertEqual(len(result), 3)

    def test_video_out_label(self):
        reel = _reel()
        _, video_out, _ = reel._build_filter_complex()
        self.assertEqual(video_out, "[vout]")

    def test_audio_out_label(self):
        reel = _reel()
        _, _, audio_out = reel._build_filter_complex()
        self.assertEqual(audio_out, "[aout]")

    def test_scale_filter_present(self):
        reel = Reel(_three_clips(), canvas_size=(1280, 720))
        fc, _, _ = reel._build_filter_complex()
        self.assertIn("scale=1280:720", fc)

    def test_gap_color_source_present(self):
        reel = _reel()
        fc, _, _ = reel._build_filter_complex()
        self.assertIn("color=black", fc)

    def test_gap_aevalsrc_present(self):
        reel = _reel()
        fc, _, _ = reel._build_filter_complex()
        self.assertIn("aevalsrc=0", fc)

    def test_n_minus_one_gaps(self):
        """3 clips → 2 gaps."""
        reel = _reel()
        fc, _, _ = reel._build_filter_complex()
        self.assertEqual(fc.count("color=black"), 2)

    def test_single_clip_no_gap(self):
        reel = Reel([ReelClip("a.mp4")])
        fc, _, _ = reel._build_filter_complex()
        self.assertNotIn("color=black", fc)

    def test_concat_n_correct(self):
        """3 clips + 2 gaps = 5 segments."""
        reel = _reel()
        fc, _, _ = reel._build_filter_complex()
        self.assertIn("concat=n=5", fc)

    def test_single_clip_concat_n_one(self):
        reel = Reel([ReelClip("a.mp4")])
        fc, _, _ = reel._build_filter_complex()
        self.assertIn("concat=n=1", fc)

    def test_gap_duration_in_filter(self):
        reel = Reel(_three_clips(), gap_ms=3000)
        fc, _, _ = reel._build_filter_complex()
        self.assertIn("duration=3.000", fc)

    def test_trim_applied_when_start_set(self):
        clips = [
            ReelClip("a.mp4", start_ms=5000, end_ms=15000),
            ReelClip("b.mp4"),
        ]
        reel = Reel(clips)
        fc, _, _ = reel._build_filter_complex()
        self.assertIn("trim=start=5.000:end=15.000", fc)

    def test_trim_not_applied_when_no_trim(self):
        reel = Reel([ReelClip("a.mp4")])
        fc, _, _ = reel._build_filter_complex()
        self.assertNotIn("trim=", fc)

    def test_sequential_input_indices(self):
        reel = _reel()
        fc, _, _ = reel._build_filter_complex()
        for i in range(3):
            self.assertIn(f"[{i}:v]", fc)
            self.assertIn(f"[{i}:a]", fc)

    def test_vout_in_filter(self):
        reel = _reel()
        fc, _, _ = reel._build_filter_complex()
        self.assertIn("[vout]", fc)

    def test_aout_in_filter(self):
        reel = _reel()
        fc, _, _ = reel._build_filter_complex()
        self.assertIn("[aout]", fc)


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------

class TestBuildCommand(unittest.TestCase):

    def _cmd(self, reel=None, meta_path=None):
        reel = reel or _reel()
        meta = meta_path or Path("meta.txt")
        return reel._build_command(Path("out.mp4"), meta, crf=18, preset="fast")

    def test_one_input_per_clip(self):
        cmd = self._cmd()
        self.assertEqual(cmd.count("-i"), len(_three_clips()) + 1)  # +1 for meta

    def test_meta_file_is_last_input(self):
        meta = Path("chapters.txt")
        cmd = self._cmd(meta_path=meta)
        # Find all -i args
        inputs = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-i"]
        self.assertEqual(inputs[-1], str(meta))

    def test_filter_complex_present(self):
        cmd = self._cmd()
        self.assertIn("-filter_complex", cmd)

    def test_map_vout(self):
        cmd = self._cmd()
        map_idx = cmd.index("-map") + 1
        self.assertEqual(cmd[map_idx], "[vout]")

    def test_map_aout(self):
        cmd = self._cmd()
        # Find second -map
        maps = [i for i, v in enumerate(cmd) if v == "-map"]
        self.assertEqual(cmd[maps[1] + 1], "[aout]")

    def test_map_metadata_index(self):
        cmd = self._cmd()
        idx = cmd.index("-map_metadata") + 1
        # 3 clips → meta is at index 3
        self.assertEqual(cmd[idx], "3")

    def test_crf_value(self):
        cmd = self._cmd()
        self.assertEqual(cmd[cmd.index("-crf") + 1], "18")

    def test_libx264_codec(self):
        cmd = self._cmd()
        self.assertIn("libx264", cmd)

    def test_aac_audio(self):
        cmd = self._cmd()
        self.assertIn("aac", cmd)


# ---------------------------------------------------------------------------
# Render — happy path and errors
# ---------------------------------------------------------------------------

class TestRender(unittest.TestCase):

    def test_returns_output_path(self):
        result = _render(_reel())
        self.assertEqual(result, Path("output.mp4"))

    def test_clip_not_found_raises(self):
        reel = _reel()
        with patch.object(Path, "exists", return_value=False):
            with self.assertRaises(FileNotFoundError):
                reel.render("output.mp4")

    def test_ffmpeg_not_found_raises_reel_error(self):
        reel = _reel()
        ffprobe_resp = _mock_run(stdout=_ffprobe_response(10.0))

        def run_side_effect(cmd, **kw):
            if cmd[0] == "ffprobe":
                return ffprobe_resp
            raise FileNotFoundError

        with patch("videoflow.reel.subprocess.run", side_effect=run_side_effect), \
             patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "mkdir"), \
             patch.object(Path, "unlink"):
            with self.assertRaises(ReelError) as ctx:
                reel.render("output.mp4")
        self.assertIn("ffmpeg not found", str(ctx.exception))

    def test_ffmpeg_timeout_raises_reel_error(self):
        reel = _reel()
        ffprobe_resp = _mock_run(stdout=_ffprobe_response(10.0))

        def run_side_effect(cmd, **kw):
            if cmd[0] == "ffprobe":
                return ffprobe_resp
            raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=3600)

        with patch("videoflow.reel.subprocess.run", side_effect=run_side_effect), \
             patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "mkdir"), \
             patch.object(Path, "unlink"):
            with self.assertRaises(ReelError) as ctx:
                reel.render("output.mp4")
        self.assertIn("timed out", str(ctx.exception))

    def test_ffmpeg_nonzero_raises_reel_error(self):
        reel = _reel()
        ffprobe_resp = _mock_run(stdout=_ffprobe_response(10.0))
        ffmpeg_fail = _mock_run(returncode=1)

        def run_side_effect(cmd, **kw):
            if cmd[0] == "ffprobe":
                return ffprobe_resp
            return ffmpeg_fail

        with patch("videoflow.reel.subprocess.run", side_effect=run_side_effect), \
             patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "mkdir"), \
             patch.object(Path, "unlink"):
            with self.assertRaises(ReelError):
                reel.render("output.mp4")


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

class TestReelSerialisation(unittest.TestCase):

    def _sample(self) -> Reel:
        return Reel(
            [
                ReelClip("a.mp4", title="Alpha", start_ms=0, end_ms=10000),
                ReelClip("b.mp4", title="Beta"),
            ],
            gap_ms=2500,
            canvas_size=(1280, 720),
        )

    def test_to_dict_type(self):
        self.assertEqual(self._sample().to_dict()["type"], "reel")

    def test_to_dict_gap_ms(self):
        self.assertEqual(self._sample().to_dict()["gap_ms"], 2500)

    def test_to_dict_canvas_size(self):
        self.assertEqual(self._sample().to_dict()["canvas_size"], [1280, 720])

    def test_to_dict_clip_count(self):
        self.assertEqual(len(self._sample().to_dict()["clips"]), 2)

    def test_to_dict_clip_fields(self):
        c = self._sample().to_dict()["clips"][0]
        for key in ("input", "title", "start_ms", "end_ms"):
            self.assertIn(key, c)

    def test_from_dict_round_trip(self):
        original = self._sample()
        restored = Reel.from_dict(original.to_dict())
        self.assertEqual(len(restored.clips), 2)
        self.assertEqual(restored.gap_ms, original.gap_ms)
        self.assertEqual(restored.canvas_size, original.canvas_size)
        self.assertEqual(restored.clips[0].title, "Alpha")
        self.assertEqual(restored.clips[0].end_ms, 10000)
        self.assertIsNone(restored.clips[1].end_ms)

    def test_from_dict_missing_clips_raises(self):
        with self.assertRaises(ReelError):
            Reel.from_dict({})

    def test_save_and_load(self):
        original = self._sample()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "reel.json"
            original.save(path)
            restored = Reel.load(path)
        self.assertEqual(len(restored.clips), 2)
        self.assertEqual(restored.gap_ms, 2500)

    def test_load_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            Reel.load("nonexistent_reel.json")

    def test_saved_json_is_human_readable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "reel.json"
            self._sample().save(path)
            content = path.read_text()
        self.assertIn("\n", content)
        data = json.loads(content)
        self.assertEqual(data["type"], "reel")


if __name__ == "__main__":
    unittest.main()
