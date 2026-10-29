import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PyQt6.QtWidgets import QApplication

from src.app.services import ClipForgeService
from src.core.database import Database
from src.ui.pages.accounts import AccountsPage
from src.ui.pages.settings import SettingsPage
from src.ui.pages.stats import StatsPage
from src.ui.pages.uploads import UploadsPage


def _labels(page):
    return [widget.text() for widget in page.findChildren(type(page.diag)) if hasattr(widget, "text")]


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_accounts_page_uses_shared_service_and_has_clear_empty_state(qapp):
    with tempfile.TemporaryDirectory() as tmp:
        service = ClipForgeService(Database(os.path.join(tmp, "pages.db")))
        page = AccountsPage(service)
        assert page.db is service.db
        assert page.header.subtitle.text() == "Нет добавленных аккаунтов"
        assert page.empty_title.text() == "Аккаунтов пока нет"
        assert not page.btn_upload.isEnabled()


def test_stats_page_uses_shared_database_and_empty_state(qapp):
    with tempfile.TemporaryDirectory() as tmp:
        service = ClipForgeService(Database(os.path.join(tmp, "stats.db")))
        page = StatsPage(service)
        assert page.db is service.db
        assert page.stack.currentIndex() == 1
        assert page.table.rowCount() == 0
        assert page.header.subtitle.text() == "Ещё не обновлялось"


def test_settings_page_uses_shared_database_and_clipforge_copy(qapp):
    with tempfile.TemporaryDirectory() as tmp:
        service = ClipForgeService(Database(os.path.join(tmp, "settings.db")))
        page = SettingsPage(service)
        assert page.db is service.db
        assert page.windowTitle() == ""
        assert "Публикация" in _labels(page)


def test_uploads_page_persists_variant_toggle(qapp):
    with tempfile.TemporaryDirectory() as tmp:
        service = ClipForgeService(Database(os.path.join(tmp, "uploads.db")))
        page = UploadsPage(service)
        assert page.chk_variants.isChecked() is False
        assert page.variant_intensity.isEnabled() is False

        page.chk_variants.setChecked(True)
        assert service.db.get("randomize_variants") is True
        assert page.variant_intensity.isEnabled() is True

        page.variant_intensity.setCurrentIndex(page.variant_intensity.findData("strong"))
        assert service.db.get("randomize_intensity") == "strong"
