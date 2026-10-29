import sqlite3
from pathlib import Path

from src.core.database import Database


def test_fresh_database_has_current_schema_version(tmp_path):
    db = Database(tmp_path / "fresh.db")
    assert db.schema_version() == db.SCHEMA_VERSION


def test_existing_records_survive_schema_initialization(tmp_path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY, username TEXT UNIQUE, cookies TEXT, proxy_id INTEGER, tag TEXT, status TEXT, videos_uploaded INTEGER, added_date TIMESTAMP)")
    conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("CREATE TABLE proxies (id INTEGER PRIMARY KEY, ip TEXT, port INTEGER, protocol TEXT)")
    conn.execute("CREATE TABLE videos (id INTEGER PRIMARY KEY, file_path TEXT NOT NULL)")
    conn.execute("CREATE TABLE schedules (id INTEGER PRIMARY KEY, video_id INTEGER, account_id INTEGER, scheduled_time TIMESTAMP)")
    conn.execute("CREATE TABLE upload_log (id INTEGER PRIMARY KEY, account_id INTEGER, username TEXT, video_path TEXT, caption TEXT, status TEXT, error TEXT, created_at TIMESTAMP)")
    conn.execute("INSERT INTO accounts(username, tag, status, videos_uploaded) VALUES ('legacy', 'old', 'active', 3)")
    conn.commit()
    conn.close()

    db = Database(path)
    assert db.get_account_by_username("legacy")[1] == "legacy"
    assert db.get_accounts()[0][6] == 3
    assert db.schema_version() == db.SCHEMA_VERSION


def test_corrupt_database_reports_actionable_error_and_preserves_original(tmp_path):
    path = tmp_path / "corrupt.db"
    original = b"not a sqlite database"
    path.write_bytes(original)

    try:
        Database(path)
    except RuntimeError as error:
        assert "corrupt" in str(error).lower()
        assert "backup" in str(error).lower()
    else:
        raise AssertionError("corrupt database must raise an actionable RuntimeError")

    assert path.read_bytes() == original
    assert list(tmp_path.glob("corrupt.before-migration-*.db.bak"))


def test_no_backup_is_created_when_schema_is_current(tmp_path):
    path = tmp_path / "current.db"
    first = Database(path)
    assert first.backup_before_migration() is None
    first.set("marker", "1")

    second = Database(path)
    assert second.backup_before_migration() is None
    assert not list(tmp_path.glob("current.before-migration-*.db.bak"))
    assert second.get("marker") is True


def test_backup_is_created_for_unversioned_existing_database(tmp_path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.commit()
    conn.close()

    db = Database(path)
    backup = db.backup_before_migration()
    assert backup is not None
    assert Path(backup).exists()
    assert Path(backup).read_bytes()
