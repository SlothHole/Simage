import os

from PIL import Image

from simage.ui import scanner


def test_scan_images(tmp_path):
    img1 = tmp_path / "one.jpg"
    img2 = tmp_path / "two.png"
    non_img = tmp_path / "note.txt"
    Image.new("RGB", (10, 10), color="red").save(img1)
    Image.new("RGB", (10, 10), color="blue").save(img2)
    non_img.write_text("ignore", encoding="utf-8")

    found = scanner.scan_images(os.fspath(tmp_path))
    found_names = {os.path.basename(p) for p in found}
    assert found_names == {"one.jpg", "two.png"}


def test_ensure_thumbnails_for_folder(tmp_path, monkeypatch):
    img1 = tmp_path / "one.jpg"
    img2 = tmp_path / "two.jpg"
    Image.new("RGB", (10, 10), color="red").save(img1)
    Image.new("RGB", (10, 10), color="blue").save(img2)

    thumb_dir = tmp_path / ".thumbs"
    monkeypatch.setattr(scanner, "THUMB_DIR", os.fspath(thumb_dir))

    thumbs = scanner.ensure_thumbnails_for_folder(os.fspath(tmp_path))
    assert len(thumbs) == 2
    assert all(os.path.exists(p) for p in thumbs)
