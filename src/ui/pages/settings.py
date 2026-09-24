import os
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit
from PyQt6.QtCore import QThread, pyqtSignal

from src.core.paths import app_dir
from src.ui.components.common import PageHeader, make_button, make_label, set_role

ENV_PATH = app_dir() / ".env"
KEY = "TIKTOK_PROXY"


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


class SettingsPage(QWidget):
    proxy_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = None

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 36, 40, 32)
        root.setSpacing(0)
        root.addWidget(PageHeader("Настройки", "Соединение с TikTok"))
        root.addSpacing(28)

        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)
        column.addWidget(make_label("Прокси", "caption"))
        self.proxy_input = QLineEdit(read_proxy_from_env())
        self.proxy_input.setPlaceholderText("socks5h://127.0.0.1:1080")
        column.addWidget(self.proxy_input)
        note = make_label(
            "Применяется к входу, загрузке и подписи запросов. Оставьте пустым, если включён VPN: "
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

        wrap = QWidget()
        wrap.setLayout(column)
        wrap.setMaximumWidth(720)
        root.addWidget(wrap)
        root.addStretch()

    def refresh(self):
        self.proxy_input.setText(os.environ.get(KEY, read_proxy_from_env()))

    def _save(self):
        value = self.proxy_input.text().strip()
        write_proxy_to_env(value)
        self.proxy_changed.emit(value)
        self._show("Сохранено", "ok")

    def _check(self):
        self.btn_check.setEnabled(False)
        self._show("Проверяю...", "muted")
        self.thread = CheckThread(self.proxy_input.text().strip())
        self.thread.result.connect(self._checked)
        self.thread.start()

    def _checked(self, ok, text):
        self.btn_check.setEnabled(True)
        self._show(text, "ok" if ok else "err")

    def _show(self, text, role):
        self.result.setText(text)
        set_role(self.result, role)
