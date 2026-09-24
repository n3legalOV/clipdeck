import sys
from PyQt6.QtWidgets import QApplication
from pathlib import Path
from PyQt6.QtGui import QFont, QIcon
from src.ui.windows.main import MainWindow
from src.ui.styles import APP_STYLE
from src.core.database import Database


class Application:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")
        self.app.setFont(QFont("Segoe UI", 10))
        self.app.setStyleSheet(APP_STYLE)
        self.app.setWindowIcon(QIcon(str(Path(__file__).resolve().parents[1] / "ui" / "assets" / "icon.png")))
        self.main_window = None
        self.db = Database()

    def run(self):
        self.main_window = MainWindow()
        self.main_window.show()
        return self.app.exec()
