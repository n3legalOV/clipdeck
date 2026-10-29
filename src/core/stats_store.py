import csv
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
        self.db.execute("CREATE INDEX IF NOT EXISTS ix_account_stats_lookup ON account_stats (username, fetched_at)")
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
            SELECT * FROM (
                SELECT a.username, a.handle, a.nickname, a.followers, a.following, a.likes, a.videos, a.fetched_at,
                       a.followers - LAG(a.followers) OVER (PARTITION BY a.username ORDER BY a.fetched_at, a.id) AS d_followers,
                       ROW_NUMBER() OVER (PARTITION BY a.username ORDER BY a.fetched_at DESC, a.id DESC) AS rn
                FROM account_stats a
            ) latest
            WHERE rn = 1
        """)
        return {r[0]: {"handle": r[1], "nickname": r[2], "followers": r[3], "following": r[4],
                       "likes": r[5], "videos": r[6], "fetched_at": r[7], "d_followers": r[8]} for r in rows}

    def latest_videos(self, username=None):
        rows = self.db.fetchall("""
            SELECT * FROM (
                SELECT v.username, v.video_id, v.caption, v.create_time, v.plays, v.likes, v.comments, v.shares,
                       v.saves, v.duration, v.fetched_at,
                       v.plays - LAG(v.plays) OVER w AS d_plays,
                       v.likes - LAG(v.likes) OVER w AS d_likes,
                       COUNT(*) OVER (PARTITION BY v.username, v.video_id) AS snapshots,
                       ROW_NUMBER() OVER (PARTITION BY v.username, v.video_id ORDER BY v.fetched_at DESC, v.id DESC) AS rn
                FROM video_stats v
                WINDOW w AS (PARTITION BY v.username, v.video_id ORDER BY v.fetched_at, v.id)
            ) latest
            WHERE rn = 1
            ORDER BY create_time DESC
        """)
        keys = ("username", "video_id", "caption", "create_time", "plays", "likes", "comments", "shares", "saves",
                "duration", "fetched_at", "d_plays", "d_likes", "snapshots")

        accounts = self.latest_accounts()
        videos = []
        for row in rows:
            item = dict(zip(keys, row))
            if username and item["username"] != username:
                continue
            # Ролик, которого не было в последней удачной выборке аккаунта,
            # считается удалённым/скрытым и в таблицу не попадает.
            last = accounts.get(item["username"], {}).get("fetched_at")
            if last and item["fetched_at"] < last:
                continue
            videos.append(item)
        return videos

    def totals(self, videos, accounts, username=None):
        def total(key):
            return sum(v[key] or 0 for v in videos)

        def delta(key):
            values = [v[key] for v in videos if v[key] is not None]
            return sum(values) if values else None

        follower_delta = [info["d_followers"] for name, info in accounts.items()
                          if username in (None, name) and info["d_followers"] is not None]
        return {
            "plays": total("plays"),
            "d_plays": delta("d_plays"),
            "likes": total("likes"),
            "d_likes": delta("d_likes"),
            "comments": total("comments"),
            "shares": total("shares"),
            "followers": sum(info["followers"] or 0 for name, info in accounts.items() if username in (None, name)),
            "d_followers": sum(follower_delta) if follower_delta else None,
        }

    def export_csv(self, path, username=None):
        """Выгружает последние значения по роликам в CSV (Excel-совместимо)."""
        videos = self.latest_videos(username)
        accounts = self.latest_accounts()
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["Аккаунт", "Ссылка", "Подпись", "Дата", "Просмотры", "Прирост", "Лайки",
                             "Комментарии", "Репосты", "Сохранения"])
            for v in videos:
                created = time.strftime("%Y-%m-%d %H:%M", time.localtime(v["create_time"])) if v["create_time"] else ""
                handle = accounts.get(v["username"], {}).get("handle")
                link = f"https://www.tiktok.com/@{handle}/video/{v['video_id']}" if handle else ""
                writer.writerow([v["username"], link, (v["caption"] or "").replace("\n", " "), created,
                                 v["plays"], v["d_plays"] if v["d_plays"] is not None else "",
                                 v["likes"], v["comments"], v["shares"], v["saves"]])
        return len(videos)

    def last_fetch(self):
        row = self.db.fetchall("SELECT MAX(fetched_at) FROM account_stats")
        return row[0][0] if row and row[0][0] else None

    def get_kv(self, key, default=None):
        rows = self.db.fetchall("SELECT value FROM kv WHERE key = ?", (key,))
        return rows[0][0] if rows else default

    def set_kv(self, key, value):
        self.db.execute("INSERT INTO kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                        (key, str(value)))
