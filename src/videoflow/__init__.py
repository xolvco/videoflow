"""videoflow — composable video workflow pipeline."""

from videoflow.analysis import Scene, SceneError, detect_scenes

__all__ = [
    "Scene",
    "SceneError",
    "detect_scenes",
]
