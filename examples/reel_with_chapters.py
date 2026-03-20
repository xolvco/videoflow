"""reel_with_chapters.py — named chapters, trim, custom gaps.

Demonstrates:
  - Manually specifying clips with chapter titles
  - Trimming clips to a specific time window (start_ms / end_ms)
  - Saving the reel description to JSON
  - Rendering

Usage:
    python examples/reel_with_chapters.py

Edit the CLIPS list below to match your actual files.
"""

from pathlib import Path

from videoflow.reel import Reel, ReelClip

# ---------------------------------------------------------------------------
# Edit this list to match your files
# ---------------------------------------------------------------------------
CLIPS = [
    # Full file — title from filename stem if title="" (try it)
    ReelClip("footage/intro.mp4",       title="Introduction"),

    # Trim: only the 10s–45s window
    ReelClip("footage/tunnel.mp4",      title="Entering the tube",
             start_ms=10_000, end_ms=45_000),

    # Trim: start at 5s, run to the end of the file
    ReelClip("footage/platform.mp4",    title="The platform",
             start_ms=5_000),

    # Full file
    ReelClip("footage/capitol.mp4",     title="The Capitol reveal"),
]

OUTPUT   = Path("output/reel_with_chapters.mp4")
JSON_OUT = Path("output/reel_with_chapters.json")
GAP_MS   = 2000    # 2-second black gap between clips

# ---------------------------------------------------------------------------

def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    reel = Reel(CLIPS, gap_ms=GAP_MS)

    # Save the description first so you can inspect / re-use it
    reel.save(JSON_OUT)
    print(f"Saved reel description → {JSON_OUT}")

    # Show what will be rendered
    print(f"\n{len(reel.clips)} clips, {GAP_MS}ms gaps:")
    for c in reel.clips:
        trim = ""
        if c.start_ms or c.end_ms:
            trim = f"  [{c.start_ms}ms → {c.end_ms or 'end'}]"
        print(f"  [{c.title}] {c.input}{trim}")

    print(f"\nRendering → {OUTPUT}")
    result = reel.render(OUTPUT)
    print(f"Done: {result}")


if __name__ == "__main__":
    main()
