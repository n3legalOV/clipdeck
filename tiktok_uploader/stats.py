import json
import os
import subprocess
import tempfile

from tiktok_uploader.cookies import load_cookies_from_file


def fetch_account_stats(username, max_scrolls=6, timeout=180, proxy=None):
    """Собирает статистику аккаунта через headless-браузер (stats.js).

    Возвращает dict с handle/nickname/user/items. Ошибки — RuntimeError с
    текстом, который можно показать пользователю.
    """
    cookies = load_cookies_from_file(f"tiktok_session-{username}")
    if not cookies:
        raise RuntimeError("нет сохранённой сессии")

    script_dir = os.path.join(os.path.dirname(__file__), "tiktok-signature")
    script = os.path.join(script_dir, "stats.js")
    if not os.path.isfile(script):
        raise RuntimeError("не найден stats.js — переустановите программу")

    fd, cookie_path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump([{"name": c["name"], "value": c["value"]} for c in cookies], f)
        env = os.environ.copy()
        proxy = proxy or env.get("TIKTOK_PROXY")
        if proxy:
            env["TIKTOK_PROXY"] = proxy
        try:
            proc = subprocess.run(
                ["node", script, cookie_path, str(max_scrolls)],
                cwd=script_dir,
                capture_output=True,
                timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                env=env,
            )
        except FileNotFoundError:
            raise RuntimeError("не найден Node.js — установите его и перезапустите программу") from None
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"TikTok не ответил за {timeout} секунд") from None
    finally:
        try:
            os.remove(cookie_path)
        except OSError:
            pass

    lines = [line for line in proc.stdout.decode("utf-8", "replace").splitlines() if line.startswith("{")]
    if not lines:
        detail = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        hint = detail[-1][:200] if detail else "нет ответа от загрузчика статистики"
        raise RuntimeError(hint)
    try:
        data = json.loads(lines[-1])
    except json.JSONDecodeError:
        raise RuntimeError("загрузчик статистики вернул некорректный ответ") from None
    if data.get("status") == "not_logged_in":
        raise RuntimeError("сессия недействительна, войдите заново")
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message", "неизвестная ошибка"))
    return data
