# API Reference

## videoflow.analysis

### `Scene`

```python
@dataclasses.dataclass
class Scene:
    index: int        # 1-based scene number
    start_ms: int     # scene start in milliseconds
    end_ms: int       # scene end in milliseconds

    @property
    def duration_ms(self) -> int: ...
```

### `detect_scenes`

```python
def detect_scenes(
    input: str | Path,
    *,
    threshold: float = 27.0,
    detector: str = "content",
) -> list[Scene]
```

Detect scene boundaries in a video file.

**Args:**

- `input` — path to the video file
- `threshold` — detection sensitivity; lower = more scenes. Default 27.0 for `content` detector.
- `detector` — `"content"` (frame-difference cuts) or `"threshold"` (fade-to-black)

**Returns:** list of `Scene` objects ordered by start time.

**Raises:**

- `FileNotFoundError` — input file does not exist
- `ValueError` — invalid `detector` value
- `SceneError` — PySceneDetect not installed, or detection failed

### `SceneError`

```python
class SceneError(RuntimeError): ...
```

Raised when PySceneDetect is not installed or when detection fails.
Install PySceneDetect with: `pip install scenedetect[opencv]`
