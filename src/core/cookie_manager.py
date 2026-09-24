import os
import pickle
from pathlib import Path
from src.core.paths import app_dir


class CookieManager:
    """Управление cookie файлами TikTok"""

    def __init__(self, cookies_dir=None):
        if cookies_dir is None:
            self.cookies_dir = app_dir() / "CookiesDir"
        else:
            self.cookies_dir = Path(cookies_dir)

        self.cookies_dir.mkdir(exist_ok=True)

    def load_cookies(self, username: str):
        """Загрузить куки из файла"""
        cookie_file = self.cookies_dir / f"tiktok_session-{username}.cookie"

        if not cookie_file.exists():
            return None

        try:
            with open(cookie_file, "rb") as f:
                cookie_data = pickle.load(f)

            cookies = []
            for cookie in cookie_data:
                if 'sameSite' in cookie:
                    if cookie['sameSite'] == 'None':
                        cookie['sameSite'] = 'Strict'
                cookies.append(cookie)

            return cookies
        except Exception as e:
            print(f"Ошибка загрузки куков для {username}: {e}")
            return None

    def save_cookies(self, username: str, cookies):
        """Сохранить куки в файл"""
        cookie_file = self.cookies_dir / f"tiktok_session-{username}.cookie"

        try:
            with open(cookie_file, "wb") as f:
                pickle.dump(cookies, f)
            return True
        except Exception as e:
            print(f"Ошибка сохранения куков для {username}: {e}")
            return False

    def delete_cookies(self, username: str):
        """Удалить файл куков"""
        cookie_file = self.cookies_dir / f"tiktok_session-{username}.cookie"

        if cookie_file.exists():
            try:
                cookie_file.unlink()
                return True
            except Exception as e:
                print(f"Ошибка удаления куков для {username}: {e}")
                return False
        return False

    def has_cookies(self, username: str) -> bool:
        """Проверить наличие куков"""
        cookie_file = self.cookies_dir / f"tiktok_session-{username}.cookie"
        return cookie_file.exists()

    def get_session_id(self, username: str) -> str:
        """Получить session_id из куков"""
        cookies = self.load_cookies(username)

        if cookies:
            for cookie in cookies:
                if cookie.get("name") == "sessionid":
                    return cookie.get("value", "")

        return None

    def list_accounts(self):
        """Список всех аккаунтов с куками"""
        accounts = []

        for cookie_file in self.cookies_dir.glob("tiktok_session-*.cookie"):
            username = cookie_file.stem.replace("tiktok_session-", "")
            accounts.append(username)

        return accounts
