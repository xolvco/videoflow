# videoflow

Composable video workflow pipeline for Python.

Concat videos with chapter markers, compose multi-panel canvases, analyse beats —
each step is a standalone function that connects into a workflow.
Connect steps with plain Python or a JSON edit file.

**FFmpeg required.** Install from [ffmpeg.org](https://ffmpeg.org) and make sure `ffmpeg` is on your PATH.

---

## Install

```bash
pip install -e "."                        # core (no extra deps, ffmpeg provides the engine)
pip install -e ".[scenes]"                # + scene detection  (PySceneDetect)
pip install -e ".[audio]"                 # + beat analysis    (librosa)
pip install -e ".[scenes,audio,dev]"      # everything + dev tools
```

---

## What's in the box

| Module | What it does |
| --- | --- |
| `videoflow.reel` | Concat clips from a folder or list, 2-second gaps, chapter markers |
| `videoflow.layout` | Four-panel canvas, independent speeds, smart crop, finale reveal |
| `videoflow.mix` | Multi-track audio — levels, fades, linear volume ramps |
| `videoflow.audio` | Beat analysis — BPM, beat grid, downbeats, phrases, energy |
| `videoflow.analysis` | Scene boundary detection — adaptive, content, threshold |

---

## Quick start — concat a folder of clips

Wire together every `.mp4` in a folder, 2-second black gaps between them, chapter
markers embedded for player navigation:

```python
from videoflow.reel import Reel

reel = Reel.from_folder("videos/", gap_ms=2000)
reel.render("output.mp4")
```

CLI:

```bash
videoflow concat --from-folder videos/ --output output.mp4
videoflow concat --from-folder videos/ --output output.mp4 --gap 3000
```

---

## Quick start — four-panel canvas

```python
from videoflow.layout import MultiPanelCanvas, Panel

canvas = MultiPanelCanvas([
    Panel("tunnel.mp4",   speed=2.0, position="outer_left",  crop="full"),
    Panel("tunnel.mp4",   speed=2.0, position="inner_left",  crop="smart"),
    Panel("platform.mp4", speed=0.5, position="inner_right", crop="smart"),
    Panel("platform.mp4", speed=0.5, position="outer_right", crop="full"),
], canvas_size=(4860, 2160))

canvas.set_finale("capitol.mp4", beats=8)
canvas.render("dc_metro.mp4")
```

---

## Quick start — beat analysis

```python
from videoflow.audio import analyze_beats

beat_map = analyze_beats("track.mp3")
print(f"{beat_map.bpm:.1f} BPM — {len(beat_map.beats)} beats")
beat_map.save("track_beats.json")   # reuse without re-analysing
```

CLI:

```bash
videoflow analyze-beats track.mp3 --human
videoflow analyze-beats track.mp3 --save track_beats.json
```

---

## CLI reference

```bash
# Concat clips
videoflow concat --from-folder DIR/ --output reel.mp4 [--gap MS] [--canvas WxH]
videoflow concat reel.json           --output reel.mp4

# Render a canvas edit file
videoflow render canvas.json         --output canvas.mp4

# Beat analysis
videoflow analyze-beats AUDIO [--beats] [--save FILE] [--human]

# Scene detection
videoflow detect-scenes VIDEO [--detector adaptive|content|threshold] [--threshold N] [--human]
videoflow detectors --human   # guidance on choosing a detector and setting the threshold
```

Every command outputs JSON by default. Add `--human` for readable output.

---

## JSON edit files

The reel and canvas each have a JSON description. Build it in code, save it,
hand-edit it, render it. The JSON is the edit — the Python API fills it in.

```bash
# Save an edit description
python -c "
from videoflow.reel import Reel, ReelClip
reel = Reel([
    ReelClip('intro.mp4',  title='Introduction'),
    ReelClip('main.mp4',   title='Main segment'),
    ReelClip('outro.mp4',  title='Outro'),
])
reel.save('my_reel.json')
"

# Later — render it
videoflow concat my_reel.json --output my_reel.mp4
```

---

## Examples

See [`examples/`](examples/) for complete scripts:

| File | What it demonstrates |
| --- | --- |
| [`reel_from_folder.py`](examples/reel_from_folder.py) | One-liner folder concat |
| [`reel_with_chapters.py`](examples/reel_with_chapters.py) | Named chapters, trim, custom gaps |
| [`dc_metro.py`](examples/dc_metro.py) | Four-panel canvas + audio mix + finale |
| [`beat_analysis.py`](examples/beat_analysis.py) | Analyse beats, save, reload, snap to beat |

---

## Docs

Guides and API reference:

```bash
pip install mkdocs-material
mkdocs serve       # → http://127.0.0.1:8000
```

---

## Tests

```bash
pytest tests/           # 225 tests
pytest tests/ -q        # quiet
```
