from pathlib import Path

import pytest

from simage.utils.paths import REPO_ROOT, repo_relative, resolve_repo_path, resolve_repo_relative


def test_resolve_repo_path_basic() -> None:
    readme = resolve_repo_path("README.md", must_exist=True)
    assert readme == REPO_ROOT / "README.md"


def test_resolve_repo_path_rejects_parent_segments() -> None:
    with pytest.raises(ValueError):
        resolve_repo_path("foo/../bar")


def test_resolve_repo_path_rejects_absolute_by_default(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        resolve_repo_path(str(tmp_path))


def test_resolve_repo_path_allows_absolute_when_enabled(tmp_path: Path) -> None:
    abs_path = resolve_repo_path(str(tmp_path), allow_absolute=True)
    assert abs_path == tmp_path.resolve()


def test_repo_relative_and_resolve_repo_relative() -> None:
    target = REPO_ROOT / "simage"
    rel = repo_relative(target)
    assert rel == Path("simage")
    rel2, abs2 = resolve_repo_relative("simage", must_exist=True)
    assert rel2 == Path("simage")
    assert abs2 == target
