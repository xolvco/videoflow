# Audio — beat analysis and mixing

videoflow has two audio modules:

- **`videoflow.audio`** — analyse the beat structure of a track (BPM, beat grid, downbeats, phrases, energy)
- **`videoflow.mix`** — describe a multi-track audio mix with levels, fades, and volume ramps

They work independently. Use beat analysis to snap edit points to the music.
Use the mix to control what the viewer hears.

---

## Beat analysis

### Install

librosa is required:

```bash
pip install -e ".[audio]"
```

### Step 1 — Analyse a track

```python
from videoflow.audio import analyze_beats

beat_map = analyze_beats("track.mp3")
print(f"{beat_map.bpm:.1f} BPM")
print(f"{len(beat_map.beats)} beats over {beat_map.duration_ms / 1000:.1f}s")
```

CLI:

```bash
videoflow analyze-beats track.mp3 --human
```

```text
bpm:          124.0
duration:     185.3s
beats:        384
downbeats:    96
phrases:      24
beat interval: 484ms
```

### Step 2 — Save and reload

Beat analysis takes a few seconds. Save the result and reload it for every
subsequent render — no need to re-run librosa.

```python
beat_map = analyze_beats("track.mp3")
beat_map.save("track_beats.json")

# Later, in another script:
from videoflow.audio import AudioBeatMap

beat_map = AudioBeatMap.load("track_beats.json")
```

CLI with save:

```bash
videoflow analyze-beats track.mp3 --save track_beats.json
```

### Step 3 — Work with beats

```python
# All beat timestamps (milliseconds)
print(beat_map.beats[:8])
# [0, 484, 968, 1452, 1936, 2420, 2904, 3388]

# Downbeats (first beat of each bar, 4/4 assumed)
print(beat_map.downbeats[:4])
# [0, 1936, 3872, 5808]

# Musical phrases (16 beats = 4 bars each)
for start, end in beat_map.phrases[:3]:
    print(f"  {start/1000:.1f}s → {end/1000:.1f}s")

# Per-beat energy (0.0–1.0, normalised RMS)
# High energy = kick drum / snare hit
loud_beats = [b for b, e in zip(beat_map.beats, beat_map.energy) if e > 0.8]
print(f"{len(loud_beats)} high-energy beats")
```

### Step 4 — Snap an edit point to a beat

`nearest_beat()` snaps a time to the closest beat. Use `direction` to control
which side of the beat to snap to.

```python
# Snap 3500ms to the nearest beat
t = beat_map.nearest_beat(3_500)
print(f"Nearest beat: {t}ms")

# Always snap to the beat before the cut
t = beat_map.nearest_beat(3_500, direction="before")

# Always snap to the beat after the cut
t = beat_map.nearest_beat(3_500, direction="after")
```

### Step 5 — Find beats in a time window

```python
# Which beats fall in the first 10 seconds?
beats_in_intro = beat_map.beats_in_range(0, 10_000)
```

---

### What `analyze_beats` returns

| Field | Type | Description |
| --- | --- | --- |
| `bpm` | `float` | Detected tempo |
| `beats` | `list[int]` | Timestamp (ms) of every beat |
| `downbeats` | `list[int]` | Every 4th beat (V1: 4/4 assumed) |
| `phrases` | `list[tuple[int,int]]` | Groups of 16 beats (4 bars) |
| `energy` | `list[float]` | Normalised RMS at each beat (0.0–1.0) |
| `duration_ms` | `int` | Total audio duration |

---

## Audio mixing

`AudioMix` describes the audio track for a `MultiPanelCanvas` render.
It takes multiple sources, sets their base levels, adds fades, and can ramp
the volume of any track at any time.

No extra dependencies — mixing is implemented as FFmpeg filter expressions.

### Step 1 — One track, set the level

```python
from videoflow.mix import AudioMix, AudioTrack

mix = AudioMix(tracks=[
    AudioTrack("music.mp3", level=0.5),   # music at 50% volume
])
```

### Step 2 — Two tracks

```python
mix = AudioMix(tracks=[
    AudioTrack("music.mp3",   level=0.3),   # quiet backing track
    AudioTrack("ambient.mp3", level=0.8),   # ambient sound
])
```

Both tracks are mixed together. `normalize=0` is set on the FFmpeg `amix`
filter so the combined level doesn't drop.

### Step 3 — Add fade-in and fade-out

```python
mix = AudioMix(
    tracks=[
        AudioTrack("music.mp3", level=0.5, fade_in_ms=1000, fade_out_ms=2000),
    ],
    duration_ms=60_000,   # required for fade_out to be placed correctly
)
```

`fade_out_ms` needs `duration_ms` to know where to start the fade.

### Step 4 — Volume ramps

A `VolumeRamp` changes a track's volume at a specific moment. Volume transitions
linearly from the track's current level to `to_level` over `over_ms` milliseconds.

```python
from videoflow.mix import AudioMix, AudioTrack, VolumeRamp

mix = AudioMix(
    tracks=[
        AudioTrack("music.mp3",   level=0.25),  # music quiet during panels
        AudioTrack("ambient.mp3", level=0.9),   # ambient loud during panels
    ],
    ramps=[
        # At 45s: swell music to full volume over 2 seconds
        VolumeRamp(track=0, at_ms=45_000, to_level=1.0, over_ms=2_000),
        # At 45s: fade ambient to silence over 1 second
        VolumeRamp(track=1, at_ms=45_000, to_level=0.0, over_ms=1_000),
    ],
)
```

Multiple ramps on the same track are applied in time order.

### Step 5 — Attach to a canvas

```python
from videoflow.layout import MultiPanelCanvas, Panel

canvas = MultiPanelCanvas(
    panels=[...],
    audio_mix=mix,
)
canvas.render("output.mp4")
```

The audio track inputs are added to the FFmpeg command after the video panel
inputs. The filter chain handles level, fades, and ramps per track, then
combines them with `amix`.

### Step 6 — Save and reload

`AudioMix` serialises alongside `MultiPanelCanvas`:

```python
canvas.save("canvas.json")
# → the JSON includes an "audio" key with the full mix description

restored = MultiPanelCanvas.load("canvas.json")
# → audio_mix is reconstructed automatically
```

---

### `AudioTrack` fields

| Field | Default | Description |
| --- | --- | --- |
| `input` | — | Audio or video file (FFmpeg extracts audio) |
| `level` | `1.0` | Base volume (0.0–1.0) |
| `fade_in_ms` | `0` | Fade in from silence at track start |
| `fade_out_ms` | `0` | Fade out to silence (requires `duration_ms` on `AudioMix`) |

### `VolumeRamp` fields

| Field | Default | Description |
| --- | --- | --- |
| `track` | — | Index into `AudioMix.tracks` |
| `at_ms` | — | When the ramp begins (ms from video start) |
| `to_level` | — | Target level at ramp end (0.0–1.0) |
| `over_ms` | `500` | Ramp duration in milliseconds |

---

## Full example — beat analysis + mix

```python
from videoflow.audio import analyze_beats
from videoflow.layout import MultiPanelCanvas, Panel
from videoflow.mix import AudioMix, AudioTrack, VolumeRamp

# 1. Analyse the music once, save for reuse
beat_map = analyze_beats("music.mp3")
beat_map.save("music_beats.json")

print(f"BPM: {beat_map.bpm:.1f}")
print(f"Phrases: {len(beat_map.phrases)}")

# 2. Find where the final phrase starts — that's the finale cue
finale_cue_ms = beat_map.phrases[-1][0]
print(f"Finale at {finale_cue_ms / 1000:.1f}s")

# 3. Build the audio mix — quiet music under footage, swell on the finale
mix = AudioMix(
    tracks=[
        AudioTrack("music.mp3",   level=0.25, fade_in_ms=500),
        AudioTrack("ambient.mp3", level=0.85),
    ],
    duration_ms=beat_map.duration_ms,
    ramps=[
        VolumeRamp(track=0, at_ms=finale_cue_ms, to_level=1.0, over_ms=2_000),
        VolumeRamp(track=1, at_ms=finale_cue_ms, to_level=0.0, over_ms=1_000),
    ],
)

# 4. Build the canvas
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
canvas.render("dc_metro.mp4")
```

See [`examples/dc_metro.py`](../examples/dc_metro.py) and
[`examples/beat_analysis.py`](../examples/beat_analysis.py) for runnable versions.
