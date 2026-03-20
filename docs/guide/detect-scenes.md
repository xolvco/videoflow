# Detect scenes

Scene detection finds the cut points between scenes in a video file.
videoflow wraps [PySceneDetect](https://scenedetect.com/) and returns results as
JSON-ready `Scene` objects.

## Install

```bash
pip install "videoflow[scenes]"
```

This pulls in `scenedetect[opencv]`.

## Python

```python
from videoflow.analysis import detect_scenes

scenes = detect_scenes("clip.mp4")

for s in scenes:
    print(f"Scene {s.index}: {s.start_ms}ms → {s.end_ms}ms  ({s.duration_ms}ms)")
```

Output:

```
Scene 1:     0ms →  4200ms  (4200ms)
Scene 2:  4200ms →  9800ms  (5600ms)
Scene 3:  9800ms → 14100ms  (4300ms)
```

## CLI

```bash
videoflow detect-scenes clip.mp4
```

JSON output (default):

```json
{
  "input": "clip.mp4",
  "scene_count": 3,
  "scenes": [
    {"index": 1, "start_ms": 0,    "end_ms": 4200,  "duration_ms": 4200},
    {"index": 2, "start_ms": 4200, "end_ms": 9800,  "duration_ms": 5600},
    {"index": 3, "start_ms": 9800, "end_ms": 14100, "duration_ms": 4300}
  ]
}
```

Human-readable output:

```bash
videoflow detect-scenes clip.mp4 --human
```

```
input:       clip.mp4
scene_count: 3
  scene   1: 0.00s — 4.20s (4.20s)
  scene   2: 4.20s — 9.80s (5.60s)
  scene   3: 9.80s — 14.10s (4.30s)
```

## Options

| Option | Default | Description |
| --- | --- | --- |
| `--threshold` | `27.0` | Detection sensitivity. Lower = more scenes. |
| `--detector` | `content` | `content` (frame-difference cuts) or `threshold` (fade-to-black). |

### Choosing a threshold

- **Content detector** (`--detector content`): threshold is the frame-difference score.
  Default 27.0 works well for live-action. Lower values (15–20) detect more subtle cuts.
- **Threshold detector** (`--detector threshold`): threshold is a brightness level (0–255).
  Use this for fade-to-black transitions. Default is 12.

```bash
# More sensitive — detects subtle cuts
videoflow detect-scenes clip.mp4 --threshold 15.0

# Fade-to-black detection
videoflow detect-scenes clip.mp4 --detector threshold --threshold 12.0
```

## Pipeline integration

Scene boundaries feed downstream steps — use them as natural clip points:

```python
from videoflow.analysis import detect_scenes
from mediatools.video import clip

scenes = detect_scenes("long_video.mp4")

for s in scenes:
    clip(
        "long_video.mp4",
        f"scenes/scene_{s.index:03d}.mp4",
        start_ms=s.start_ms,
        end_ms=s.end_ms,
    )
```

Or pipe the JSON output to another tool:

```bash
videoflow detect-scenes clip.mp4 | jq '.scenes[] | select(.duration_ms > 3000)'
```
