import contextlib
import os
import sys
import time
from pathlib import Path

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QPlainTextEdit,
                             QComboBox, QProgressBar, QCheckBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from src.app.contracts import RandomizerSettings, UploadOutcome
from src.app.services import (
    ClipForgeService,
    MAX_VIDEO_BYTES,
    VIDEO_EXTENSIONS,
    validate_video_file,
)
from src.core.paths import app_dir
from src.core.video_randomizer import RandomizerError, clear_variants, randomize_video, resolve_ffmpeg, variant_filename
from src.ui.components.common import PageHeader, make_button, make_label, make_divider, set_role, plural
from src.ui.dialogs.styled_dialogs import show_warning
from src.ui.dialogs.upload_history import UploadHistoryDialog

CAPTION_LIMIT = 2200
PROJECT_DIR = app_dir()


class _LineEmitter:
    def __init__(self, emit):
        self.emit = emit
        self.buffer = ""

    def write(self, text):
        self.buffer += text
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line.strip():
                self.emit(line.rstrip())
        return len(text)

    def flush(self):
        if self.buffer.strip():
            self.emit(self.buffer.strip())
        self.buffer = ""


class UploadThread(QThread):
    line = pyqtSignal(str)
    account_result = pyqtSignal(str, bool, str)
    finished_all = pyqtSignal(int, int, bool)

    def __init__(self, video_path, caption, usernames, delay=0, variant_settings=None, variant_dir=None):
        super().__init__()
        self.video_path = video_path
        self.caption = caption
        self.usernames = usernames
        self.delay = max(0, int(delay or 0))
        self.variant_settings = variant_settings
        self.variant_dir = Path(variant_dir) if variant_dir else None
        self.stop_requested = False

    def _sleep(self, seconds):
        """Пауза, которую можно прервать кнопкой «Остановить»."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self.stop_requested:
                return
            time.sleep(min(0.5, max(0.0, deadline - time.monotonic())))

    def run(self):
        if str(PROJECT_DIR) not in sys.path:
            sys.path.insert(0, str(PROJECT_DIR))
        try:
            from tiktok_uploader import tiktok
        except Exception as e:
            self.line.emit(f"Не удалось загрузить модуль загрузки: {e}")
            self.finished_all.emit(0, len(self.usernames), bool(self.stop_requested))
            return

        variant_dir = self.variant_dir or (PROJECT_DIR / "data" / "variants" / f"run-{int(time.time() * 1000)}")
        total = len(self.usernames)
        done = 0
        try:
            for index, username in enumerate(self.usernames, 1):
                if self.stop_requested:
                    self.line.emit("Остановлено пользователем")
                    break
                self.line.emit(f"[{index}/{total}] @{username}")
                target = self.video_path
                if self.variant_settings is not None:
                    try:
                        variant_dir.mkdir(parents=True, exist_ok=True)
                        self.line.emit("    Готовлю уникальную версию")
                        variant = randomize_video(
                            self.video_path,
                            str(variant_dir / variant_filename(self.video_path, index, username)),
                            self.variant_settings,
                        )
                        target = variant.path
                        self.line.emit(
                            f"    Вариант: {Path(target).name} · контраст {variant.contrast} · "
                            f"яркость {variant.brightness} · шум {variant.noise} · CRF {variant.crf}"
                        )
                    except RandomizerError as e:
                        error = str(e) or type(e).__name__
                        self.line.emit(f"    Ошибка уникализации: {error}")
                        self.account_result.emit(username, False, error)
                        if index < total and self.delay and not self.stop_requested:
                            self._sleep(self.delay)
                        continue
                if self.stop_requested:
                    self.line.emit("Остановлено пользователем")
                    break

                emitter = _LineEmitter(lambda text: self.line.emit("    " + text))
                ok = False
                error = ""
                try:
                    with contextlib.redirect_stdout(emitter):
                        result = tiktok.upload_video(
                            session_user=username,
                            video=target,
                            title=self.caption,
                            proxy=os.environ.get("TIKTOK_PROXY") or None,
                        )
                    ok = result is not False
                    if not ok:
                        error = "TikTok не принял публикацию"
                except (Exception, SystemExit) as e:
                    error = str(e) or type(e).__name__
                finally:
                    emitter.flush()

                if ok:
                    done += 1
                    self.line.emit("    Опубликовано")
                else:
                    self.line.emit(f"    Ошибка: {error}")
                self.account_result.emit(username, ok, error)

                if index < total and self.delay and not self.stop_requested:
                    self.line.emit(f"    Пауза {self.delay} с перед следующим аккаунтом")
                    self._sleep(self.delay)

            self.finished_all.emit(done, total, bool(self.stop_requested))
        finally:
            if self.variant_dir is None:
                clear_variants(variant_dir)


class UploadsPage(QWidget):
    accounts_changed = pyqtSignal()

    def __init__(self, service=None, parent=None):
        super().__init__(parent)
        self.service = service or ClipForgeService()
        self.db = self.service.db
        self.video_path = None
        self.thread = None
        self.failed = []
        self.last_job = None
        self._active_usernames = []
        self._last_status = None
        self.setAcceptDrops(True)
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 36, 40, 32)
        root.setSpacing(0)

        self.header = PageHeader("Новая публикация", "Подготовьте видео и отправьте его аккаунтам группы")
        root.addWidget(self.header)
        root.addSpacing(28)

        form = QVBoxLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(6)

        form.addWidget(make_label("1 · Видео для публикации", "caption"))
        video_row = QHBoxLayout()
        video_row.setSpacing(12)
        self.video_label = make_label("Файл не выбран · перетащите видео в окно", "muted")
        self.btn_video = make_button("Выбрать файл")
        self.btn_video.clicked.connect(self._select_video)
        video_row.addWidget(self.video_label, 1)
        video_row.addWidget(self.btn_video)
        form.addLayout(video_row)
        form.addSpacing(16)

        caption_head = QHBoxLayout()
        caption_head.addWidget(make_label("2 · Подпись и хэштеги", "caption"))
        caption_head.addStretch()
        self.counter = make_label(f"0 / {CAPTION_LIMIT}", "caption")
        caption_head.addWidget(self.counter)
        form.addLayout(caption_head)
        self.caption = QPlainTextEdit()
        self.caption.setFixedHeight(120)
        self.caption.setPlaceholderText("Текст под видео. Хэштеги пишите прямо здесь.")
        self.caption.textChanged.connect(self._on_caption)
        form.addWidget(self.caption)
        form.addSpacing(16)

        form.addWidget(make_label("3 · Группа аккаунтов", "caption"))
        self.group = QComboBox()
        self.group.currentIndexChanged.connect(self._update_state)
        form.addWidget(self.group)
        form.addSpacing(10)

        variant_row = QHBoxLayout()
        variant_row.setSpacing(10)
        self.chk_variants = QCheckBox("Разные версии видео для каждого аккаунта")
        self.chk_variants.setChecked(bool(self.db.get("randomize_variants", False)))
        self.chk_variants.toggled.connect(self._on_variants_toggled)
        variant_row.addWidget(self.chk_variants)
        self.variant_intensity = QComboBox()
        for label, code in (("Лёгкая", "light"), ("Средняя", "medium"),
                            ("Сильная", "strong"), ("Случайная", "random")):
            self.variant_intensity.addItem(label, code)
        saved_intensity = str(self.db.get("randomize_intensity", "medium") or "medium")
        self.variant_intensity.setCurrentIndex(max(0, self.variant_intensity.findData(saved_intensity)))
        self.variant_intensity.currentIndexChanged.connect(self._on_intensity_changed)
        variant_row.addWidget(self.variant_intensity)
        variant_row.addStretch()
        form.addLayout(variant_row)
        hint = make_label("FFmpeg меняет контраст, яркость, шум и сжатие у копии для каждого аккаунта.", "caption")
        hint.setWordWrap(True)
        form.addWidget(hint)

        form_wrap = QWidget()
        form_wrap.setLayout(form)
        form_wrap.setMaximumWidth(720)
        root.addWidget(form_wrap)
        root.addSpacing(24)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)
        self.btn_start = make_button("Опубликовать", "primary")
        self.btn_start.clicked.connect(lambda: self._start())
        self.btn_stop = make_button("Остановить")
        self.btn_stop.clicked.connect(self._stop)
        self.btn_stop.setVisible(False)
        self.btn_retry = make_button("Повторить ошибки")
        self.btn_retry.clicked.connect(self._retry_failed)
        self.btn_retry.setVisible(False)
        self.status = make_label("", "muted")
        actions.addWidget(self.btn_start)
        actions.addWidget(self.btn_stop)
        actions.addWidget(self.btn_retry)
        actions.addSpacing(8)
        actions.addWidget(self.status, 1)
        actions_wrap = QWidget()
        actions_wrap.setLayout(actions)
        actions_wrap.setMaximumWidth(720)
        root.addWidget(actions_wrap)
        root.addSpacing(16)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        root.addSpacing(8)
        root.addWidget(make_divider())
        root.addSpacing(16)
        log_head = QHBoxLayout()
        log_head.addWidget(make_label("Журнал", "caption"))
        log_head.addStretch()
        self.btn_history = make_button("История публикаций")
        self.btn_history.clicked.connect(self._show_history)
        log_head.addWidget(self.btn_history)
        self.btn_copy_log = make_button("Скопировать журнал")
        self.btn_copy_log.clicked.connect(self._copy_log)
        log_head.addWidget(self.btn_copy_log)
        root.addLayout(log_head)
        root.addSpacing(6)
        self.log = QPlainTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Здесь появится ход загрузки и причины ошибок.")
        root.addWidget(self.log, 1)

    def refresh(self):
        current = self.group.currentData()
        self.group.blockSignals(True)
        self.group.clear()
        rows = self.db.fetchall(
            "SELECT tag, COUNT(*) AS c FROM accounts WHERE status = 'active' AND tag IS NOT NULL "
            "GROUP BY tag ORDER BY tag")
        for row in rows:
            self.group.addItem(f"{row[0]}   ·   {plural(row[1], 'аккаунт', 'аккаунта', 'аккаунтов')}", row[0])
        if current is not None:
            index = self.group.findData(current)
            if index >= 0:
                self.group.setCurrentIndex(index)
        self.group.blockSignals(False)
        self._update_state()

    def _select_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать видео", "",
                                              "Видео (*.mp4 *.mov *.m4v *.webm);;Все файлы (*)")
        if path:
            self._use_video(path)

    def _use_video(self, path):
        validation = validate_video_file(path)
        if not validation.valid:
            if validation.code == "missing":
                title, detail = "Файл не найден", f"Не удалось открыть файл:\n{path}"
            elif validation.code == "unsupported":
                ext = os.path.splitext(path)[1].lower()
                title = "Формат не поддерживается"
                detail = (f"ClipForge принимает MP4, MOV, M4V и WEBM.\nФайл «{os.path.basename(path)}» "
                          f"в формате {ext or 'без расширения'} загрузить не получится.")
            elif validation.code == "empty":
                title, detail = "Пустой файл", f"Файл «{os.path.basename(path)}» весит 0 байт."
            else:
                title = "Файл слишком большой"
                detail = f"Размер {validation.size / 1024 / 1024 / 1024:.2f} ГБ превышает лимит в 4 ГБ."
            show_warning(self, title, detail)
            return
        size = validation.size
        self._last_status = None
        self.video_path = path
        self.video_label.setText(f"{os.path.basename(path)}   ·   {size / 1024 / 1024:.1f} МБ")
        set_role(self.video_label, "")
        self.failed = []
        self.btn_retry.setVisible(False)
        self._update_state()

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        if not self._busy() and any(url.toLocalFile().lower().endswith(VIDEO_EXTENSIONS) for url in urls):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(VIDEO_EXTENSIONS):
                self._use_video(path)
                event.acceptProposedAction()
                return
        event.ignore()

    def _show_history(self):
        UploadHistoryDialog(self, service=self.service).exec()

    def _on_caption(self):
        self._last_status = None
        length = len(self.caption.toPlainText())
        self.counter.setText(f"{length} / {CAPTION_LIMIT}")
        set_role(self.counter, "err" if length > CAPTION_LIMIT else "caption")
        self._update_state()

    def _busy(self):
        return self.thread is not None

    def _on_variants_toggled(self, checked):
        self.db.set("randomize_variants", bool(checked))
        self._update_state()

    def _on_intensity_changed(self, _index):
        self.db.set("randomize_intensity", self.variant_intensity.currentData() or "medium")

    def _update_state(self):
        busy = self._busy()
        caption = self.caption.toPlainText().strip()
        ready = bool(self.video_path and caption and len(caption) <= CAPTION_LIMIT and self.group.count())
        self.btn_start.setEnabled(ready and not busy)
        self.btn_video.setEnabled(not busy)
        self.group.setEnabled(not busy)
        self.chk_variants.setEnabled(not busy)
        self.variant_intensity.setEnabled(not busy and self.chk_variants.isChecked())
        self.caption.setReadOnly(busy)
        self.btn_retry.setVisible(bool(self.failed) and not busy)
        if busy:
            return
        if self._last_status:
            text, role = self._last_status
            self.status.setText(text)
            set_role(self.status, role)
            return
        if not self.group.count():
            self.status.setText("Сначала добавьте аккаунт")
        elif not ready:
            self.status.setText("Нужны видео, подпись и группа")
        else:
            self.status.setText("")

    def _log(self, text):
        self.log.appendPlainText(text)

    def _copy_log(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.log.toPlainText())

    def _usernames(self, tag):
        return self.db.get_accounts_by_tag(tag)

    def _start(self, usernames=None):
        if self._busy():
            return
        caption = self.caption.toPlainText().strip()
        tag = self.group.currentData()
        targets = usernames or self._usernames(tag)
        if not targets:
            show_warning(self, "Нет аккаунтов", f"В группе «{tag}» нет активных аккаунтов.")
            return
        if not self.video_path:
            show_warning(self, "Нет видео", "Выберите файл видео.")
            return
        validation = validate_video_file(self.video_path)
        if not validation.valid:
            self.video_path = None
            self.video_label.setText("Файл не выбран · перетащите видео в окно")
            set_role(self.video_label, "muted")
            self._update_state()
            show_warning(self, "Файл недоступен", f"{validation.detail}. Выберите файл заново.")
            return

        variant_settings = None
        if self.chk_variants.isChecked():
            if not resolve_ffmpeg():
                show_warning(
                    self, "Нужен FFmpeg",
                    "Для уникализации видео нужен FFmpeg.\n"
                    "Установите его и добавьте в PATH или положите ffmpeg.exe в папку ffmpeg\\bin рядом с программой.")
                return
            variant_settings = RandomizerSettings(intensity=self.variant_intensity.currentData() or "medium")

        self.failed = []
        self._active_usernames = list(targets)
        self.last_job = (self.video_path, caption)
        self._last_status = None
        self.db.save_video(self.video_path, caption[:100], caption)

        self.log.clear()
        self._log(f"Видео: {os.path.basename(self.video_path)}")
        proxy = os.environ.get("TIKTOK_PROXY")
        self._log(f"Соединение: {proxy if proxy else 'напрямую или VPN'}")
        delay = int(self.db.get("upload_delay", 0) or 0)
        if delay:
            self._log(f"Пауза между аккаунтами: {delay} с")
        if variant_settings is not None:
            self._log(f"Уникализация: включена ({self.variant_intensity.currentText().lower()})")
        self._log(f"Аккаунтов в очереди: {len(targets)}")
        self._log("")

        self.thread = UploadThread(self.video_path, caption, targets, delay, variant_settings=variant_settings)
        self.thread.line.connect(self._log)
        self.thread.account_result.connect(self._account_done)
        self.thread.finished_all.connect(self._finished)
        self.thread.finished.connect(self._thread_closed)
        self.progress.setRange(0, len(targets))
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.btn_stop.setVisible(True)
        self.btn_stop.setEnabled(True)
        self.status.setText(f"Загрузка идёт: 0 из {len(targets)}")
        set_role(self.status, "muted")
        self.thread.start()
        self._update_state()

    def _retry_failed(self):
        if self.failed and self.last_job:
            path, caption = self.last_job
            self.video_path = path
            if not self.caption.toPlainText().strip():
                self.caption.setPlainText(caption)
            self._start(usernames=list(self.failed))

    def _stop(self):
        if self.thread:
            self.thread.stop_requested = True
            self.btn_stop.setEnabled(False)
            self.status.setText("Остановится после текущего аккаунта")
            set_role(self.status, "muted")

    def _account_done(self, username, ok, error):
        if ok:
            self.db.increment_account_uploads([username])
        self.service.record_upload(
            UploadOutcome(
                username=username,
                video_path=self.video_path or "",
                status="ok" if ok else "error",
                error=error or None,
                caption=self.caption.toPlainText().strip(),
            )
        )
        if username in self._active_usernames:
            self._active_usernames.remove(username)
        if not ok:
            self.failed.append(username)
        self.progress.setValue(self.progress.value() + 1)
        self.status.setText(f"Загрузка идёт: {self.progress.value()} из {self.progress.maximum()}")
        self.accounts_changed.emit()

    def _finished(self, done, total, stopped=False):
        self.btn_stop.setVisible(False)
        self.progress.setVisible(False)
        if stopped:
            for username in self._active_usernames:
                if username not in self.failed:
                    self.failed.append(username)
        self._log("")
        self._log(f"Готово: опубликовано {done} из {total}")
        if stopped:
            self._log("Остановлено пользователем; непройденные аккаунты можно повторить")
        if self.failed:
            self._log(f"Не удалось: {', '.join('@' + name for name in self.failed)}")
        self._last_status = (f"Опубликовано {done} из {total}",
                             "ok" if done == total and total else "muted" if done else "err")
        self._update_state()

    def _thread_closed(self):
        # QThread нельзя удалять, пока он работает: чистим ссылку только здесь.
        thread = self.thread
        self.thread = None
        if thread is not None:
            thread.deleteLater()
        if not self.failed:
            self.video_path = None
            self.video_label.setText("Файл не выбран · перетащите видео в окно")
            set_role(self.video_label, "muted")
            self.caption.clear()
            self.last_job = None
        self._active_usernames = []
        self._update_state()
