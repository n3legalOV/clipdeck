from PyQt6.QtWidgets import QHeaderView, QAbstractItemView
from PyQt6.QtCore import Qt
from src.ui.components.drag_table import DragSelectTableBase

COL_ID, COL_NAME, COL_TAG, COL_VIDEOS = range(4)


def create_accounts_table():
    table = DragSelectTableBase()
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(["ID", "Имя", "Тег", "Видео"])
    table.setColumnHidden(COL_ID, True)

    header = table.horizontalHeader()
    header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(COL_TAG, QHeaderView.ResizeMode.Interactive)
    header.setSectionResizeMode(COL_VIDEOS, QHeaderView.ResizeMode.Interactive)
    header.setHighlightSections(False)
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    table.setColumnWidth(COL_TAG, 200)
    table.setColumnWidth(COL_VIDEOS, 100)

    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(44)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setShowGrid(False)
    table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    return table
