import os
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget
from src.ui.components.sidebar import Sidebar
from src.ui.pages.accounts import AccountsPage
from src.ui.pages.uploads import UploadsPage
from src.ui.pages.stats import StatsPage
from src.ui.pages.settings import SettingsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clipdeck")
        self.resize(1120, 720)
        self.setMinimumSize(960, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self.on_page_changed)
        layout.addWidget(self.sidebar)

        self.pages = QStackedWidget()
        self.pages.setObjectName("content")
        self.accounts_page = AccountsPage()
        self.uploads_page = UploadsPage()
        self.stats_page = StatsPage()
        self.settings_page = SettingsPage()
        self.settings_page.proxy_changed.connect(self.sidebar.set_connection)
        self.accounts_page.go_upload.connect(lambda: self.show_page(1))

        for page in (self.accounts_page, self.uploads_page, self.stats_page, self.settings_page):
            self.pages.addWidget(page)
        layout.addWidget(self.pages, 1)

        self.sidebar.set_connection(os.environ.get("TIKTOK_PROXY", ""))

    def show_page(self, index: int):
        self.sidebar.select(index, emit=False)
        self.on_page_changed(index)

    def on_page_changed(self, index: int):
        self.pages.setCurrentIndex(index)
        page = self.pages.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()
