from __future__ import annotations

import sys
from pathlib import Path


def ensure_videoedit_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    candidate = repo_root.parent / "videoedit" / "src"
    candidate_text = str(candidate)
    if candidate.exists() and candidate_text not in sys.path:
        sys.path.insert(0, candidate_text)
