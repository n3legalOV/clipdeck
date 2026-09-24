import sys
import time
from datetime import datetime

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QComboBox,
                             QHeaderView, QAbstractItemView, QProgressBar, QMenu, QStackedLayout, QApplication)
from PyQt6.QtCore import Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QAction

from src.core.database import Database
from src.core.paths import app_dir
from src.core.stats_store import StatsStore
from src.ui.components.common import PageHeader, make_button, make_label, set_role
from src.ui.styles import SUCCESS, DANGER, MUTED

AUTO_OPTIONS = [("Выкл", 0), ("Каждые 15 минут", 15), ("Каждые 30 минут", 30), ("Каждый час", 60)]
ALL = "__all__"

COLUMNS = ["Аккаунт", "Ролик", "Дата", "Просмотры", "Прирост", "Лайки", "Комм.", "Репосты", "Состояние"]
COL_ACCOUNT, COL_CAPTION, COL_DATE, COL_PLAYS, COL_DELTA, COL_LIKES, COL_COMMENTS, COL_SHARES, COL_STATE = range(9)
NUMERIC_COLS = (COL_PLAYS, COL_DELTA, COL_LIKES, COL_COMMENTS, COL_SHARES)


def fmt(n):
    return f"{int(n):,}".replace(",", " ")


class NumItem(QTableWidgetItem):
    def __init__(self, value, text=None):
        super().__init__(text if text is not None else fmt(value))
        self.setData(Qt.ItemDataRole.UserRole, value)
        self.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def __lt__(self, other):
        return (self.data(Qt.ItemDataRole.UserRole) or 0) < (other.data(Qt.ItemDataRole.UserRole) or 0)


class StatsThread(QThread):
    progress = pyqtSignal(str)
    account_done = pyqtSignal(str, bool, str)

    def __init__(self, usernames):
        super().__init__()
        self.usernames = usernames

    def run(self):
        if str(app_dir()) not in sys.path:
            sys.path.insert(0, str(app_dir()))
        from tiktok_uploader.stats import fetch_account_stats
        store = StatsStore()
        total = len(self.usernames)
        for index, username in enumerate(self.usernames, 1):
            self.progress.emit(f"Обновляю {username} ({index} из {total})")
            try:
                data = fetch_account_stats(username)
                store.save_snapshot(username, data)
                self.account_done.emit(username, True, "")
            except Exception as e:
                self.account_done.emit(username, False, str(e))


class StatCard(QWidget):
    def __init__(self, title):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(make_label(title, "caption"))
        self.value = make_label("0")
        self.value.setObjectName("statValue")
        layout.addWidget(self.value)
        self.delta = make_label("", "caption")
        layout.addWidget(self.delta)

    def set(self, value, delta=None):
        self.value.setText(fmt(value))
        if delta is None:
            self.delta.setText(" ")
            set_role(self.delta, "caption")
        elif delta > 0:
            self.delta.setText(f"+{fmt(delta)} с прошлого раза")
            set_role(self.delta, "ok")
        else:
            self.delta.setText("без изменений")
            set_role(self.delta, "caption")


class StatsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self.store = StatsStore(self.db)
        self.thread = None
        self.errors = {}
        self.handles = {}
        self._build()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._auto_tick)
        saved = int(self.store.get_kv("stats_auto_minutes", 0) or 0)
        index = next((i for i, (_, m) in enumerate(AUTO_OPTIONS) if m == saved), 0)
        self.auto.blockSignals(True)
        self.auto.setCurrentIndex(index)
        self.auto.blockSignals(False)
        self._apply_auto()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 36, 40, 32)
        root.setSpacing(0)

        top = QHBoxLayout()
        self.header = PageHeader("Статистика", "")
        top.addWidget(self.header, 1)
        self.btn_refresh = make_button("Обновить", "primary")
        self.btn_refresh.clicked.connect(self.refresh_all)
        top.addWidget(self.btn_refresh, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(top)
        root.addSpacing(24)

        cards = QHBoxLayout()
        cards.setSpacing(40)
        self.card_plays = StatCard("Просмотры")
        self.card_likes = StatCard("Лайки")
        self.card_comments = StatCard("Комментарии")
        self.card_shares = StatCard("Репосты")
        self.card_followers = StatCard("Подписчики")
        for card in (self.card_plays, self.card_likes, self.card_comments, self.card_shares, self.card_followers):
            cards.addWidget(card)
        cards.addStretch()
        root.addLayout(cards)
        root.addSpacing(24)

        controls = QHBoxLayout()
        controls.setSpacing(12)
        controls.addWidget(make_label("Аккаунт", "caption"))
        self.account_filter = QComboBox()
        self.account_filter.setMinimumWidth(200)
        self.account_filter.currentIndexChanged.connect(self.reload)
        controls.addWidget(self.account_filter)
        controls.addSpacing(16)
        controls.addWidget(make_label("Автообновление", "caption"))
        self.auto = QComboBox()
        for label, _ in AUTO_OPTIONS:
            self.auto.addItem(label)
        self.auto.currentIndexChanged.connect(self._auto_changed)
        controls.addWidget(self.auto)
        controls.addStretch()
        root.addLayout(controls)
        root.addSpacing(8)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        root.addWidget(self.progress)
        self.note = make_label("", "caption")
        self.note.setWordWrap(True)
        root.addWidget(self.note)
        root.addSpacing(8)

        holder = QWidget()
        self.stack = QStackedLayout(holder)
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_CAPTION, QHeaderView.ResizeMode.Stretch)
        widths = {COL_ACCOUNT: 124, COL_DATE: 104, COL_PLAYS: 96, COL_DELTA: 80, COL_LIKES: 64,
                  COL_COMMENTS: 64, COL_SHARES: 80, COL_STATE: 136}
        for col, width in widths.items():
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, width)
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setStyleSheet("QTableWidget::item { padding: 0 10px; } QHeaderView::section { padding: 10px 10px; }")
        header.setMinimumSectionSize(48)
        for col in NUMERIC_COLS:
            self.table.horizontalHeaderItem(col).setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.setSortingEnabled(True)
        self.table.itemDoubleClicked.connect(lambda item: self._open(item.row()))
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu)
        self.stack.addWidget(self.table)

        empty = QWidget()
        empty_layout = QVBoxLayout(empty)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = make_label("Данных пока нет")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = make_label("Нажмите «Обновить», чтобы загрузить статистику роликов.", "muted")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(title)
        empty_layout.addWidget(hint)
        self.stack.addWidget(empty)
        root.addWidget(holder, 1)

    def refresh(self):
        accounts = [row[1] for row in self.db.get_accounts()]
        current = self.account_filter.currentData()
        self.account_filter.blockSignals(True)
        self.account_filter.clear()
        self.account_filter.addItem("Все аккаунты", ALL)
        for name in accounts:
            self.account_filter.addItem(name, name)
        index = self.account_filter.findData(current) if current else 0
        self.account_filter.setCurrentIndex(max(index, 0))
        self.account_filter.blockSignals(False)
        self.btn_refresh.setEnabled(bool(accounts) and not self._busy())
        self.reload()

    def _busy(self):
        return self.thread is not None and self.thread.isRunning()

    def reload(self):
        selected = self.account_filter.currentData() or ALL
        accounts = self.store.latest_accounts()
        self.handles = {name: info["handle"] for name, info in accounts.items()}
        videos = [v for v in self.store.latest_videos() if selected == ALL or v["username"] == selected]

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        now = time.time()
        for row, v in enumerate(videos):
            self.table.insertRow(row)
            handle = self.handles.get(v["username"], "")
            first = self.table.setItem
            account_item = QTableWidgetItem(f"@{handle}" if handle else v["username"])
            account_item.setData(Qt.ItemDataRole.UserRole, (handle, v["video_id"]))
            first(row, COL_ACCOUNT, account_item)
            caption = (v["caption"] or "").replace("\n", " ").strip() or "без подписи"
            caption_item = QTableWidgetItem(caption)
            caption_item.setToolTip(v["caption"] or "")
            first(row, COL_CAPTION, caption_item)
            created = int(v["create_time"] or 0)
            date_item = NumItem(created, self._format_date(created))
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            first(row, COL_DATE, date_item)
            first(row, COL_PLAYS, NumItem(v["plays"]))

            d_plays = v["d_plays"]
            if d_plays is None:
                delta_item, state, color = NumItem(0, "—"), "Новый", MUTED
            elif d_plays > 0:
                delta_item, state, color = NumItem(d_plays, f"+{fmt(d_plays)}"), "Растёт", SUCCESS
            else:
                delta_item, state, color = NumItem(0, "0"), "Без роста", MUTED
            age_hours = (now - created) / 3600 if created else 0
            if v["plays"] == 0 and age_hours > 2:
                state, color = "Нет просмотров", DANGER
            delta_item.setForeground(QColor(SUCCESS if (d_plays or 0) > 0 else MUTED))
            first(row, COL_DELTA, delta_item)
            first(row, COL_LIKES, NumItem(v["likes"]))
            first(row, COL_COMMENTS, NumItem(v["comments"]))
            first(row, COL_SHARES, NumItem(v["shares"]))
            state_item = QTableWidgetItem(state)
            state_item.setForeground(QColor(color))
            first(row, COL_STATE, state_item)
        self.table.setSortingEnabled(True)
        self.table.sortItems(COL_DATE, Qt.SortOrder.DescendingOrder)
        self.stack.setCurrentIndex(0 if videos else 1)

        def total(key):
            return sum(v[key] or 0 for v in videos)

        def delta(key):
            values = [v[key] for v in videos if v[key] is not None]
            return sum(values) if values else None

        self.card_plays.set(total("plays"), delta("d_plays"))
        self.card_likes.set(total("likes"), delta("d_likes"))
        self.card_comments.set(total("comments"))
        self.card_shares.set(total("shares"))
        followers = sum(info["followers"] or 0 for name, info in accounts.items() if selected in (ALL, name))
        self.card_followers.set(followers)

        last = self.store.last_fetch()
        self.header.set_subtitle(
            f"Обновлено {datetime.fromtimestamp(last).strftime('%d.%m в %H:%M')}" if last else "Ещё не обновлялось")
        errors = "; ".join(f"{name}: {msg}" for name, msg in self.errors.items())
        self.note.setText(errors)
        set_role(self.note, "err" if errors else "caption")

    @staticmethod
    def _format_date(created):
        if not created:
            return ""
        moment = datetime.fromtimestamp(created)
        return moment.strftime("%d.%m %H:%M" if moment.year == datetime.now().year else "%d.%m.%y")

    def refresh_all(self):
        if self._busy():
            return
        usernames = [row[1] for row in self.db.get_accounts()]
        if not usernames:
            return
        self.errors = {}
        self.thread = StatsThread(usernames)
        self.thread.progress.connect(self._on_progress)
        self.thread.account_done.connect(self._on_account_done)
        self.thread.finished.connect(self._on_finished)
        self.btn_refresh.setEnabled(False)
        self.progress.setVisible(True)
        self.thread.start()

    def _on_progress(self, text):
        self.note.setText(text)
        set_role(self.note, "caption")

    def _on_account_done(self, username, ok, message):
        if not ok:
            self.errors[username] = message
        self.reload()

    def _on_finished(self):
        self.progress.setVisible(False)
        self.btn_refresh.setEnabled(True)
        self.thread = None
        self.reload()

    def _auto_changed(self):
        minutes = AUTO_OPTIONS[self.auto.currentIndex()][1]
        self.store.set_kv("stats_auto_minutes", minutes)
        self._apply_auto()

    def _apply_auto(self):
        minutes = AUTO_OPTIONS[self.auto.currentIndex()][1]
        if minutes:
            self.timer.start(minutes * 60 * 1000)
        else:
            self.timer.stop()

    def _auto_tick(self):
        if not self._busy():
            self.refresh_all()

    def _video_url(self, row):
        data = self.table.item(row, COL_ACCOUNT).data(Qt.ItemDataRole.UserRole)
        if not data or not data[0]:
            return None
        return f"https://www.tiktok.com/@{data[0]}/video/{data[1]}"

    def _open(self, row):
        url = self._video_url(row)
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _menu(self, position):
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        self.table.selectRow(row)
        menu = QMenu(self)
        open_action = QAction("Открыть в TikTok", self)
        open_action.triggered.connect(lambda: self._open(row))
        copy_action = QAction("Копировать ссылку", self)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(self._video_url(row) or ""))
        menu.addAction(open_action)
        menu.addAction(copy_action)
        menu.exec(self.table.viewport().mapToGlobal(position))
