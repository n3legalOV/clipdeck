import sqlite3
from pathlib import Path
from threading import Lock
from src.core.paths import app_dir


class Database:
    def __init__(self):
        self.db_path = app_dir() / "data" / "tiktok.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self.lock = Lock()
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    cookies TEXT,
                    proxy_id INTEGER,
                    tag TEXT DEFAULT '---',
                    status TEXT DEFAULT 'active',
                    videos_uploaded INTEGER DEFAULT 0,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (proxy_id) REFERENCES proxies(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS proxies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    protocol TEXT NOT NULL,
                    login TEXT,
                    password TEXT,
                    status TEXT DEFAULT 'alive',
                    response_time REAL,
                    tag TEXT DEFAULT '---',
                    country TEXT DEFAULT 'UN',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ip, port)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    title TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    account_id INTEGER,
                    uploaded_date TIMESTAMP,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES accounts(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER NOT NULL,
                    account_id INTEGER NOT NULL,
                    scheduled_time TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (video_id) REFERENCES videos(id),
                    FOREIGN KEY (account_id) REFERENCES accounts(id)
                )
            """)

            default_settings = {
                "show_splash": True,
            }
            for key, value in default_settings.items():
                cursor.execute("SELECT COUNT(*) FROM settings WHERE key = ?", (key,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute(
                        "INSERT INTO settings (key, value) VALUES (?, ?)",
                        (key, '1' if value else '0')
                    )

            conn.commit()
            conn.close()

    def get(self, key, default=None):
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            conn.close()

            if row:
                value = row[0]
                if value == '1':
                    return True
                elif value == '0':
                    return False
                return value
            return default

    def set(self, key, value):
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            if isinstance(value, bool):
                value = '1' if value else '0'

            cursor.execute("""
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, str(value)))

            conn.commit()
            conn.close()

    def execute(self, query, params=None):
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            result = cursor.fetchall()
            conn.close()
            return result

    def fetchall(self, query, params=None):
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
            conn.close()
            return result

    def fetchone(self, query, params=None):
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchone()
            conn.close()
            return result

    def save_proxies(self, proxies: list) -> tuple:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT ip, port FROM proxies")
            existing_proxies = set((row[0], row[1]) for row in cursor.fetchall())

            saved_count = 0
            duplicates_count = 0

            for proxy in proxies:
                try:
                    key = (proxy.ip, proxy.port)
                    if key in existing_proxies:
                        duplicates_count += 1
                        continue

                    cursor.execute("""
                        INSERT OR IGNORE INTO proxies (ip, port, protocol, login, password, status, response_time, tag, country)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        proxy.ip,
                        proxy.port,
                        proxy.protocol,
                        proxy.login,
                        proxy.password,
                        proxy.status,
                        proxy.response_time,
                        getattr(proxy, 'tag', '---'),
                        getattr(proxy, 'country', 'UN')
                    ))
                    if cursor.rowcount > 0:
                        existing_proxies.add(key)
                        saved_count += 1
                    else:
                        duplicates_count += 1
                except Exception:
                    continue

            conn.commit()
            conn.close()
            return saved_count, duplicates_count

    def load_proxies(self) -> list:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, ip, port, protocol, login, password, status, response_time, tag, country
                FROM proxies
                ORDER BY created_at DESC
            """)
            result = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return result

    def get_proxy_count(self) -> int:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM proxies")
            count = cursor.fetchone()[0]
            conn.close()
            return count

    def delete_proxies(self, proxy_ids: list) -> int:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            placeholders = ",".join("?" * len(proxy_ids))
            cursor.execute(f"DELETE FROM proxies WHERE id IN ({placeholders})", proxy_ids)
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted_count

    def update_proxy_tags(self, proxy_ids: list, tag: str) -> int:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            placeholders = ",".join("?" * len(proxy_ids))
            cursor.execute(f"UPDATE proxies SET tag = ? WHERE id IN ({placeholders})", [tag] + proxy_ids)
            updated_count = cursor.rowcount
            conn.commit()
            conn.close()
            return updated_count

    def get_proxy_tags(self) -> list:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT tag FROM proxies WHERE tag != '---' ORDER BY tag")
            tags = [row[0] for row in cursor.fetchall()]
            conn.close()
            return tags

    def update_proxy_status(self, proxy_id: int, status: str, response_time: float, country: str, protocol: str) -> bool:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE proxies SET status = ?, response_time = ?, country = ?, protocol = ? WHERE id = ?",
                (status, response_time, country, protocol, proxy_id)
            )
            conn.commit()
            conn.close()
            return True

    def save_account(self, username: str, cookies_file: str = None, proxy_id: int = None, tag: str = "default") -> int:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO accounts (username, cookies, proxy_id, tag)
                VALUES (?, ?, ?, ?)
            """, (username, cookies_file, proxy_id, tag))
            account_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return account_id

    def get_accounts(self, limit: int = None, offset: int = 0) -> list:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            query = """
                SELECT a.id, a.username, a.cookies, a.proxy_id, a.tag, a.status,
                       a.videos_uploaded, a.added_date,
                       p.ip, p.port
                FROM accounts a
                LEFT JOIN proxies p ON a.proxy_id = p.id
                ORDER BY a.added_date DESC
            """
            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"
            cursor.execute(query)
            accounts = cursor.fetchall()
            conn.close()
            return accounts

    def get_account_count(self) -> int:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM accounts WHERE status = 'active'")
            count = cursor.fetchone()[0]
            conn.close()
            return count

    def delete_accounts(self, account_ids: list) -> int:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            placeholders = ",".join("?" * len(account_ids))
            cursor.execute(f"DELETE FROM accounts WHERE id IN ({placeholders})", account_ids)
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted_count

    def update_account_tags(self, account_ids: list, tag: str) -> int:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            placeholders = ",".join("?" * len(account_ids))
            cursor.execute(f"UPDATE accounts SET tag = ? WHERE id IN ({placeholders})", [tag] + account_ids)
            updated_count = cursor.rowcount
            conn.commit()
            conn.close()
            return updated_count

    def get_account_tags(self) -> list:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT tag FROM accounts WHERE tag != '---' ORDER BY tag")
            tags = [row[0] for row in cursor.fetchall()]
            conn.close()
            return tags

    def save_video(self, file_path: str, title: str = None, description: str = None) -> int:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO videos (file_path, title, description)
                VALUES (?, ?, ?)
            """, (file_path, title, description))
            video_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return video_id

    def get_videos(self) -> list:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.id, v.file_path, v.title, v.description, v.status,
                       v.account_id, v.uploaded_date, v.added_date,
                       a.username
                FROM videos v
                LEFT JOIN accounts a ON v.account_id = a.id
                ORDER BY v.added_date DESC
            """)
            videos = cursor.fetchall()
            conn.close()
            return videos

    def get_video_count(self) -> int:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM videos")
            count = cursor.fetchone()[0]
            conn.close()
            return count

    def delete_videos(self, video_ids: list) -> int:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            placeholders = ",".join("?" * len(video_ids))
            cursor.execute(f"DELETE FROM videos WHERE id IN ({placeholders})", video_ids)
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted_count

    def get_proxies_for_rotation(self, mode: str, value: str = None) -> list:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            if mode == "all":
                cursor.execute("SELECT * FROM proxies WHERE status = 'alive'")
            elif mode == "tag":
                cursor.execute("SELECT * FROM proxies WHERE tag = ? AND status = 'alive'", (value,))
            elif mode == "country":
                cursor.execute("SELECT * FROM proxies WHERE country = ? AND status = 'alive'", (value,))
            elif mode == "unused":
                cursor.execute("""
                    SELECT * FROM proxies
                    WHERE status = 'alive'
                    AND id NOT IN (SELECT DISTINCT proxy_id FROM accounts WHERE proxy_id IS NOT NULL)
                """)

            proxies = cursor.fetchall()
            conn.close()
            return proxies

    def remove_duplicate_proxies(self) -> int:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM proxies
                WHERE id NOT IN (
                    SELECT MAX(id)
                    FROM proxies
                    GROUP BY ip, port
                )
            """)
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted_count
