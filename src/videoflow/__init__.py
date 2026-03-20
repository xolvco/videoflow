"""videoflow — composable video workflow pipeline."""

from videoflow.analysis import DETECTOR_INFO, DetectorInfo, Scene, SceneError, detect_scenes

__all__ = [
    "DETECTOR_INFO",
    "DetectorInfo",
    "Scene",
    "SceneError",
    "detect_scenes",
]
