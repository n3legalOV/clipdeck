import os
import subprocess
import time

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QProgressBar, QVBoxLayout

from src.ui.components.common import make_button, make_label

REQUIRED = ("sessionid", "tt-target-idc")
TIMEOUT_SECONDS = 300

# Держим ссылки на работающие потоки: QThread нельзя удалять во время работы.
_RUNNING = []


def chrome_major_version() -> int:
    """Версия Chrome из реестра Windows (надёжнее, чем --version)."""
    try:
        import winreg

        for hive, path in (
            (winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Google\Chrome\BLBeacon"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Google\Chrome\BLBeacon"),
        ):
            try:
                with winreg.OpenKey(hive, path) as key:
                    version, _ = winreg.QueryValueEx(key, "version")
                return int(str(version).split(".")[0])
            except OSError:
                continue
    except ImportError:  # не Windows
        pass
    for binary in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        try:
            out = subprocess.check_output([binary, "--version"], stderr=subprocess.DEVNULL).decode()
            return int(out.strip().split()[-1].split(".")[0])
        except (FileNotFoundError, ValueError, IndexError, OSError):
            continue
    return 0


class LoginCancelled(Exception):
    pass


class LoginThread(QThread):
    succeeded = pyqtSignal(list)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, username):
        super().__init__()
        self.username = username
        self.stop_requested = False

    def run(self):
        driver = None
        try:
            try:
                import undetected_chromedriver as uc
            except Exception as e:
                self.failed.emit(f"Не установлен undetected-chromedriver: {e}")
                return

            options = uc.ChromeOptions()
            proxy = os.environ.get("TIKTOK_PROXY")
            if proxy:
                options.add_argument("--proxy-server={}".format(proxy.replace("socks5h://", "socks5://")))
            options.add_argument("--no-first-run")
            version = chrome_major_version()
            driver = uc.Chrome(options=options, version_main=version) if version > 0 else uc.Chrome(options=options)
            driver.get("https://www.tiktok.com/login")

            collected = {}
            started = time.monotonic()
            while True:
                if self.stop_requested:
                    raise LoginCancelled()
                if time.monotonic() - started > TIMEOUT_SECONDS:
                    raise TimeoutError("Превышено время ожидания входа")
                try:
                    for cookie in driver.get_cookies():
                        if cookie["name"] in REQUIRED:
                            collected[cookie["name"]] = cookie
                except Exception:
                    raise RuntimeError("Браузер закрыт до завершения входа")
                if all(name in collected for name in REQUIRED):
                    break
                time.sleep(1)

            self.succeeded.emit([collected["sessionid"], collected["tt-target-idc"]])
        except LoginCancelled:
            self.cancelled.emit()
        except Exception as e:
            self.failed.emit(str(e) or type(e).__name__)
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass


class LoginDialog(QDialog):
    """Ожидание входа в браузере: интерфейс не блокируется, можно отменить."""

    def __init__(self, parent, username):
        super().__init__(parent)
        self.setWindowTitle("Вход в TikTok")
        self.setMinimumWidth(460)
        self.setModal(True)
        self.cookies = None
        self.error = None
        self.cancelled_by_user = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)

        title = make_label(f"Вход в «{username}»")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        note = make_label(
            "Откроется браузер. Войдите в TikTok под нужным аккаунтом — окно закроется само, "
            "а куки сохранятся в программе.", "caption")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        self.status = make_label("Ожидаю вход...", "muted")
        layout.addWidget(self.status)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.btn_cancel = make_button("Отмена")
        self.btn_cancel.clicked.connect(self._cancel)
        buttons.addWidget(self.btn_cancel)
        layout.addLayout(buttons)

        self.thread = LoginThread(username)
        self.thread.succeeded.connect(self._succeeded)
        self.thread.failed.connect(self._failed)
        self.thread.cancelled.connect(self._cancelled)
        # Обработчик без receiver-объекта: он должен сработать даже если
        # диалог уже закрыт и удалён.
        self.thread.finished.connect(lambda thread=self.thread: _release(thread))
        _RUNNING.append(self.thread)

    def start(self):
        self.thread.start()

    def _cancel(self):
        self.cancelled_by_user = True
        self.thread.stop_requested = True
        self.status.setText("Отменяю...")
        self.btn_cancel.setEnabled(False)

    def _succeeded(self, cookies):
        self.cookies = cookies
        self.accept()

    def _failed(self, message):
        self.error = message
        self.status.setText(message)
        self.reject()

    def _cancelled(self):
        self.status.setText("Вход отменён")
        self.reject()

    def closeEvent(self, event):
        self.thread.stop_requested = True
        super().closeEvent(event)


def _release(thread):
    if thread in _RUNNING:
        _RUNNING.remove(thread)
    try:
        thread.deleteLater()
    except RuntimeError:
        pass
