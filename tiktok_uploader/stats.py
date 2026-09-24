import json
import os
import subprocess
import tempfile

from tiktok_uploader.cookies import load_cookies_from_file


def fetch_account_stats(username, max_scrolls=6, timeout=180):
    cookies = load_cookies_from_file(f"tiktok_session-{username}")
    if not cookies:
        raise RuntimeError("нет сохранённой сессии")

    script_dir = os.path.join(os.path.dirname(__file__), "tiktok-signature")
    fd, cookie_path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump([{"name": c["name"], "value": c["value"]} for c in cookies], f)
        proc = subprocess.run(
            ["node", os.path.join(script_dir, "stats.js"), cookie_path, str(max_scrolls)],
            cwd=script_dir,
            capture_output=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    finally:
        try:
            os.remove(cookie_path)
        except OSError:
            pass

    lines = [line for line in proc.stdout.decode("utf-8", "replace").splitlines() if line.startswith("{")]
    if not lines:
        raise RuntimeError("нет ответа от загрузчика статистики")
    data = json.loads(lines[-1])
    if data.get("status") == "not_logged_in":
        raise RuntimeError("сессия недействительна, войдите заново")
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message", "неизвестная ошибка"))
    return data
