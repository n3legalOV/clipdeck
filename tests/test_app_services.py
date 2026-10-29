import os

import pytest

from src.app.contracts import UploadOutcome
from src.app.services import ClipForgeService
from src.core.database import Database

SID = "a1b2c3d4e5f60718293a4b5c6d7e8f90"


def test_list_account_groups_counts_active_accounts(tmp_path):
    db = Database(tmp_path / "groups.db")
    db.save_account("one", "one.cookie", tag="music")
    db.save_account("two", "two.cookie", tag="music")
    db.save_account("off", "off.cookie", tag="music")
    db.set_account_status("off", "deleted")
    db.save_account("news", "news.cookie", tag="news")

    assert ClipForgeService(db).list_account_groups() == [("music", 2), ("news", 1)]


def test_import_accounts_is_idempotent_and_reports_added_updated_invalid(tmp_path):
    db = Database(tmp_path / "import.db")
    db.save_account("main", "old.cookie", tag="old")
    service = ClipForgeService(db)

    result = service.import_accounts(
        f"main\t{SID}\nnew\t{SID}\ninvalid\tno-session", default_tag="clips"
    )

    assert result.added == 1
    assert result.updated == 1
    assert result.invalid_lines == (3,)
    assert db.get_account_count() == 2
    assert db.get_account_by_username("main")[2] == "clips"


def test_import_accounts_matches_existing_username_case_insensitively(tmp_path):
    db = Database(tmp_path / "case.db")
    db.save_account("foo", "foo.cookie", tag="old")
    result = ClipForgeService(db).import_accounts(f"Foo\t{SID}", default_tag="clips")

    assert result.added == 0
    assert result.updated == 1
    assert db.get_account_count() == 1
    assert db.get_accounts()[0][1] == "foo"
    assert db.get_accounts()[0][4] == "clips"


def test_record_upload_preserves_caption(tmp_path):
    db = Database(tmp_path / "caption.db")
    ClipForgeService(db).record_upload(UploadOutcome("main", "clip.mp4", "ok", caption="#clip"))

    assert db.get_upload_log(1)[0][2] == "#clip"


def test_prepare_upload_validates_file_caption_and_group(tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")
    db = Database(tmp_path / "upload.db")
    db.save_account("main", "main.cookie", tag="clips")
    service = ClipForgeService(db)

    request = service.prepare_upload(str(video), "hello #clip", "clips")
    assert request.video_path == str(video)
    assert request.usernames == ("main",)
    assert request.caption == "hello #clip"

    with pytest.raises(ValueError, match="video"):
        service.prepare_upload(str(tmp_path / "missing.mp4"), "hello", "clips")
    with pytest.raises(ValueError, match="caption"):
        service.prepare_upload(str(video), "   ", "clips")
    with pytest.raises(ValueError, match="group"):
        service.prepare_upload(str(video), "hello", "empty")


def test_record_history_and_clear_delegate_to_database(tmp_path):
    db = Database(tmp_path / "history.db")
    service = ClipForgeService(db)
    service.record_upload(UploadOutcome("main", "clip.mp4", "ok"))

    history = service.recent_uploads()
    assert len(history) == 1
    assert history[0].username == "main"
    assert history[0].status == "ok"

    service.clear_upload_history()
    assert service.recent_uploads() == []


def test_diagnostics_returns_results_without_importing_ui(tmp_path):
    results = ClipForgeService(Database(tmp_path / "diag.db")).diagnostics()
    assert results
    assert all(result.name and result.status in {"ok", "warning", "error"} for result in results)
