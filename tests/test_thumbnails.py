import os
import tempfile
from simage.ui.thumbnails import ensure_thumbnail, THUMB_DIR
from PIL import Image

def test_ensure_thumbnail_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        img_path = os.path.join(tmp, "testimg.jpg")
        # Create a dummy image
        im = Image.new("RGB", (100, 100), color="red")
        im.save(img_path)
        thumb_path = ensure_thumbnail(img_path)
        assert os.path.exists(thumb_path)
        assert thumb_path.startswith(THUMB_DIR)

def test_ensure_thumbnail_returns_existing():
    with tempfile.TemporaryDirectory() as tmp:
        img_path = os.path.join(tmp, "testimg2.jpg")
        im = Image.new("RGB", (100, 100), color="blue")
        im.save(img_path)
        thumb_path1 = ensure_thumbnail(img_path)
        thumb_path2 = ensure_thumbnail(img_path)
        assert thumb_path1 == thumb_path2
        assert os.path.exists(thumb_path2)
