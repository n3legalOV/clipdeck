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
    lines = []
    for name in ("tiktok_uploader.tiktok", "undetected_chromedriver", "moviepy.editor", "fake_useragent"):
        try:
            __import__(name)
            lines.append(f"ok  {name}")
        except Exception as e:
            lines.append(f"ERR {name}: {e!r}")
    js = app_dir() / "_internal" / "tiktok_uploader" / "tiktok-signature" / "browser.js"
    lines.append(f"{'ok ' if js.exists() else 'ERR'} signer {js}")
    stats_js = js.with_name("stats.js")
    lines.append(f"{'ok ' if stats_js.exists() else 'ERR'} stats {stats_js}")
    lines.append(f"{'ok ' if shutil.which('node') else 'ERR'} node {shutil.which('node')}")
    (app_dir() / "selftest.log").write_text(chr(10).join(lines), encoding="utf-8")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    app = Application()
    sys.exit(app.run())
