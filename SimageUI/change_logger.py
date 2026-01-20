import os
import json

class ChangeLogger:
    """
    Logs unsaved changes to a file for recovery after crash or improper close.
    """
    LOG_PATH = os.path.join(os.path.dirname(__file__), "unsaved_changes.log")

    @staticmethod
    def log_change(change: dict):
        changes = ChangeLogger.load_changes()
        changes.append(change)
        with open(ChangeLogger.LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(changes, f)

    @staticmethod
    def load_changes():
        if not os.path.exists(ChangeLogger.LOG_PATH):
            return []
        try:
            with open(ChangeLogger.LOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @staticmethod
    def clear():
        if os.path.exists(ChangeLogger.LOG_PATH):
            os.remove(ChangeLogger.LOG_PATH)
