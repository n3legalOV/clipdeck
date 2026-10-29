from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AccountSummary:
    username: str
    tag: Optional[str]
    status: str
    videos_uploaded: int


@dataclass(frozen=True)
class UploadOutcome:
    username: str
    video_path: str
    status: str
    error: Optional[str] = None
    created_at: Optional[str] = None
    caption: Optional[str] = None


@dataclass(frozen=True)
class UploadRunSummary:
    total: int
    succeeded: int
    failed: int
    stopped: bool
    outcomes: tuple[UploadOutcome, ...]


@dataclass(frozen=True)
class ImportSummary:
    added: int
    updated: int
    invalid_lines: tuple[int, ...]


@dataclass(frozen=True)
class UploadRequest:
    video_path: str
    caption: str
    tag: str
    usernames: tuple[str, ...]


@dataclass(frozen=True)
class VideoValidation:
    valid: bool
    code: str
    detail: str
    size: int = 0


@dataclass(frozen=True)
class DiagnosticResult:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class RandomizerSettings:
    intensity: str = "medium"
    keep_audio: bool = True
    noise: Optional[int] = None
    crf: Optional[int] = None


@dataclass(frozen=True)
class VideoVariant:
    account: str
    source: str
    path: str
    contrast: float
    brightness: float
    noise: int
    crf: int
    size: int
