"""reel_from_folder.py — simplest reel: scan a folder and concat.

Usage:
    python examples/reel_from_folder.py <folder> <output.mp4> [gap_ms]

Example:
    python examples/reel_from_folder.py footage/ reel.mp4
    python examples/reel_from_folder.py footage/ reel.mp4 3000

Every .mp4 file in <folder> is included, sorted by filename.
Each clip gets a 2-second black gap (or the gap_ms you specify).
Chapter markers are embedded — one per clip, titled from the filename stem.
"""

import sys
from pathlib import Path

from videoflow.reel import Reel


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    folder = Path(sys.argv[1])
    output = Path(sys.argv[2])
    gap_ms = int(sys.argv[3]) if len(sys.argv) > 3 else 2000

    print(f"Scanning {folder} for *.mp4 files …")
    reel = Reel.from_folder(folder, gap_ms=gap_ms)

    print(f"Found {len(reel.clips)} clips:")
    for clip in reel.clips:
        print(f"  {clip.input}")

    print(f"\nRendering → {output}  (gap={gap_ms}ms)")
    result = reel.render(output)
    print(f"Done: {result}")


if __name__ == "__main__":
    main()
