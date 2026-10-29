import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import Database


def make_db(tmp):
    return Database(os.path.join(tmp, "test.db"))


def test_save_account_updates_existing():
    with tempfile.TemporaryDirectory() as tmp:
        db = make_db(tmp)
        db.save_account("main", "tiktok_session-main.cookie", tag="music")
        first = db.get_account_by_username("main")
        db.save_account("main", "tiktok_session-main.cookie", tag="clips")
        second = db.get_account_by_username("main")
        assert first[0] == second[0], "повторное сохранение не должно создавать дубль"
        assert second[2] == "clips"
        assert db.get_account_count() == 1


def test_accounts_by_tag_ignores_deleted():
    with tempfile.TemporaryDirectory() as tmp:
        db = make_db(tmp)
        db.save_account("a", "a.cookie", tag="music")
        db.save_account("b", "b.cookie", tag="music")
        db.set_account_status("b", "deleted")
        assert db.get_accounts_by_tag("music") == ["a"]


def test_upload_log_and_counter():
    with tempfile.TemporaryDirectory() as tmp:
        db = make_db(tmp)
        db.save_account("a", "a.cookie", tag="music")
        db.increment_account_uploads(["a"])
        db.log_upload("a", "ok", video_path="v.mp4", caption="тест")
        db.log_upload("a", "error", error="сессия недействительна")
        account = db.get_account_by_username("a")
        assert account is not None
        log = db.get_upload_log(10)
        assert len(log) == 2
        assert log[0][3] == "error" or log[1][3] == "error"
        assert db.get_accounts()[0][6] == 1


def test_wal_enabled():
    with tempfile.TemporaryDirectory() as tmp:
        db = make_db(tmp)
        mode = db.fetchone("PRAGMA journal_mode")
        assert mode[0].lower() == "wal"
