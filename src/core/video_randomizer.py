"""Уникализация видео через FFmpeg: контраст, яркость, шум и качество сжатия.

Модуль не зависит от PyQt6 и от TikTok-адаптера: на вход файл и настройки,
на выход — готовый вариант с другим визуальным отпечатком.
"""

import os
import random
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from src.app.contracts import RandomizerSettings, VideoVariant
from src.core.paths import app_dir

INTENSITIES = ("light", "medium", "strong", "random")
NOISE_LEVELS = (5, 10, 15, 20, 25, 30)
CRF_RANGE = (18, 35)
DEFAULT_TIMEOUT = 900

_RANGES = {
    "light": {"contrast": (0.98, 1.02), "brightness": (-0.02, 0.02), "noise": (5, 10), "crf": (20, 24)},
    "medium": {"contrast": (0.95, 1.08), "brightness": (-0.05, 0.05), "noise": (10, 20), "crf": (23, 28)},
    "strong": {"contrast": (0.90, 1.15), "brightness": (-0.10, 0.10), "noise": (20, 30), "crf": (26, 32)},
    "random": {"contrast": (0.90, 1.15), "brightness": (-0.10, 0.10), "noise": (5, 30), "crf": (18, 35)},
}


class RandomizerError(RuntimeError):
    """Уникализация невозможна: нет FFmpeg, битый файл или ошибка кодирования."""


@dataclass(frozen=True)
class VariantParams:
    contrast: float
    brightness: float
    noise: int
    crf: int


def _local_ffmpeg(name: str) -> Path | None:
    for base in (app_dir(), app_dir() / "_internal"):
        candidate = base / "ffmpeg" / "bin" / name
        if candidate.exists():
            return candidate
    return None


def resolve_ffmpeg() -> str | None:
    override = os.environ.get("CLIPFORGE_FFMPEG")
    if override and Path(override).exists():
        return override
    local = _local_ffmpeg("ffmpeg.exe")
    if local:
        return str(local)
    return shutil.which("ffmpeg")


def resolve_ffprobe() -> str | None:
    override = os.environ.get("CLIPFORGE_FFPROBE")
    if override and Path(override).exists():
        return override
    local = _local_ffmpeg("ffprobe.exe")
    if local:
        return str(local)
    return shutil.which("ffprobe")


def pick_params(settings: RandomizerSettings, rng: random.Random | None = None) -> VariantParams:
    rng = rng or random.Random()
    intensity = settings.intensity if settings.intensity in _RANGES else "medium"
    ranges = _RANGES[intensity]
    contrast = round(rng.uniform(*ranges["contrast"]), 3)
    brightness = round(rng.uniform(*ranges["brightness"]), 3)
    noise = settings.noise if settings.noise in NOISE_LEVELS else _pick_noise(ranges["noise"], rng)
    crf = settings.crf if settings.crf and CRF_RANGE[0] <= settings.crf <= CRF_RANGE[1] else rng.randint(*ranges["crf"])
    return VariantParams(contrast, brightness, noise, crf)


def _pick_noise(bounds: tuple[int, int], rng: random.Random) -> int:
    candidates = [level for level in NOISE_LEVELS if bounds[0] <= level <= bounds[1]]
    return rng.choice(candidates)


def build_filter(params: VariantParams) -> str:
    return f"eq=contrast={params.contrast}:brightness={params.brightness},noise=alls={params.noise}:allf=t+u"


def build_command(ffmpeg: str, source: str, destination: str, params: VariantParams,
                  keep_audio: bool = True) -> list[str]:
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-i", str(source),
        "-vf", build_filter(params),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(params.crf),
        "-pix_fmt", "yuv420p", "-map_metadata", "-1", "-movflags", "+faststart",
    ]
    command += ["-c:a", "aac", "-b:a", "128k"] if keep_audio else ["-an"]
    command.append(str(destination))
    return command


def variant_filename(source: str, index: int, account: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", account).strip("_")[:40] or "account"
    return f"{Path(source).stem}-{index:02d}-{safe}.mp4"


def randomize_video(source: str, destination: str, settings: RandomizerSettings | None = None,
                    rng: random.Random | None = None, runner=None,
                    ffmpeg: str | None = None) -> VideoVariant:
    settings = settings or RandomizerSettings()
    source_path = Path(source)
    if not source_path.is_file():
        raise RandomizerError(f"исходный файл не найден: {source_path.name}")
    binary = ffmpeg or resolve_ffmpeg()
    if not binary:
        raise RandomizerError("FFmpeg не найден: положите ffmpeg.exe в папку ffmpeg/bin или добавьте его в PATH")

    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    params = pick_params(settings, rng)
    command = build_command(binary, str(source_path), str(destination_path), params, settings.keep_audio)

    runner = runner or _run
    try:
        result = runner(command)
    except OSError as error:
        raise RandomizerError(f"FFmpeg не запускается: {error}") from error
    if getattr(result, "returncode", 0) != 0:
        detail = _last_error(getattr(result, "stderr", "")) or f"код {result.returncode}"
        raise RandomizerError(f"FFmpeg не смог обработать видео: {detail}")
    if not destination_path.is_file():
        raise RandomizerError("FFmpeg завершился без выходного файла")

    return VideoVariant(
        account="",
        source=str(source_path),
        path=str(destination_path),
        contrast=params.contrast,
        brightness=params.brightness,
        noise=params.noise,
        crf=params.crf,
        size=destination_path.stat().st_size,
    )


def _run(command):
    return subprocess.run(
        command, capture_output=True, text=True, timeout=DEFAULT_TIMEOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _last_error(stderr) -> str:
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8", "replace")
    lines = [line.strip() for line in str(stderr or "").splitlines() if line.strip()]
    return lines[-1] if lines else ""


def clear_variants(directory: str | Path) -> None:
    target = Path(directory)
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)
