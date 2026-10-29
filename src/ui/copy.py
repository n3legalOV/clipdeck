"""Centralized user-facing copy for the ClipForge application."""

PRODUCT_NAME = "ClipForge"
PRODUCT_TAGLINE = "Публикации и статистика без лишней суеты"
NAV_ITEMS = ("Обзор", "Публикации", "Аккаунты", "Статистика", "Настройки")
STATUS_LABELS = {
    "ok": "Готово",
    "error": "Ошибка",
    "working": "В работе",
    "idle": "Ожидание",
}

_MESSAGES = {
    "missing_video": "Выберите видеофайл для публикации.",
    "group_empty": "В группе «{tag}» нет активных аккаунтов.",
}


def message(key: str, **values) -> str:
    try:
        template = _MESSAGES[key]
    except KeyError as exc:
        raise KeyError(f"Unknown ClipForge message: {key}") from exc
    return template.format(**values)
