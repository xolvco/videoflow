# Backlog

Features and improvements in priority order.
Items at the top are closest to ready. Items at the bottom are future/exploratory.

---

## Ready to build

### Audio beat analysis — librosa (V1)

`analyze_beats(input)` → `AudioBeatMap`. Wraps librosa for onset detection,
BPM estimation, beat grid, and downbeat tracking. Accepts audio or video files
(extracts audio automatically). Foundation for beat-snap and beat-grid assembly.

```python
from videoflow.audio import analyze_beats

beat_map = analyze_beats("track.mp3")
# beat_map.bpm, beat_map.beats, beat_map.downbeats, beat_map.phrases
```

---

### Simple split (media-tools)

`split(input, at_ms)` → two files. `split(input, [t1, t2, t3])` → N+1 files.
Stream copy — no re-encode. Lives in media-tools, same pattern as `clip()`.

---

### Beat-snap

Adjust a manual cut point to the nearest beat. Direction: `nearest`, `before`,
`after`. Works across tempo changes — the beat map knows every beat timestamp
regardless of BPM variation. Foundation for the UI snap-to-beat interaction.

---

### Beat-grid assembly

Assemble clips from multiple source videos, each cut to exactly N beats.
The beat map is the master timeline; clips breathe with the music.
See spec for full design.

---

## Near-term

### Speech-aware editing — filler/stammer detection (V1)

`analyze_speech(input)` → `SpeechAnalysis`. Uses Whisper (open-source) for
word-level timestamped transcription. Detects filler words ("uh", "um", "right?",
"you know"), stammers (repeated tokens), and long pauses (silence threshold).

```python
from videoflow.speech import analyze_speech, remove_fillers

speech = analyze_speech("interview.mp4")
clean_segments = remove_fillers("interview.mp4", speech, remove=["uh", "um", "right?"])
# → list of (start_ms, end_ms) segments — feed into concat_videos()
```

One audio pass → filler markers + stammer markers + pause markers + full transcript.
Filler cuts can be beat-snapped via `snap_to_beat()` so music doesn't stumble at the cut.
Configurable filler word list; `pad_ms` to soften cuts.

**Why it's near-term:** Every speaker recording benefits. Powers the customer lifecycle
agent (pre-sales recordings, onboarding tutorials, support videos). Descript solves this
as a product; videoflow makes it a composable pipeline step.

---

### Topaz Video AI script generator

Generate ffmpeg commands from human-friendly inputs (model, target res, GPU device).
Writes .ps1 + .sh scripts with progress reporting. RTX 4070 / `hevc_nvenc` primary.

---

### Multi-machine job monitor

Live terminal table of all jobs/ folder entries. Refreshes every 30s.
No server — coordination via shared folder (NAS, Dropbox, OneDrive).

---

### Smart crop — energy histogram

4K → ultra-wide QHD (3440×1440, 21:9). Auto-crop mode uses vertical spatial
energy to find the region of interest. No ML required for V1.

---

### Multi-panel canvas layout

Compose multiple video streams onto a single wider-than-4K canvas.
Panels run at independent speeds; inner panels use smart crop to show the
region of highest energy from the outer panel's source.

Standard layout: 4 panels — two outer portrait + two inner square — on a
4860×2160 canvas (fits four 9:16 portrait streams side by side).

```python
from videoflow.layout import MultiPanelCanvas, Panel

canvas = MultiPanelCanvas(
    panels=[
        Panel(input="tunnel.mp4",   speed=2.0, position="outer_left",  crop="full"),
        Panel(input="tunnel.mp4",   speed=2.0, position="inner_left",  crop="smart"),
        Panel(input="platform.mp4", speed=0.5, position="inner_right", crop="smart"),
        Panel(input="platform.mp4", speed=0.5, position="outer_right", crop="full"),
    ],
    canvas_size=(4860, 2160),
    beat_map=beat_map,
)
canvas.set_finale(clip=capitol_clip, beats=8, mode="full_width")
canvas.render(output="dc_metro.mp4")
```

Implementation: FFmpeg `filter_complex` — `setpts` for speed, smart crop for
inner panels, `hstack` or `overlay` to compose the canvas. The finale
`mode="full_width"` expands a single clip across all four panel positions.

The dance principle: panels are dancers, beat is the conductor.
Fast outer vs. slow outer = tension. Panels syncing on the reveal = release.

---

## Future / exploratory

### madmom — higher-accuracy beat tracking

**Why it's here:** librosa is good for most music, but its beat tracker can
drift on complex rhythms — live recordings with tempo fluctuation, jazz,
polyrhythm, or music where the downbeat is ambiguous. madmom uses a recurrent
neural network (RNN) trained specifically on beat tracking, and consistently
outperforms librosa on these edge cases. Its downbeat detection is also more
reliable, which matters for beat-grid assembly where a wrong downbeat shifts
every cut in a measure.

**Why it's not V1:** madmom requires compiled C extensions and is harder to
install than librosa. It also processes slower. For a first release and for
most pop/electronic music (the primary use case), librosa is sufficient.

**How to add it:** expose as an optional backend parameter on `analyze_beats()`:

```python
beat_map = analyze_beats("track.mp3", backend="madmom")
# Falls back to librosa if madmom not installed, with a warning
```

Install: `pip install "videoflow[madmom]"` — separate optional dep group.

---

### Real-ESRGAN integration

Free AI upscaler. Frame extract → process → reassemble.
Good 2× and 4× quality. Compare against Topaz on a test clip before committing.

---

### Drone / geospatial analysis

Anomaly detection, historical comparison, object detection (YOLO), temporal
progression. See spec for full design. Separate track — build after core
video production features are stable.

---

### DaVinci Resolve scripting

Python API wrapper for import, timeline, color grade, Smart Reframe, export.
Requires Resolve to be running — investigate headless options.

---

### 3D rendering integration

Script generation for Blender, Cinema 4D, Unreal Engine headless rendering.
GPU-aware: device selection, progress reporting, job manifest integration.
