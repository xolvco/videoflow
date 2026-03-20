# Multi-panel canvas

A **MultiPanelCanvas** composes multiple video streams side by side onto a single
wide canvas. The standard layout is four 9:16 portrait panels on a 4860×2160 frame —
wider than 4K — with each panel running at an independent speed.

The panel arrangement is the edit language. Fast outer panel + slow inner panel =
visual tension. All panels syncing on a finale = release. You don't cut on beat —
you let the panel sizes do it.

**FFmpeg required.** Install from [ffmpeg.org](https://ffmpeg.org).

---

## Step 1 — Install

No extra dependencies beyond FFmpeg:

```bash
pip install -e "."
```

---

## Step 2 — Build a basic four-panel canvas

The four positions are `outer_left`, `inner_left`, `inner_right`, `outer_right` —
left to right across the canvas.

```python
from videoflow.layout import MultiPanelCanvas, Panel

canvas = MultiPanelCanvas([
    Panel("tunnel.mp4",   speed=2.0, position="outer_left",  crop="full"),
    Panel("tunnel.mp4",   speed=2.0, position="inner_left",  crop="smart"),
    Panel("platform.mp4", speed=0.5, position="inner_right", crop="smart"),
    Panel("platform.mp4", speed=0.5, position="outer_right", crop="full"),
], canvas_size=(4860, 2160))

canvas.render("canvas.mp4")
```

The same source file can appear in multiple panels — FFmpeg handles this fine.
Here `tunnel.mp4` appears twice: once full (context) and once smart-cropped (close-up).

---

## Step 3 — Understand crop modes

**`crop="full"`** — scales the source to fill the panel. The full frame, scaled down.

**`crop="smart"`** — center-crops to 60% of the source before scaling.
The result is a zoomed-in view of the most active region of the frame.
Use this on inner panels alongside a full outer panel showing the same source.

```python
# Outer panels: full frame for context
Panel("footage.mp4", position="outer_left",  crop="full")
Panel("footage.mp4", position="outer_right", crop="full")

# Inner panels: zoomed-in close-up from the same source
Panel("footage.mp4", position="inner_left",  crop="smart")
Panel("footage.mp4", position="inner_right", crop="smart")
```

The visual tension between full and smart on the same source is what makes the
edit feel alive without any manual cutting.

---

## Step 4 — Set panel speeds

`speed` is a multiplier. 2.0 = twice as fast. 0.5 = half speed.

```python
Panel("clip.mp4", speed=2.0)   # fast-forward
Panel("clip.mp4", speed=0.5)   # slow motion
Panel("clip.mp4", speed=1.0)   # normal (default)
Panel("clip.mp4", speed=0.25)  # quarter speed
```

Outer panels fast + inner panels slow (or the reverse) creates a constant visual
tension that keeps the eye moving.

---

## Step 5 — Add a finale

The finale is a full-width clip pinned to the end. Every panel position collapses
into one image — the reveal moment.

```python
canvas = MultiPanelCanvas([...])
canvas.set_finale("capitol.mp4", beats=8)
canvas.render("dc_metro.mp4")
```

`beats=8` is informational for now — it tells the renderer how many beats the
finale holds (beat-sync transitions are a V2 feature).

```python
canvas.set_finale("product_reveal.mp4")   # beats defaults to 8
```

The finale clip is scaled to the full canvas size.

---

## Step 6 — Add audio

Pass an `AudioMix` to add music or ambient audio to the output:

```python
from videoflow.layout import MultiPanelCanvas, Panel
from videoflow.mix import AudioMix, AudioTrack, VolumeRamp

mix = AudioMix(
    tracks=[
        AudioTrack("music.mp3",   level=0.3),   # backing music, quiet under footage
        AudioTrack("ambient.mp3", level=0.8),   # ambient Metro sounds
    ],
    duration_ms=60_000,
    ramps=[
        # At 45s: swell music to full, fade ambient to silence
        VolumeRamp(track=0, at_ms=45_000, to_level=1.0, over_ms=2_000),
        VolumeRamp(track=1, at_ms=45_000, to_level=0.0, over_ms=1_000),
    ],
)

canvas = MultiPanelCanvas(
    panels=[...],
    audio_mix=mix,
)
canvas.render("dc_metro.mp4")
```

See the [audio guide](audio.md) for full documentation on `AudioMix`.

---

## Step 7 — Save to JSON, render later

```python
canvas.save("dc_metro_canvas.json")
```

The JSON:

```json
{
  "type": "canvas_edit",
  "version": "1.0",
  "canvas_size": [4860, 2160],
  "output": "",
  "panels": [
    {"input": "tunnel.mp4",   "speed": 2.0, "position": "outer_left",  "crop": "full"},
    {"input": "tunnel.mp4",   "speed": 2.0, "position": "inner_left",  "crop": "smart"},
    {"input": "platform.mp4", "speed": 0.5, "position": "inner_right", "crop": "smart"},
    {"input": "platform.mp4", "speed": 0.5, "position": "outer_right", "crop": "full"}
  ],
  "finale": {
    "input": "capitol.mp4",
    "beats": 8,
    "mode": "full_width"
  }
}
```

Set `"output"` in the JSON, then render with the CLI:

```bash
videoflow render dc_metro_canvas.json
```

Or override the output path:

```bash
videoflow render dc_metro_canvas.json --output dc_metro.mp4
```

---

## Step 8 — Use fewer panels

Two panels, one source each:

```python
canvas = MultiPanelCanvas([
    Panel("a.mp4", position="outer_left",  crop="full"),
    Panel("b.mp4", position="outer_right", crop="full"),
], canvas_size=(2430, 2160))
canvas.render("split_screen.mp4")
```

Panel widths are calculated as `canvas_width / num_panels` — so a 2430px canvas
with two panels gives 1215px per panel, same as the 4-panel layout.

---

## Canvas sizes

| Layout | Canvas size | Panel width |
| --- | --- | --- |
| 4-panel portrait (standard) | 4860 × 2160 | 1215 px |
| 2-panel 16:9 | 3840 × 2160 | 1920 px |
| 2-panel 16:9 (1080p) | 3840 × 1080 | 1920 px |
| 4-panel 1080p | 4320 × 1080 | 1080 px |

---

## Full example

```python
from videoflow.layout import MultiPanelCanvas, Panel
from videoflow.mix import AudioMix, AudioTrack, VolumeRamp

mix = AudioMix(
    tracks=[
        AudioTrack("music.mp3",   level=0.25, fade_in_ms=1000),
        AudioTrack("ambient.mp3", level=0.9),
    ],
    duration_ms=53_000,
    ramps=[
        VolumeRamp(track=0, at_ms=45_000, to_level=1.0, over_ms=2_000),
        VolumeRamp(track=1, at_ms=45_000, to_level=0.0, over_ms=1_500),
    ],
)

canvas = MultiPanelCanvas(
    panels=[
        Panel("tunnel.mp4",   speed=2.0, position="outer_left",  crop="full"),
        Panel("tunnel.mp4",   speed=2.0, position="inner_left",  crop="smart"),
        Panel("platform.mp4", speed=0.5, position="inner_right", crop="smart"),
        Panel("platform.mp4", speed=0.5, position="outer_right", crop="full"),
    ],
    canvas_size=(4860, 2160),
    audio_mix=mix,
)

canvas.set_finale("capitol.mp4", beats=8)
canvas.save("dc_metro_canvas.json")
canvas.render("dc_metro.mp4")
```

See [`examples/dc_metro.py`](../examples/dc_metro.py) for the full runnable version.
