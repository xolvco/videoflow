# videoflow

Composable video workflow pipeline.

Scene detection, smart clips, GPU upscaling, job monitoring — each step is a
standalone function that connects into a workflow. The job manifest is the
composition mechanism.

**Relationship to media-tools:** media-tools handles individual file operations
(probe, clip, extract, normalize, concat). videoflow orchestrates multi-step,
multi-machine, multi-tool workflows over collections of files.

## Install

```bash
pip install -e ".[scenes]"   # PySceneDetect wrapper
pip install -e ".[dev]"      # development tools
```

## Quick start

```python
from videoflow.analysis import detect_scenes

scenes = detect_scenes("clip.mp4")
for s in scenes:
    print(f"Scene {s.index}: {s.start_ms}ms → {s.end_ms}ms")
```

CLI:

```bash
videoflow detect-scenes clip.mp4
videoflow detect-scenes clip.mp4 --threshold 20.0 --detector content
```

## Features

- **Scene detection** — PySceneDetect wrapper, JSON output, job-manifest compatible
- More coming: Topaz script generation, job monitor, smart crop, Real-ESRGAN, smart clips
