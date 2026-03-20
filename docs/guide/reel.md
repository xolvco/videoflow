# Concat clips into a reel

A **Reel** joins multiple video files end-to-end with black-frame gaps between them
and embeds chapter markers so compatible players can jump ahead.
This is the "user-controlled ADHD" feature — the viewer decides what to skip.

**FFmpeg and ffprobe required.** Both ship together from [ffmpeg.org](https://ffmpeg.org).

---

## Step 1 — Install

No extra dependencies beyond FFmpeg:

```bash
pip install -e "."
```

---

## Step 2 — Simplest case: concat a folder

Put your `.mp4` files in a folder. One call does the rest:

```python
from videoflow.reel import Reel

reel = Reel.from_folder("videos/", gap_ms=2000)
reel.render("output.mp4")
```

CLI equivalent:

```bash
videoflow concat --from-folder videos/ --output output.mp4
```

`from_folder` loads all `.mp4` files sorted by filename, sets each clip's chapter
title to the filename stem, and inserts a 2-second black gap between every pair.

---

## Step 3 — Control the gap

`gap_ms` is in milliseconds. 2000 = 2 seconds, 0 = no gap (straight cut).

```python
reel = Reel.from_folder("videos/", gap_ms=3000)   # 3-second gaps
reel = Reel.from_folder("videos/", gap_ms=0)       # hard cuts, no gap
```

CLI:

```bash
videoflow concat --from-folder videos/ --output output.mp4 --gap 3000
```

---

## Step 4 — Name your chapters

Chapter titles show up in players that support chapter navigation
(VLC, QuickTime, syscplayer). Build the reel manually to set titles:

```python
from videoflow.reel import Reel, ReelClip

reel = Reel([
    ReelClip("intro.mp4",     title="Introduction"),
    ReelClip("segment_a.mp4", title="The Metro"),
    ReelClip("segment_b.mp4", title="The Platform"),
    ReelClip("outro.mp4",     title="The Capitol"),
], gap_ms=2000)

reel.render("dc_metro_reel.mp4")
```

If `title` is empty, the chapter title defaults to the filename stem.

---

## Step 5 — Trim clips

Use `start_ms` and `end_ms` to take only part of a source file:

```python
reel = Reel([
    ReelClip("raw_tunnel.mp4",   title="Entering the tube",  start_ms=12_000, end_ms=45_000),
    ReelClip("raw_platform.mp4", title="The platform",       start_ms=0,      end_ms=30_000),
    ReelClip("capitol.mp4",      title="The Capitol reveal"),   # full file
], gap_ms=2000)

reel.render("trimmed_reel.mp4")
```

When `end_ms` is set, `ffprobe` is not called — the duration is known from
`end_ms - start_ms`. When `end_ms` is `None`, ffprobe probes the file to get
the duration for the chapter end timestamp.

---

## Step 6 — Change canvas size

Default output is 1920×1080. Override for portrait, 4K, or any other size:

```python
reel = Reel.from_folder("clips/", canvas_size=(1080, 1920))  # portrait 9:16
reel = Reel.from_folder("clips/", canvas_size=(3840, 2160))  # 4K UHD
```

CLI:

```bash
videoflow concat --from-folder clips/ --output portrait.mp4 --canvas 1080x1920
```

All source clips are scaled to `canvas_size`. Aspect ratio is not preserved by
default — if your sources don't match the canvas, add padding or crop in a
pre-processing step.

---

## Step 7 — Use a non-MP4 pattern

```python
reel = Reel.from_folder("footage/", pattern="*.mov")
```

CLI:

```bash
videoflow concat --from-folder footage/ --output reel.mp4 --pattern "*.mov"
```

---

## Step 8 — Save to JSON, render later

The reel description is a plain JSON file. Save it, inspect it, edit it by hand,
then render it as a separate step:

```python
reel = Reel([
    ReelClip("a.mp4", title="Part one"),
    ReelClip("b.mp4", title="Part two"),
])
reel.save("my_reel.json")
```

The saved JSON:

```json
{
  "type": "reel",
  "version": "1.0",
  "gap_ms": 2000,
  "canvas_size": [1920, 1080],
  "frame_rate": 30,
  "sample_rate": 44100,
  "output": "",
  "clips": [
    {"input": "a.mp4", "title": "Part one", "start_ms": 0, "end_ms": null},
    {"input": "b.mp4", "title": "Part two", "start_ms": 0, "end_ms": null}
  ]
}
```

Set the `"output"` field in the JSON to skip passing `--output` on the command line:

```json
"output": "my_reel.mp4"
```

Then render:

```bash
videoflow concat my_reel.json
```

Or from Python:

```python
from videoflow.reel import Reel

reel = Reel.load("my_reel.json")
reel.render("my_reel.mp4")
```

---

## Step 9 — Control encoding quality

```python
reel.render("output.mp4", crf=23, preset="medium")
```

| Parameter | Default | Notes |
| --- | --- | --- |
| `crf` | `18` | H.264 quality. Lower = better. 18 is near-lossless; 23 is default H.264. |
| `preset` | `"fast"` | Encoding speed. `ultrafast` … `veryslow`. Slower = smaller file. |

CLI:

```bash
videoflow concat reel.json --output output.mp4 --crf 23 --preset medium
```

---

## How chapters work

Each clip becomes one chapter in the output. The chapter start and end times are
calculated from clip duration + gap:

```
Clip 0: START=0        END=10000     title=Introduction
  gap: 2000ms
Clip 1: START=12000    END=20000     title=The Metro
  gap: 2000ms
Clip 2: START=22000    END=27000     title=The Capitol
```

The chapter metadata is embedded as an `ffmetadata` file and passed to FFmpeg via
`-map_metadata`. Players that read MP4 chapter atoms (VLC, QuickTime, most mobile
players) will show a chapter list.

---

## Full example

```python
from videoflow.reel import Reel, ReelClip

reel = Reel(
    clips=[
        ReelClip("footage/tunnel_enter.mp4", title="Entering the tube",
                 start_ms=5_000, end_ms=40_000),
        ReelClip("footage/tunnel_mid.mp4",   title="In the tube",
                 start_ms=0, end_ms=30_000),
        ReelClip("footage/platform.mp4",     title="The platform"),
        ReelClip("footage/capitol.mp4",      title="The Capitol reveal"),
    ],
    gap_ms=2000,
    canvas_size=(1920, 1080),
)

reel.save("dc_metro_reel.json")   # save for later editing
reel.render("dc_metro_reel.mp4")
```

See [`examples/reel_with_chapters.py`](../examples/reel_with_chapters.py) for the
full runnable version.
