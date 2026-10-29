"""Application use cases shared by ClipForge pages and entry points."""

import os
import shutil
import subprocess
from pathlib import Path

from src.app.contracts import (
    DiagnosticResult,
    ImportSummary,
    UploadOutcome,
    UploadRequest,
    VideoValidation,
)
from src.core.account_import import parse_accounts
from src.core.database import Database
from src.core.paths import app_dir
from src.core.video_randomizer import resolve_ffmpeg

VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v", ".webm")
MAX_VIDEO_BYTES = 4 * 1024 ** 3


def validate_video_file(path: str) -> VideoValidation:
    video = Path(path)
    if not video.is_file():
        return VideoValidation(False, "missing", "video file not found")
    if video.suffix.lower() not in VIDEO_EXTENSIONS:
        return VideoValidation(False, "unsupported", "unsupported video format")
    size = video.stat().st_size
    if size == 0:
        return VideoValidation(False, "empty", "video file is empty")
    if size > MAX_VIDEO_BYTES:
        return VideoValidation(False, "too_large", "video file exceeds 4 GB", size)
    return VideoValidation(True, "ok", "", size)


class ClipForgeService:
    def __init__(self, db: Database | None = None):
        self.db = db or Database()

    def list_account_groups(self) -> list[tuple[str, int]]:
        rows = self.db.fetchall(
            "SELECT tag, COUNT(*) FROM accounts "
            "WHERE status = 'active' AND tag IS NOT NULL GROUP BY tag ORDER BY tag"
        )
        return [(str(tag), int(count)) for tag, count in rows]

    def import_accounts(self, text: str, default_tag: str | None = None) -> ImportSummary:
        accounts, errors = parse_accounts(text)
        tag = (default_tag or "default").strip() or "default"
        added = 0
        updated = 0
        existing = {
            str(row[1]).casefold(): row[1]
            for row in self.db.get_accounts()
            if row[1]
        }
        for account in accounts:
            username = account["username"]
            canonical = existing.get(username.casefold(), username)
            existed = canonical.casefold() in existing
            cookie_name = f"tiktok_session-{canonical}.cookie"
            self.db.save_account(canonical, cookie_name, tag=tag)
            existing[canonical.casefold()] = canonical
            if existed:
                updated += 1
            else:
                added += 1
        return ImportSummary(added, updated, tuple(errors))

    def prepare_upload(self, video_path: str, caption: str, tag: str) -> UploadRequest:
        validation = validate_video_file(video_path)
        if not validation.valid:
            raise ValueError(validation.detail)
        clean_caption = caption.strip()
        if not clean_caption:
            raise ValueError("caption is required")
        clean_tag = tag.strip()
        if not clean_tag:
            raise ValueError("group is required")
        usernames = tuple(self.db.get_accounts_by_tag(clean_tag))
        if not usernames:
            raise ValueError("group has no active accounts")
        return UploadRequest(str(video_path), clean_caption, clean_tag, usernames)

    def record_upload(self, outcome: UploadOutcome) -> None:
        self.db.log_upload(
            outcome.username,
            outcome.status,
            video_path=outcome.video_path,
            caption=outcome.caption,
            error=outcome.error,
        )

    def recent_uploads(self, limit: int = 100) -> list[UploadOutcome]:
        return [
            UploadOutcome(
                username=username,
                video_path=video_path or "",
                status=status,
                error=error,
                created_at=created_at,
                caption=caption,
            )
            for username, video_path, caption, status, error, created_at
            in self.db.get_upload_log(limit)
        ]

    def clear_upload_history(self) -> None:
        self.db.clear_upload_log()

    def diagnostics(self) -> list[DiagnosticResult]:
        results = []
        node = shutil.which("node")
        if not node:
            results.append(DiagnosticResult("Node.js", "error", "не найден в PATH"))
        else:
            try:
                version = subprocess.check_output(
                    [node, "--version"], stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                ).decode().strip()
                results.append(DiagnosticResult("Node.js", "ok", version))
            except Exception:
                results.append(DiagnosticResult("Node.js", "warning", "найден, но не запускается"))

        for module, label in (("undetected_chromedriver", "Вход через браузер"), ("playwright", "Статистика")):
            try:
                __import__(module)
                results.append(DiagnosticResult(label, "ok", "пакет установлен"))
            except Exception:
                results.append(DiagnosticResult(label, "warning", f"пакет {module} не установлен"))

        ffmpeg = resolve_ffmpeg()
        if ffmpeg:
            results.append(DiagnosticResult("FFmpeg", "ok", ffmpeg))
        else:
            results.append(DiagnosticResult("FFmpeg", "warning", "не найден — уникализация видео недоступна"))

        cookies = app_dir() / "CookiesDir"
        count = len(list(cookies.glob("*.cookie"))) if cookies.exists() else 0
        results.append(DiagnosticResult("Локальные данные", "ok", f"куков: {count}; папка: {app_dir()}"))
        return results
