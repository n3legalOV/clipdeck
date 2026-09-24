from PyQt6.QtWidgets import QTableWidget


class DragSelectTableBase(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
