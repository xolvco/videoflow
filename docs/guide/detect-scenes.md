# Detect scenes

Scene detection finds the cut points between scenes in a video file.
videoflow wraps [PySceneDetect](https://scenedetect.com/) and returns results as
JSON-ready `Scene` objects.

## Install

```bash
pip install "videoflow[scenes]"
```

## Quick start

```python
from videoflow.analysis import detect_scenes

scenes = detect_scenes("clip.mp4")   # adaptive detector, default threshold

for s in scenes:
    print(f"Scene {s.index}: {s.start_ms}ms → {s.end_ms}ms  ({s.duration_ms}ms)")
```

CLI:

```bash
videoflow detect-scenes clip.mp4
```

JSON output:

```json
{
  "input": "clip.mp4",
  "detector": "adaptive",
  "threshold": 3.0,
  "scene_count": 3,
  "scenes": [
    {"index": 1, "start_ms": 0,    "end_ms": 4200,  "duration_ms": 4200},
    {"index": 2, "start_ms": 4200, "end_ms": 9800,  "duration_ms": 5600},
    {"index": 3, "start_ms": 9800, "end_ms": 14100, "duration_ms": 4300}
  ]
}
```

Human-readable:

```bash
videoflow detect-scenes clip.mp4 --human
```

```text
input:       clip.mp4
detector:    adaptive — Adaptive (mixed content)
threshold:   3.0
scene_count: 3
  scene   1: 0.00s — 4.20s (4.20s)
  scene   2: 4.20s — 9.80s (5.60s)
  scene   3: 9.80s — 14.10s (4.30s)
```

---

## Choosing a detector

Three algorithms are available. If you're not sure, use the default (`adaptive`).

```bash
# See full guidance for all detectors
videoflow detectors --human
```

### Adaptive *(default)*

Adjusts its own sensitivity based on local activity in the video.
Works well when cut frequency varies — fast-cut action sequences and slow
talking-head sections in the same file.

```bash
videoflow detect-scenes clip.mp4 --detector adaptive
```

**Threshold scale:** 1 – 10, default **3.0**

| Slider position | Effect |
| --- | --- |
| Lower (1–2) | More scenes — catches subtle transitions and moderate camera moves |
| Default (3) | Good starting point for unknown content |
| Higher (5–10) | Fewer scenes — only obvious hard cuts |

**Best for:** long-form video, documentaries, vlogs, mixed content, anything you
don't know well.

**Tip:** Start at 3. If action shots are being split into multiple scenes, raise
toward 5–6. If cuts are being missed, lower toward 2.

---

### Content

Compares color, saturation, and brightness between consecutive frames.
When two frames look significantly different, that's a cut.

```bash
videoflow detect-scenes clip.mp4 --detector content
```

**Threshold scale:** 5 – 100, default **27.0**

| Slider position | Effect |
| --- | --- |
| Lower (10–20) | More scenes — catches subtle cuts and fast camera moves. May over-split on shaky footage. |
| Default (27) | Good for standard live-action edited video |
| Higher (40–100) | Fewer scenes — only major cuts like a new location or subject |

**Best for:** live action, edited video, music videos, interviews, sports.

**Not great for:** slow dissolves, fades to black, very shaky handheld footage.

**Tip:** Start at 27. Too many splits on action shots → raise toward 40.
Cuts being missed → lower toward 15.

---

### Threshold (fade to black)

Watches average frame brightness. When the screen goes dark enough, that's a
scene boundary.

```bash
videoflow detect-scenes clip.mp4 --detector threshold
```

**Threshold scale:** 1 – 255 (brightness level), default **12.0**

| Slider position | Effect |
| --- | --- |
| Lower (1–8) | Only near-black transitions |
| Default (12) | Standard fade-to-black |
| Higher (30+) | Triggers on any dark scene — may split night sequences |

**Best for:** documentary, film, broadcast TV, any content with intentional
fade-to-black transitions between scenes.

**Not great for:** hard cuts, dissolves, wipes — it simply won't see them.

**Tip:** Use this when your video fades to black between scenes. Leave at 12
unless your blacks aren't quite black (dark grey transfer artifacts) — then
raise it slightly.

---

## Setting the threshold

```bash
# More sensitive adaptive — catches subtle cuts
videoflow detect-scenes clip.mp4 --detector adaptive --threshold 2.0

# Less sensitive content — only major hard cuts
videoflow detect-scenes clip.mp4 --detector content --threshold 40.0

# Fade-to-black with slightly raised brightness cutoff
videoflow detect-scenes clip.mp4 --detector threshold --threshold 20.0
```

---

## Pipeline integration

Scene boundaries feed downstream steps. Use them as natural clip points:

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

Pipe JSON to another tool:

```bash
# Only keep scenes longer than 3 seconds
videoflow detect-scenes clip.mp4 | jq '.scenes[] | select(.duration_ms > 3000)'
```

Or feed into smart-clips selection (coming soon):

```python
from videoflow.analysis import detect_scenes
from videoflow.clips import select_best_scenes   # coming soon

scenes = detect_scenes("long_video.mp4")
best = select_best_scenes(scenes, source="long_video.mp4", max_count=10)
```
