import os
import tempfile

from simage.ui.change_log import ChangeLogger

def test_change_logger_log_and_recover():
    # Use a temp log file
    orig_log = ChangeLogger.LOG_PATH
    with tempfile.TemporaryDirectory() as tmp:
        ChangeLogger.LOG_PATH = os.path.join(tmp, "unsaved_changes.log")
        # Log a change
        change = {"type": "tag", "img": "img1.png", "tags": ["cat"]}
        ChangeLogger.log_change(change)
        # Should be recoverable
        loaded = ChangeLogger.load_changes()
        assert loaded and loaded[0]["img"] == "img1.png"
        # Clear and check
        ChangeLogger.clear()
        assert ChangeLogger.load_changes() == []
    ChangeLogger.LOG_PATH = orig_log

def test_change_logger_handles_corrupt():
    orig_log = ChangeLogger.LOG_PATH
    with tempfile.TemporaryDirectory() as tmp:
        ChangeLogger.LOG_PATH = os.path.join(tmp, "unsaved_changes.log")
        with open(ChangeLogger.LOG_PATH, "w") as f:
            f.write("not json")
        assert ChangeLogger.load_changes() == []
    ChangeLogger.LOG_PATH = orig_log
