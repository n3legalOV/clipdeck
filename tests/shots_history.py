"""Скриншот диалога истории публикаций (offscreen)."""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from src.core.database import Database
from src.core.paths import app_dir
from src.ui.styles import APP_STYLE
from src.ui.dialogs.upload_history import UploadHistoryDialog
from src.ui.pages.uploads import UploadsPage, VIDEO_EXTENSIONS

SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shots")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(APP_STYLE)

    with tempfile.TemporaryDirectory() as tmp:
        db = Database(os.path.join(tmp, "shots.db"))
        db.log_upload("main", "ok", video_path="C:/videos/kitchen.mp4", caption="Проверка")
        db.log_upload("second", "error", video_path="C:/videos/kitchen.mp4", caption="Проверка",
                      error="слишком частые публикации, попробуйте позже")
        db.log_upload("third", "ok", video_path="C:/videos/kitchen.mp4", caption="Проверка")
        db.log_upload("fourth", "error", video_path="C:/videos/kitchen.mp4", caption="Проверка",
                      error="сессия недействительна, войдите заново")

        dialog = UploadHistoryDialog(None, db)
        dialog.resize(820, 420)
        dialog.show()
        app.processEvents()
        os.makedirs(SHOTS, exist_ok=True)
        dialog.grab().save(os.path.join(SHOTS, "upload_history.png"))

        page = UploadsPage()
        page.resize(1120, 720)
        page.show()
        app.processEvents()
        page.grab().save(os.path.join(SHOTS, "uploads_dnd.png"))
        print("extensions:", VIDEO_EXTENSIONS, "accept drops:", page.acceptDrops())

    print("HISTORY SHOTS OK")


if __name__ == "__main__":
    main()
