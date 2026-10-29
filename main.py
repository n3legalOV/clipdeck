import sys
import os

from src.core.paths import app_dir

os.chdir(app_dir())

from dotenv import load_dotenv
load_dotenv(app_dir() / ".env")

if sys.platform == 'win32' and sys.stdout is not None:
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.core.app import Application

def selftest():
    import shutil
    lines = ["ClipForge self-test"]
    for name in ("PyQt6.QtWidgets", "requests", "tiktok_uploader.tiktok", "tiktok_uploader.stats",
                 "undetected_chromedriver", "fake_useragent"):
        try:
            __import__(name)
            lines.append(f"ok  {name}")
        except Exception as e:
            lines.append(f"ERR {name}: {e!r}")

    signature = app_dir() / "_internal" / "tiktok_uploader" / "tiktok-signature"
    if not signature.exists():
        signature = app_dir() / "tiktok_uploader" / "tiktok-signature"
    for name in ("browser.js", "stats.js"):
        path = signature / name
        lines.append(f"{'ok ' if path.exists() else 'ERR'} signer {path}")
    modules = signature / "node_modules" / "playwright-chromium"
    lines.append(f"{'ok ' if modules.exists() else 'ERR'} node_modules playwright-chromium в {signature}")

    node = shutil.which("node")
    lines.append(f"{'ok ' if node else 'ERR'} node {node}")
    try:
        from src.ui.dialogs.login import chrome_major_version
        major = chrome_major_version()
        lines.append(f"{'ok ' if major else 'ERR'} chrome {major or 'не найден'}")
    except Exception as e:
        lines.append(f"ERR chrome: {e!r}")

    try:
        from src.core.video_randomizer import resolve_ffmpeg
        binary = resolve_ffmpeg()
        lines.append(f"{'ok ' if binary else 'ERR'} ffmpeg {binary or 'не найден'}")
    except Exception as e:
        lines.append(f"ERR ffmpeg: {e!r}")

    try:
        from src.core.database import Database
        db = Database()
        db.set("selftest", "1")
        lines.append(f"ok  database {app_dir() / 'data' / 'tiktok.db'}")
    except Exception as e:
        lines.append(f"ERR база данных: {e!r}")

    (app_dir() / "selftest.log").write_text(chr(10).join(lines) + chr(10), encoding="utf-8")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    app = Application()
    sys.exit(app.run())
