"""videoflow — composable video workflow pipeline."""

from videoflow.analysis import DETECTOR_INFO, DetectorInfo, Scene, SceneError, detect_scenes
from videoflow.audio import AudioBeatMap, BeatError, analyze_beats
from videoflow.generate import (
    GenerateError,
    beats_to_curve,
    classify_modes,
    export_funscript,
    generate_from_beats,
    shape_curve,
)
from videoflow.layout import FinaleClip, LayoutError, MultiPanelCanvas, Panel
from videoflow.mix import AudioMix, AudioTrack, MixError, VolumeRamp
from videoflow.reel import Reel, ReelClip, ReelError

__all__ = [
    "DETECTOR_INFO",
    "DetectorInfo",
    "Scene",
    "SceneError",
    "detect_scenes",
    "AudioBeatMap",
    "BeatError",
    "analyze_beats",
    "GenerateError",
    "beats_to_curve",
    "classify_modes",
    "export_funscript",
    "generate_from_beats",
    "shape_curve",
    "FinaleClip",
    "LayoutError",
    "MultiPanelCanvas",
    "Panel",
    "AudioMix",
    "AudioTrack",
    "MixError",
    "VolumeRamp",
    "Reel",
    "ReelClip",
    "ReelError",
]
