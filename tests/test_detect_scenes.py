"""Tests for videoflow.analysis.detect_scenes."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from videoflow.analysis import Scene, SceneError, detect_scenes


def _make_timecode(seconds: float) -> MagicMock:
    tc = MagicMock()
    tc.get_seconds.return_value = seconds
    return tc


def _make_raw_scenes(*pairs: tuple[float, float]) -> list:
    """Build a fake PySceneDetect scene list from (start_s, end_s) pairs."""
    return [(_make_timecode(start), _make_timecode(end)) for start, end in pairs]


class TestDetectScenes(unittest.TestCase):

    def _run(self, raw_scenes, *, threshold=27.0, detector="content"):
        """Run detect_scenes with a mocked PySceneDetect."""
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            src = Path(f.name)
            with patch("videoflow.analysis.detect", return_value=raw_scenes), \
                 patch("videoflow.analysis.ContentDetector"), \
                 patch("videoflow.analysis.ThresholdDetector"):
                return detect_scenes(src, threshold=threshold, detector=detector)

    def test_returns_list_of_scenes(self):
        result = self._run(_make_raw_scenes((0.0, 4.2), (4.2, 9.8)))
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        for s in result:
            self.assertIsInstance(s, Scene)

    def test_timestamps_converted_to_ms(self):
        result = self._run(_make_raw_scenes((0.0, 4.2), (4.2, 9.8)))
        self.assertEqual(result[0].start_ms, 0)
        self.assertEqual(result[0].end_ms, 4200)
        self.assertEqual(result[1].start_ms, 4200)
        self.assertEqual(result[1].end_ms, 9800)

    def test_indices_are_one_based(self):
        result = self._run(_make_raw_scenes((0.0, 3.0), (3.0, 6.0), (6.0, 9.0)))
        self.assertEqual([s.index for s in result], [1, 2, 3])

    def test_duration_ms_property(self):
        result = self._run(_make_raw_scenes((0.0, 5.0)))
        self.assertEqual(result[0].duration_ms, 5000)

    def test_empty_result(self):
        result = self._run([])
        self.assertEqual(result, [])

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            detect_scenes("/nonexistent/clip.mp4")

    def test_invalid_detector(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            with self.assertRaises(ValueError) as ctx:
                detect_scenes(f.name, detector="optical_flow")
            self.assertIn("detector", str(ctx.exception))

    def test_scenedetect_not_installed(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            with patch("videoflow.analysis.detect", None):
                with self.assertRaises(SceneError) as ctx:
                    detect_scenes(f.name)
                self.assertIn("pip install scenedetect", str(ctx.exception))

    def test_detection_error_wrapped(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            src = Path(f.name)
            with patch("videoflow.analysis.detect", side_effect=RuntimeError("codec error")), \
                 patch("videoflow.analysis.ContentDetector"), \
                 patch("videoflow.analysis.ThresholdDetector"):
                with self.assertRaises(SceneError) as ctx:
                    detect_scenes(src)
                self.assertIn("codec error", str(ctx.exception))

    def test_uses_content_detector_by_default(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            src = Path(f.name)
            mock_content = MagicMock()
            mock_threshold = MagicMock()
            with patch("videoflow.analysis.detect", return_value=[]) as mock_detect, \
                 patch("videoflow.analysis.ContentDetector", return_value=mock_content), \
                 patch("videoflow.analysis.ThresholdDetector", return_value=mock_threshold):
                detect_scenes(src)
                mock_detect.assert_called_once_with(str(src), mock_content)

    def test_uses_threshold_detector(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            src = Path(f.name)
            mock_threshold = MagicMock()
            with patch("videoflow.analysis.detect", return_value=[]) as mock_detect, \
                 patch("videoflow.analysis.ContentDetector"), \
                 patch("videoflow.analysis.ThresholdDetector", return_value=mock_threshold):
                detect_scenes(src, detector="threshold")
                mock_detect.assert_called_once_with(str(src), mock_threshold)

    def test_threshold_passed_to_detector(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            src = Path(f.name)
            with patch("videoflow.analysis.detect", return_value=[]), \
                 patch("videoflow.analysis.ContentDetector") as mock_cls, \
                 patch("videoflow.analysis.ThresholdDetector"):
                detect_scenes(src, threshold=15.0)
                mock_cls.assert_called_once_with(threshold=15.0)

    def test_rounding_ms(self):
        """Fractional milliseconds are rounded to the nearest int."""
        result = self._run(_make_raw_scenes((0.0, 4.2009)))
        self.assertIsInstance(result[0].end_ms, int)
        self.assertEqual(result[0].end_ms, 4201)


if __name__ == "__main__":
    unittest.main()
