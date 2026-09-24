import time

from src.core.database import Database

KEEP_SECONDS = 30 * 24 * 3600


class StatsStore:
    def __init__(self, db=None):
        self.db = db or Database()
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS account_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                handle TEXT,
                nickname TEXT,
                followers INTEGER, following INTEGER, likes INTEGER, videos INTEGER,
                fetched_at INTEGER NOT NULL
            )""")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS video_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                video_id TEXT NOT NULL,
                caption TEXT,
                create_time INTEGER,
                plays INTEGER, likes INTEGER, comments INTEGER, shares INTEGER, saves INTEGER,
                duration INTEGER,
                fetched_at INTEGER NOT NULL
            )""")
        self.db.execute("CREATE INDEX IF NOT EXISTS ix_video_stats_lookup ON video_stats (username, video_id, fetched_at)")
        self.db.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)")

    def save_snapshot(self, username, data):
        now = int(time.time())
        user = data.get("user", {})
        self.db.execute(
            "INSERT INTO account_stats (username, handle, nickname, followers, following, likes, videos, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (username, data.get("handle"), data.get("nickname"), user.get("followers", 0),
             user.get("following", 0), user.get("likes", 0), user.get("videos", 0), now),
        )
        for item in data.get("items", []):
            self.db.execute(
                "INSERT INTO video_stats (username, video_id, caption, create_time, plays, likes, comments, "
                "shares, saves, duration, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (username, item["id"], item.get("desc", ""), item.get("createTime", 0), item.get("plays", 0),
                 item.get("likes", 0), item.get("comments", 0), item.get("shares", 0), item.get("saves", 0),
                 item.get("duration", 0), now),
            )
        cutoff = now - KEEP_SECONDS
        self.db.execute("DELETE FROM video_stats WHERE fetched_at < ?", (cutoff,))
        self.db.execute("DELETE FROM account_stats WHERE fetched_at < ?", (cutoff,))

    def latest_accounts(self):
        rows = self.db.fetchall("""
            SELECT a.username, a.handle, a.nickname, a.followers, a.following, a.likes, a.videos, a.fetched_at
            FROM account_stats a
            WHERE a.id = (SELECT MAX(id) FROM account_stats b WHERE b.username = a.username)
        """)
        return {r[0]: {"handle": r[1], "nickname": r[2], "followers": r[3], "following": r[4],
                       "likes": r[5], "videos": r[6], "fetched_at": r[7]} for r in rows}

    def latest_videos(self):
        rows = self.db.fetchall("""
            SELECT * FROM (
                SELECT username, video_id, caption, create_time, plays, likes, comments, shares, saves, duration,
                       fetched_at,
                       plays - LAG(plays) OVER w AS d_plays,
                       likes - LAG(likes) OVER w AS d_likes,
                       COUNT(*) OVER (PARTITION BY username, video_id) AS snapshots,
                       ROW_NUMBER() OVER (PARTITION BY username, video_id ORDER BY fetched_at DESC, id DESC) AS rn
                FROM video_stats
                WINDOW w AS (PARTITION BY username, video_id ORDER BY fetched_at, id)
            ) v
            WHERE rn = 1
              AND fetched_at = (SELECT MAX(fetched_at) FROM account_stats a WHERE a.username = v.username)
            ORDER BY create_time DESC
        """)
        keys = ("username", "video_id", "caption", "create_time", "plays", "likes", "comments", "shares", "saves",
                "duration", "fetched_at", "d_plays", "d_likes", "snapshots")
        return [dict(zip(keys, row)) for row in rows]

    def last_fetch(self):
        row = self.db.fetchall("SELECT MAX(fetched_at) FROM account_stats")
        return row[0][0] if row and row[0][0] else None

    def get_kv(self, key, default=None):
        rows = self.db.fetchall("SELECT value FROM kv WHERE key = ?", (key,))
        return rows[0][0] if rows else default

    def set_kv(self, key, value):
        self.db.execute("INSERT INTO kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                        (key, str(value)))
