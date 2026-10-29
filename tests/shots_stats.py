import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.app import Application

application = Application()
app = application.app

from src.core.database import Database
from src.core.stats_store import StatsStore
from src.ui.windows.main import MainWindow

db = Database()
store = StatsStore(db)
now = int(time.time())
for name, handle in (("studio.one", "studioone"), ("studio.two", "studiotwo")):
    if not db.get_account_by_username(name):
        db.save_account(name, f"tiktok_session-{name}.cookie", tag="music")
    store.save_snapshot(name, {"handle": handle, "nickname": name, "user": {"followers": 1200, "following": 8,
                                                                          "likes": 5600, "videos": 3},
                               "items": [
                                   {"id": "7001", "desc": "Танцы в парке #fyp", "createTime": now - 1800,
                                    "plays": 12400, "likes": 830, "comments": 42, "shares": 21, "saves": 130,
                                    "duration": 17},
                                   {"id": "7002", "desc": "Утренний вайб", "createTime": now - 7200,
                                    "plays": 3100, "likes": 120, "comments": 5, "shares": 2, "saves": 30,
                                    "duration": 22},
                                   {"id": "7003", "desc": "Поздний ролик", "createTime": now - 86000,
                                    "plays": 0, "likes": 0, "comments": 0, "shares": 0, "saves": 0,
                                    "duration": 9},
                               ]})

window = MainWindow()
window.resize(1120, 720)
window.show()
window.show_page(2)
for _ in range(3):
    app.processEvents()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shots", "stats_data.png")
window.grab().save(out)
print("OK", out)

for name in ("studio.one", "studio.two"):
    account = db.get_account_by_username(name)
    if account:
        db.delete_accounts([account[0]])
