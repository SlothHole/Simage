from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _reject_parent_segments(path: Path) -> None:
    if ".." in path.parts:
        raise ValueError(f"Parent path segments are not allowed: {path}")


def resolve_repo_path(path_str: str, *, must_exist: bool = False, allow_absolute: bool = False) -> Path:
    if not path_str:
        raise ValueError("Path cannot be empty.")

    raw = Path(path_str)
    if raw.is_absolute():
        if not allow_absolute:
            raise ValueError(f"Absolute paths are not allowed: {path_str}")
        candidate = raw.resolve()
    else:
        _reject_parent_segments(raw)
        candidate = (REPO_ROOT / raw).resolve()

    if candidate != REPO_ROOT and REPO_ROOT not in candidate.parents:
        raise ValueError(f"Path escapes repository root: {path_str}")

    if must_exist and not candidate.exists():
        raise FileNotFoundError(candidate)

    return candidate


def repo_relative(path: Path) -> Path:
    return path.relative_to(REPO_ROOT)


def resolve_repo_relative(
    path_str: str,
    *,
    must_exist: bool = False,
    allow_absolute: bool = False,
) -> tuple[Path, Path]:
    absolute = resolve_repo_path(path_str, must_exist=must_exist, allow_absolute=allow_absolute)
    return repo_relative(absolute), absolute
