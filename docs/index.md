# videoflow

Composable video workflow pipeline.

Scene detection, smart clips, GPU upscaling, job monitoring — each step is a
standalone function that connects into a workflow.

## Quick start

```bash
pip install "videoflow[scenes]"
videoflow detect-scenes clip.mp4
```

## Pipeline overview

```mermaid
flowchart LR
    A([Source videos]) --> B[detect_scenes]
    B --> C[clip segments]
    C --> D[normalize]
    D --> E[upscale / crop]
    E --> F([reel.mp4])
```

## Features

- **Scene detection** — PySceneDetect wrapper, JSON output
- **Topaz script generation** — human-friendly inputs → ffmpeg commands *(coming soon)*
- **Job monitor** — live terminal table across multiple machines *(coming soon)*
- **Smart crop** — 4K → ultra-wide QHD with energy-histogram auto-crop *(coming soon)*
- **Real-ESRGAN** — free AI upscaling *(coming soon)*
- **Smart clips** — beat-map-driven highlight extraction *(coming soon)*
