import os
import shutil
import subprocess

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QSpinBox
from PyQt6.QtCore import QThread, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices

from src.app.services import ClipForgeService
from src.core.paths import app_dir
from src.ui.components.common import PageHeader, make_button, make_label, make_divider, set_role

ENV_PATH = app_dir() / ".env"
KEY = "TIKTOK_PROXY"
DELAY_KEY = "upload_delay"


def read_proxy_from_env() -> str:
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{KEY}="):
                return line.split("=", 1)[1].strip()
    return ""


def write_proxy_to_env(value: str):
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    lines = [line for line in lines if not line.startswith(f"{KEY}=")]
    if value:
        lines.append(f"{KEY}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if value:
        os.environ[KEY] = value
    else:
        os.environ.pop(KEY, None)


class CheckThread(QThread):
    result = pyqtSignal(bool, str)

    def __init__(self, proxy):
        super().__init__()
        self.proxy = proxy

    def run(self):
        try:
            import requests
            session = requests.Session()
            session.trust_env = False
            if self.proxy:
                session.proxies = {"http": self.proxy, "https": self.proxy}
            data = session.get("https://ipinfo.io/json", timeout=15).json()
            self.result.emit(True, f"{data.get('ip', '?')}   ·   {data.get('country', '?')}   ·   {data.get('org', '')}")
        except Exception as e:
            self.result.emit(False, f"Нет соединения: {type(e).__name__}")


class DiagnosticsThread(QThread):
    """Проверяет, всё ли на месте для публикации и статистики."""

    result = pyqtSignal(str)

    def run(self):
        lines = []

        node = shutil.which("node")
        if node:
            try:
                version = subprocess.check_output([node, "--version"], stderr=subprocess.DEVNULL,
                                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                lines.append(f"Node.js: {version.decode().strip()}")
            except Exception:
                lines.append("Node.js: найден, но не запускается")
        else:
            lines.append("Node.js: НЕ НАЙДЕН — без него не работают публикация и статистика")

        try:
            from src.ui.dialogs.login import chrome_major_version
            major = chrome_major_version()
            lines.append(f"Chrome: {f'версия {major}' if major else 'не найден — вход через браузер не сработает'}")
        except Exception as e:
            lines.append(f"Chrome: проверить не удалось ({e})")

        for module, title in (("undetected_chromedriver", "Вход через браузер"), ("playwright", "Статистика")):
            try:
                __import__(module)
                lines.append(f"{title}: пакет установлен")
            except Exception:
                lines.append(f"{title}: пакет {module} не установлен")

        from src.core.video_randomizer import resolve_ffmpeg
        ffmpeg = resolve_ffmpeg()
        lines.append(f"FFmpeg: {ffmpeg}" if ffmpeg else "FFmpeg: НЕ НАЙДЕН — уникализация видео недоступна")

        cookies = app_dir() / "CookiesDir"
        count = len(list(cookies.glob("*.cookie"))) if cookies.exists() else 0
        lines.append(f"Файлов куков: {count}")
        lines.append(f"Папка данных: {app_dir()}")
        self.result.emit("\n".join(lines))


class SettingsPage(QWidget):
    proxy_changed = pyqtSignal(str)

    def __init__(self, service=None, parent=None):
        super().__init__(parent)
        self.service = service or ClipForgeService()
        self.db = self.service.db
        self.thread = None
        self.diag_thread = None

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 36, 40, 32)
        root.setSpacing(0)
        root.addWidget(PageHeader("Настройки", "Соединение, публикация, папка данных"))
        root.addSpacing(28)

        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)
        column.addWidget(make_label("Прокси", "caption"))
        self.proxy_input = QLineEdit(read_proxy_from_env())
        self.proxy_input.setPlaceholderText("socks5h://127.0.0.1:1080")
        column.addWidget(self.proxy_input)
        note = make_label(
            "Применяется к входу, загрузке, статистике и подписи запросов. Оставьте пустым, если включён VPN: "
            "запросы пойдут напрямую через него.", "caption")
        note.setWordWrap(True)
        column.addWidget(note)
        column.addSpacing(16)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.btn_save = make_button("Сохранить", "primary")
        self.btn_save.clicked.connect(self._save)
        self.btn_check = make_button("Проверить IP")
        self.btn_check.clicked.connect(self._check)
        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_check)
        buttons.addStretch()
        column.addLayout(buttons)
        column.addSpacing(16)

        self.result = make_label("", "muted")
        self.result.setWordWrap(True)
        column.addWidget(self.result)

        column.addSpacing(24)
        column.addWidget(make_divider())
        column.addSpacing(20)

        column.addWidget(make_label("Публикация", "caption"))
        delay_row = QHBoxLayout()
        delay_row.setSpacing(10)
        self.delay = QSpinBox()
        self.delay.setRange(0, 3600)
        self.delay.setSuffix(" с")
        self.delay.setMaximumWidth(120)
        self.delay.setValue(int(self.db.get(DELAY_KEY, 0) or 0))
        self.delay.valueChanged.connect(self._save_delay)
        delay_row.addWidget(self.delay)
        delay_hint = make_label("пауза между аккаунтами в одной публикации", "caption")
        delay_row.addWidget(delay_hint, 1)
        column.addLayout(delay_row)
        note2 = make_label(
            "Пауза снижает риск ограничений: TikTok не любит, когда с одного IP публикуют десятки роликов подряд.",
            "caption")
        note2.setWordWrap(True)
        column.addWidget(note2)

        column.addSpacing(24)
        column.addWidget(make_divider())
        column.addSpacing(20)

        column.addWidget(make_label("Обслуживание", "caption"))
        service = QHBoxLayout()
        service.setSpacing(8)
        self.btn_data = make_button("Открыть папку данных")
        self.btn_data.clicked.connect(self._open_data_dir)
        self.btn_diag = make_button("Проверить окружение")
        self.btn_diag.clicked.connect(self._diagnostics)
        service.addWidget(self.btn_data)
        service.addWidget(self.btn_diag)
        service.addStretch()
        column.addLayout(service)
        self.diag = make_label("", "caption")
        self.diag.setWordWrap(True)
        self.diag.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        column.addSpacing(8)
        column.addWidget(self.diag)

        wrap = QWidget()
        wrap.setLayout(column)
        wrap.setMaximumWidth(720)
        root.addWidget(wrap)
        root.addStretch()

    def refresh(self):
        self.proxy_input.setText(os.environ.get(KEY, read_proxy_from_env()))
        self.delay.setValue(int(self.db.get(DELAY_KEY, 0) or 0))

    def _save(self):
        value = self.proxy_input.text().strip()
        write_proxy_to_env(value)
        self.proxy_changed.emit(value)
        self._show("Сохранено", "ok")

    def _save_delay(self, value):
        self.db.set(DELAY_KEY, int(value))

    def _check(self):
        self.btn_check.setEnabled(False)
        self._show("Проверяю...", "muted")
        self.thread = CheckThread(self.proxy_input.text().strip())
        self.thread.result.connect(self._checked)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _checked(self, ok, text):
        self.btn_check.setEnabled(True)
        self._show(text, "ok" if ok else "err")

    def _open_data_dir(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(app_dir())))

    def _diagnostics(self):
        self.btn_diag.setEnabled(False)
        self.diag.setText("Проверяю окружение...")
        set_role(self.diag, "caption")
        self.diag_thread = DiagnosticsThread()
        self.diag_thread.result.connect(self._diagnostics_done)
        self.diag_thread.finished.connect(self.diag_thread.deleteLater)
        self.diag_thread.start()

    def _diagnostics_done(self, text):
        self.btn_diag.setEnabled(True)
        self.diag.setText(text)
        set_role(self.diag, "ok" if "НЕ НАЙДЕН" not in text else "err")

    def _show(self, text, role):
        self.result.setText(text)
        set_role(self.result, role)
