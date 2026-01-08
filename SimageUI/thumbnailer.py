"""
Thumbnailer: Handles high-quality thumbnail generation and caching for SimageUI.
"""
import os
from PIL import Image


THUMB_SIZE = (256, 256)
THUMB_QUALITY = 90
# Central thumbnail directory at project root
THUMB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".thumbnails"))


def ensure_thumbnail(img_path: str, thumb_dir: str = THUMB_DIR) -> str:
    """
    Ensure a high-quality thumbnail exists for the given image in the central .thumbnails folder.
    Returns the thumbnail path.
    """
    if not os.path.exists(thumb_dir):
        os.makedirs(thumb_dir, exist_ok=True)
    # Use a unique name for the thumbnail to avoid collisions (e.g., hash or relpath)
    base = os.path.basename(img_path)
    # Optionally, use a hash or relpath for uniqueness
    import hashlib
    rel_path = os.path.relpath(img_path, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    hash_part = hashlib.md5(rel_path.encode("utf-8")).hexdigest()[:8]
    thumb_name = f"{os.path.splitext(base)[0]}_{hash_part}.jpg"
    thumb_path = os.path.join(thumb_dir, thumb_name)
    if os.path.exists(thumb_path):
        return thumb_path
    try:
        with Image.open(img_path) as im:
            im.thumbnail(THUMB_SIZE, Image.LANCZOS)
            im.save(thumb_path, "JPEG", quality=THUMB_QUALITY, optimize=True)
        return thumb_path
    except Exception:
        return ""
