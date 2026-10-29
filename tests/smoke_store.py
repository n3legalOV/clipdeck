import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.stats_store import StatsStore

store = StatsStore()
username = "store_test_user"
now = int(time.time())


def snapshot(followers, plays):
    return {
        "handle": "storetest",
        "nickname": "Test",
        "user": {"followers": followers, "following": 5, "likes": 900, "videos": 2},
        "items": [
            {"id": "111", "desc": "first", "createTime": now - 3600, "plays": plays, "likes": 1,
             "comments": 0, "shares": 0, "saves": 0, "duration": 15},
            {"id": "222", "desc": "second", "createTime": now - 7200, "plays": 5, "likes": 0,
             "comments": 0, "shares": 0, "saves": 0, "duration": 12},
        ],
    }


store.save_snapshot(username, snapshot(100, 10))
time.sleep(1.1)
store.save_snapshot(username, snapshot(130, 40))

accounts = store.latest_accounts()
assert accounts[username]["followers"] == 130, accounts
assert accounts[username]["d_followers"] == 30, accounts

videos = store.latest_videos(username)
assert len(videos) == 2, videos
first = [v for v in videos if v["video_id"] == "111"][0]
assert first["plays"] == 40 and first["d_plays"] == 30, first

with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, "out.csv")
    rows = store.export_csv(path, username)
    assert rows == 2, rows
    with open(path, encoding="utf-8-sig") as fh:
        content = fh.read()
    assert "store_test_user" in content and "40" in content, content[:300]

store.db.execute("DELETE FROM video_stats WHERE username = ?", (username,))
store.db.execute("DELETE FROM account_stats WHERE username = ?", (username,))
print("STORE OK")
