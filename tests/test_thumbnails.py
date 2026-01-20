import os
from simage.ui.thumbnails import ensure_thumbnail, thumbnail_path_for_source
from PIL import Image

def test_ensure_thumbnail_creates_file(tmp_path):
    img_path = tmp_path / "testimg.jpg"
    thumb_dir = tmp_path / ".thumbs"
    # Create a dummy image
    im = Image.new("RGB", (100, 100), color="red")
    im.save(img_path)
    thumb_path = ensure_thumbnail(os.fspath(img_path), thumb_dir=os.fspath(thumb_dir))
    assert os.path.exists(thumb_path)
    assert thumb_path.startswith(os.fspath(thumb_dir))

def test_ensure_thumbnail_returns_existing(tmp_path):
    img_path = tmp_path / "testimg2.jpg"
    thumb_dir = tmp_path / ".thumbs"
    im = Image.new("RGB", (100, 100), color="blue")
    im.save(img_path)
    thumb_path1 = ensure_thumbnail(os.fspath(img_path), thumb_dir=os.fspath(thumb_dir))
    thumb_path2 = ensure_thumbnail(os.fspath(img_path), thumb_dir=os.fspath(thumb_dir))
    assert thumb_path1 == thumb_path2
    assert os.path.exists(thumb_path2)

def test_thumbnail_path_matches_ensure_thumbnail(tmp_path):
    img_path = tmp_path / "testimg3.jpg"
    thumb_dir = tmp_path / ".thumbs"
    im = Image.new("RGB", (100, 100), color="green")
    im.save(img_path)
    thumb_path = ensure_thumbnail(os.fspath(img_path), thumb_dir=os.fspath(thumb_dir))
    expected = thumbnail_path_for_source(os.fspath(img_path), thumb_dir=os.fspath(thumb_dir))
    assert thumb_path == expected
