"""TikTok uploader package.

Модули подгружаются лениво: приложению для публикации и статистики нужны
только `tiktok`, `cookies`, `Config` и `bot_utils`. Тяжёлые зависимости
(moviepy, yt_dlp, undetected_chromedriver) подтягиваются только если их
действительно импортируют — иначе один отсутствующий пакет ломал весь
импорт `tiktok_uploader`.
"""

from .basics import eprint

__all__ = [
    "eprint",
    "tiktok",
    "cookies",
    "Config",
    "Browser",
    "Video",
    "bot_utils",
    "stats",
]

_LAZY = {
    "tiktok": ".tiktok",
    "cookies": ".cookies",
    "Config": ".Config",
    "Browser": ".Browser",
    "Video": ".Video",
    "bot_utils": ".bot_utils",
    "stats": ".stats",
}


def __getattr__(name):
    if name in _LAZY:
        import importlib

        return importlib.import_module(_LAZY[name], __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(__all__)
