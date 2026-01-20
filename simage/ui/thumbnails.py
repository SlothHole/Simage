"""
Thumbnailer: Handles high-quality thumbnail generation and caching for Simage UI.
"""
import hashlib
import os
from PIL import Image

from simage.utils.paths import resolve_repo_path

THUMB_SIZE = (256, 256)
THUMB_QUALITY = 90
# Central thumbnail directory at repo root
THUMB_DIR = str(resolve_repo_path(".thumbnails", must_exist=False, allow_absolute=False))

def thumbnail_path_for_source(img_path: str, thumb_dir: str = THUMB_DIR) -> str:
    base = os.path.basename(img_path)
    repo_root = str(resolve_repo_path(".", allow_absolute=False))
    rel_path = os.path.relpath(img_path, repo_root)
    hash_part = hashlib.md5(rel_path.encode("utf-8")).hexdigest()[:8]
    thumb_name = f"{os.path.splitext(base)[0]}_{hash_part}.jpg"
    return os.path.join(thumb_dir, thumb_name)


def ensure_thumbnail(img_path: str, thumb_dir: str = THUMB_DIR) -> str:
    """
    Ensure a high-quality thumbnail exists for the given image in the central .thumbnails folder.
    Returns the thumbnail path.
    """
    if not os.path.exists(thumb_dir):
        os.makedirs(thumb_dir, exist_ok=True)
    thumb_path = thumbnail_path_for_source(img_path, thumb_dir)
    if os.path.exists(thumb_path):
        return thumb_path
    try:
        with Image.open(img_path) as im:
            im.thumbnail(THUMB_SIZE, Image.LANCZOS)
            im.save(thumb_path, "JPEG", quality=THUMB_QUALITY, optimize=True)
        return thumb_path
    except Exception:
        return ""
