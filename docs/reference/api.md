# API Reference

---

## videoflow.reel

### `ReelClip`

```python
@dataclasses.dataclass
class ReelClip:
    input:    str | Path       # source video file
    title:    str  = ""        # chapter title (shown in compatible players)
    start_ms: int  = 0         # trim start offset in milliseconds
    end_ms:   int | None = None  # trim end offset (None = to end of file)
```

**Raises `ValueError`** if `start_ms < 0` or `end_ms <= start_ms`.

---

### `Reel`

```python
class Reel:
    def __init__(
        self,
        clips: list[ReelClip],
        *,
        gap_ms: int = 2000,
        canvas_size: tuple[int, int] = (1920, 1080),
        frame_rate: int = 30,
        sample_rate: int = 44100,
    ) -> None
```

**Raises `ValueError`** if `clips` is empty or `gap_ms < 0`.

#### `Reel.from_folder`

```python
@classmethod
def from_folder(
    cls,
    folder: str | Path,
    *,
    pattern: str = "*.mp4",
    gap_ms: int = 2000,
    **kw,
) -> Reel
```

Load all files matching `pattern` from `folder`, sorted by name.
Each clip's title is set to the filename stem.

**Raises:** `FileNotFoundError` if the folder doesn't exist; `ValueError` if no files match.

#### `Reel.render`

```python
def render(
    self,
    output: str | Path,
    *,
    crf: int = 18,
    preset: str = "fast",
    timeout: float = 3600.0,
) -> Path
```

Render to `output`.

1. Probes each clip's duration via `ffprobe` (skipped if `end_ms` is set).
2. Writes an ffmetadata file with one `[CHAPTER]` per clip.
3. Runs `ffmpeg` with interleaved clips and black-frame/silence gaps.

**Returns:** `Path` to the rendered file.

**Raises:**

- `FileNotFoundError` — a clip input file does not exist
- `ReelError` — `ffmpeg`/`ffprobe` not on PATH, non-zero exit, or timeout

#### `Reel.save` / `Reel.load`

```python
def save(self, path: str | Path) -> Path
@classmethod
def load(cls, path: str | Path) -> Reel
```

Save/load a JSON description of this reel.

---

### `ReelError`

```python
class ReelError(RuntimeError): ...
```

---

## videoflow.layout

### `Panel`

```python
@dataclasses.dataclass
class Panel:
    input:    str | Path          # source video file
    speed:    float = 1.0         # playback speed (2.0 = 2× fast, 0.5 = half speed)
    position: str   = "outer_left"  # "outer_left" | "inner_left" | "inner_right" | "outer_right"
    crop:     str   = "full"        # "full" (scale to fill) | "smart" (60% center crop then scale)
```

**`crop="smart"`** center-crops to 60% of the source before scaling — gives a zoomed-in view of the most active region of the frame. Use on inner panels alongside a full outer panel showing the same source.

**Raises `ValueError`** on invalid `position`, `crop`, or `speed <= 0`.

---

### `FinaleClip`

```python
@dataclasses.dataclass
class FinaleClip:
    input: str | Path    # video file
    beats: int = 8       # number of beats to hold (requires beat_map on MultiPanelCanvas)
    mode:  str = "full_width"   # only supported value
```

---

### `MultiPanelCanvas`

```python
class MultiPanelCanvas:
    def __init__(
        self,
        panels: list[Panel],
        *,
        canvas_size: tuple[int, int] = (4860, 2160),
        beat_map: AudioBeatMap | None = None,
        audio_mix: AudioMix | None = None,
    ) -> None
```

Standard layout: four 9:16 portrait panels side by side on a 4860×2160 canvas
(wider than 4K). Outer panels give context; inner panels show the same source
with `crop="smart"` for a zoomed-in close-up.

**Raises `ValueError`** if `panels` is empty.

#### `set_finale`

```python
def set_finale(
    self,
    clip: str | Path,
    *,
    beats: int = 8,
    mode: str = "full_width",
) -> None
```

Pin a full-width clip to the end. The clip expands across the entire canvas —
all panel positions become one image. The reveal moment.

#### `render`

```python
def render(
    self,
    output: str | Path,
    *,
    crf: int = 18,
    preset: str = "fast",
    timeout: float = 3600.0,
) -> Path
```

Builds an FFmpeg `filter_complex` that applies per-panel speed and crop, scales
each panel, stacks horizontally, and optionally appends the finale via `concat`.

**Raises:** `FileNotFoundError`, `LayoutError`

#### `save` / `load`

```python
def save(self, path: str | Path) -> Path
@classmethod
def load(cls, path: str | Path) -> MultiPanelCanvas
```

---

### `LayoutError`

```python
class LayoutError(RuntimeError): ...
```

---

## videoflow.mix

### `AudioTrack`

```python
@dataclasses.dataclass
class AudioTrack:
    input:       str | Path   # audio or video file (FFmpeg extracts audio automatically)
    level:       float = 1.0  # base volume 0.0–1.0
    fade_in_ms:  int   = 0    # fade-in from silence at track start
    fade_out_ms: int   = 0    # fade-out to silence at track end (requires AudioMix.duration_ms)
```

---

### `VolumeRamp`

```python
@dataclasses.dataclass
class VolumeRamp:
    track:    int          # index into AudioMix.tracks
    at_ms:    int          # when the ramp begins (ms from video start)
    to_level: float        # target level at the end of the ramp (0.0–1.0)
    over_ms:  int = 500    # ramp duration in milliseconds
```

Volume transitions linearly from the track's current level to `to_level` over `over_ms` ms.
Use multiple ramps to swell music at the reveal while ambient sound fades out.

---

### `AudioMix`

```python
@dataclasses.dataclass
class AudioMix:
    tracks:      list[AudioTrack]
    duration_ms: int | None = None   # required if any track has fade_out_ms > 0
    ramps:       list[VolumeRamp] = []
```

Pass to `MultiPanelCanvas(audio_mix=mix)` to add music/ambient to a canvas render.

**Raises `ValueError`** if `tracks` is empty or a ramp references an out-of-range track index.

---

### `MixError`

```python
class MixError(RuntimeError): ...
```

---

## videoflow.audio

### `AudioBeatMap`

```python
@dataclasses.dataclass
class AudioBeatMap:
    bpm:         float        # detected tempo in BPM
    beats:       list[int]    # timestamp (ms) of every beat
    downbeats:   list[int]    # timestamp (ms) of every downbeat (V1: every 4th beat, 4/4 assumed)
    phrases:     list[tuple[int, int]]   # (start_ms, end_ms) of each phrase (V1: 16 beats = 4 bars)
    energy:      list[float]  # normalised RMS energy (0.0–1.0) at each beat
    duration_ms: int          # total audio duration
```

#### Properties and methods

```python
@property
def beat_interval_ms(self) -> float:
    """Average interval between beats (60_000 / bpm)."""

def beats_in_range(self, start_ms: int, end_ms: int) -> list[int]:
    """Return all beat timestamps in [start_ms, end_ms)."""

def nearest_beat(self, ms: int, *, direction: str = "nearest") -> int:
    """
    Snap a time to the nearest beat.
    direction: "nearest" | "before" | "after"
    """

def save(self, path: str | Path) -> Path:
    """Save to JSON. Reload with load() to skip re-analysis."""

@classmethod
def load(cls, path: str | Path) -> AudioBeatMap:
    """Load a previously saved beat map."""
```

---

### `analyze_beats`

```python
def analyze_beats(
    input: str | Path,
    *,
    sr: int = 22050,
) -> AudioBeatMap
```

Analyse the beat structure of an audio or video file.

One call, one pass — the returned `AudioBeatMap` is the single source of truth
for all downstream consumers (beat-snap, beat-grid assembly, canvas sync).

**Args:**

- `input` — path to audio (`.mp3`, `.wav`, `.flac`, `.m4a`, …) or video file
- `sr` — sample rate (default 22050 Hz, librosa's standard for beat tracking)

**Raises:**

- `FileNotFoundError` — input file does not exist
- `BeatError` — librosa is not installed, or analysis failed

**Install librosa:** `pip install "videoflow[audio]"`

---

### `BeatError`

```python
class BeatError(RuntimeError): ...
```

---

## videoflow.analysis

### `Scene`

```python
@dataclasses.dataclass
class Scene:
    index:    int   # 1-based scene number
    start_ms: int   # scene start in milliseconds
    end_ms:   int   # scene end in milliseconds

    @property
    def duration_ms(self) -> int: ...
```

---

### `detect_scenes`

```python
def detect_scenes(
    input: str | Path,
    *,
    threshold: float | None = None,
    detector: str = "adaptive",
) -> list[Scene]
```

Detect scene boundaries in a video file. Wraps PySceneDetect.

**`detector` values:**

| Value | Algorithm | Default threshold | Best for |
| --- | --- | --- | --- |
| `"adaptive"` | Local adaptive | 3.0 | Mixed content, unknown footage |
| `"content"` | Frame difference | 27.0 | Hard cuts, edited video |
| `"threshold"` | Brightness | 12.0 | Fade-to-black transitions |

**Raises:** `FileNotFoundError`, `ValueError`, `SceneError`

**Install PySceneDetect:** `pip install "videoflow[scenes]"`

---

### `DETECTOR_INFO`

```python
DETECTOR_INFO: dict[str, DetectorInfo]
```

Metadata for each detector. Used by the CLI `detectors` command and by UIs
to populate threshold sliders with the correct range and guidance text.

---

### `SceneError`

```python
class SceneError(RuntimeError): ...
```
