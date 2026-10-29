"""ClipForge publication and history screenshots."""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from src.app.services import ClipForgeService
from src.core.database import Database
from src.ui.dialogs.upload_history import UploadHistoryDialog
from src.ui.pages.uploads import UploadsPage
from src.ui.styles import APP_STYLE

SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shots")


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(APP_STYLE)
    os.makedirs(SHOTS, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        db = Database(os.path.join(tmp, "shots.db"))
        db.save_account("demo", "demo.cookie", tag="launch")
        service = ClipForgeService(db)
        page = UploadsPage(service)
        page.resize(1120, 720)
        page.show()
        app.processEvents()
        page.grab().save(os.path.join(SHOTS, "clipforge_publication.png"))

        db.log_upload("demo", "error", video_path="demo.mp4", error="пример ошибки")
        dialog = UploadHistoryDialog(service=service)
        dialog.resize(820, 420)
        dialog.show()
        app.processEvents()
        dialog.grab().save(os.path.join(SHOTS, "clipforge_history.png"))

    print("CLIPFORGE SHOTS OK", page.acceptDrops(), dialog.table.rowCount())


if __name__ == "__main__":
    main()
