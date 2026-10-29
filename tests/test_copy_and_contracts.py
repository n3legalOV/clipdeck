import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_clipforge_brand_contract_is_stable():
    from src.ui.copy import NAV_ITEMS, PRODUCT_NAME, PRODUCT_TAGLINE, STATUS_LABELS

    assert PRODUCT_NAME == "ClipForge"
    assert PRODUCT_TAGLINE
    assert NAV_ITEMS == ("Обзор", "Публикации", "Аккаунты", "Статистика", "Настройки")
    assert STATUS_LABELS["ok"] == "Готово"
    assert STATUS_LABELS["error"] == "Ошибка"


def test_message_formats_product_copy():
    from src.ui.copy import message

    assert message("missing_video") == "Выберите видеофайл для публикации."
    assert message("group_empty", tag="Тест") == "В группе «Тест» нет активных аккаунтов."


def test_application_contracts_are_typed_data():
    from src.app.contracts import AccountSummary, UploadOutcome, UploadRunSummary

    account = AccountSummary(username="demo", tag="music", status="active", videos_uploaded=2)
    outcome = UploadOutcome(username="demo", video_path="video.mp4", status="ok")
    summary = UploadRunSummary(total=1, succeeded=1, failed=0, stopped=False, outcomes=(outcome,))

    assert account.username == "demo"
    assert outcome.status == "ok"
    assert summary.outcomes == (outcome,)
