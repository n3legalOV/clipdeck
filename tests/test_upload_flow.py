import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PyQt6.QtWidgets import QApplication

from src.app.contracts import VideoValidation
from src.app.services import ClipForgeService, validate_video_file
from src.core.database import Database
from src.ui.pages.uploads import UploadsPage


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_validate_video_file_reports_missing_and_unsupported():
    missing = validate_video_file("C:/missing/clip.mp4")
    assert missing == VideoValidation(False, "missing", "video file not found")

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "clip.avi")
        open(path, "wb").close()
        result = validate_video_file(path)
        assert result.valid is False
        assert result.code == "unsupported"


def test_validate_video_file_accepts_non_empty_supported_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "clip.MP4")
        with open(path, "wb") as stream:
            stream.write(b"video")
        result = validate_video_file(path)
        assert result.valid is True
        assert result.code == "ok"
        assert result.size == 5


def test_partial_results_are_recorded_and_retry_list_is_preserved(qapp):
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(os.path.join(tmp, "clipforge.db"))
        db.save_account("one", "one.cookie", tag="team")
        db.save_account("two", "two.cookie", tag="team")
        service = ClipForgeService(db)
        page = UploadsPage(service)
        page.video_path = os.path.join(tmp, "clip.mp4")
        with open(page.video_path, "wb") as stream:
            stream.write(b"video")
        page.caption.setPlainText("#test")
        page.group.setCurrentIndex(0)

        page._account_done("one", True, "")
        page._account_done("two", False, "quota")
        page._finished(1, 2)

        assert page.failed == ["two"]
        assert not page.btn_retry.isHidden()
        history = service.recent_uploads()
        assert [item.status for item in reversed(history)] == ["ok", "error"]
        assert history[0].error == "quota"


def test_stop_after_success_keeps_unattempted_accounts_for_retry(qapp):
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(os.path.join(tmp, "stop.db"))
        service = ClipForgeService(db)
        page = UploadsPage(service)
        page.video_path = os.path.join(tmp, "clip.mp4")
        with open(page.video_path, "wb") as stream:
            stream.write(b"video")
        page.caption.setPlainText("#test")
        page.last_job = (page.video_path, "#test")
        page.thread = type("RunningThread", (), {"deleteLater": lambda self: None})()
        page._active_usernames = ["one", "two", "three"]
        page._account_done("one", True, "")
        page._finished(1, 3, stopped=True)
        page.thread = None
        page._thread_closed()

        assert page.failed == ["two", "three"]
        assert page.last_job == (page.video_path, "#test")
        assert not page.btn_retry.isHidden()


def test_history_dialog_uses_service_and_clears_through_it(qapp):
    from src.ui.dialogs.upload_history import UploadHistoryDialog

    with tempfile.TemporaryDirectory() as tmp:
        db = Database(os.path.join(tmp, "clipforge.db"))
        service = ClipForgeService(db)
        db.log_upload("one", "error", video_path="clip.mp4", error="bad")
        dialog = UploadHistoryDialog(service=service)
        assert dialog.windowTitle() == "ClipForge · История публикаций"
        assert dialog.table.rowCount() == 1
        assert dialog.table.item(0, 3).text() == "ошибка"
        service.clear_upload_history()
        dialog.reload()
        assert dialog.table.rowCount() == 0
