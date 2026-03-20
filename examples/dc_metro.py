"""dc_metro.py — four-panel canvas with audio mix and finale reveal.

The DC Metro edit: two sources (tunnel footage + platform footage) composed
into a four-panel wider-than-4K canvas. Outer panels show the full frame;
inner panels show a zoomed-in smart-crop of the same source.
Tunnel runs at 2× speed; platform at half speed. The Capitol is the finale.

Demonstrates:
  - MultiPanelCanvas with four panels
  - crop="full" vs crop="smart"
  - Independent panel speeds
  - set_finale() — full-width reveal at the end
  - AudioMix — two tracks, base levels, volume ramps on the finale cue
  - Saving to canvas.json and rendering

Usage:
    python examples/dc_metro.py

Edit the file paths at the top to match your actual footage.
"""

from pathlib import Path

from videoflow.layout import MultiPanelCanvas, Panel
from videoflow.mix import AudioMix, AudioTrack, VolumeRamp

# ---------------------------------------------------------------------------
# File paths — edit these
# ---------------------------------------------------------------------------
TUNNEL_CLIP   = "footage/tunnel.mp4"      # tunnel / underground footage
PLATFORM_CLIP = "footage/platform.mp4"   # platform / station footage
FINALE_CLIP   = "footage/capitol.mp4"    # reveal clip (full-width at the end)
MUSIC_TRACK   = "audio/music.mp3"        # backing music
AMBIENT_TRACK = "audio/ambient.mp3"      # ambient Metro sounds

OUTPUT   = Path("output/dc_metro.mp4")
JSON_OUT = Path("output/dc_metro_canvas.json")

# Finale cue — when the music swells and ambient fades (milliseconds)
# If you have a beat map, use: beat_map.phrases[-1][0]
FINALE_CUE_MS = 45_000   # 45 seconds in

CANVAS_SIZE = (4860, 2160)   # four 9:16 portrait panels side by side

# ---------------------------------------------------------------------------

def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    # Audio mix: quiet music under footage → swell to full on the finale
    mix = AudioMix(
        tracks=[
            AudioTrack(MUSIC_TRACK,   level=0.25, fade_in_ms=1_000),
            AudioTrack(AMBIENT_TRACK, level=0.85),
        ],
        duration_ms=FINALE_CUE_MS + 10_000,   # rough total duration
        ramps=[
            # Music swells over 2 seconds
            VolumeRamp(track=0, at_ms=FINALE_CUE_MS, to_level=1.0, over_ms=2_000),
            # Ambient fades out over 1 second
            VolumeRamp(track=1, at_ms=FINALE_CUE_MS, to_level=0.0, over_ms=1_000),
        ],
    )

    canvas = MultiPanelCanvas(
        panels=[
            # Left side: tunnel footage
            Panel(TUNNEL_CLIP,   speed=2.0, position="outer_left",  crop="full"),
            Panel(TUNNEL_CLIP,   speed=2.0, position="inner_left",  crop="smart"),
            # Right side: platform footage
            Panel(PLATFORM_CLIP, speed=0.5, position="inner_right", crop="smart"),
            Panel(PLATFORM_CLIP, speed=0.5, position="outer_right", crop="full"),
        ],
        canvas_size=CANVAS_SIZE,
        audio_mix=mix,
    )

    # The Capitol: full-width reveal at the end
    canvas.set_finale(FINALE_CLIP, beats=8)

    # Save the edit description (inspect / edit / re-render without re-running)
    canvas.save(JSON_OUT)
    print(f"Saved canvas description → {JSON_OUT}")

    print(f"\nRendering {CANVAS_SIZE[0]}×{CANVAS_SIZE[1]} canvas → {OUTPUT}")
    print("  outer_left / inner_left  : tunnel  @ 2.0× (full / smart-crop)")
    print("  inner_right / outer_right: platform @ 0.5× (smart-crop / full)")
    print(f"  Finale cue at {FINALE_CUE_MS / 1000:.0f}s — music swells, ambient fades")

    result = canvas.render(OUTPUT, crf=18, preset="fast")
    print(f"\nDone: {result}")


if __name__ == "__main__":
    main()
