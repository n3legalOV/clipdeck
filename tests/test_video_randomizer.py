import random
from pathlib import Path

import pytest

from src.app.contracts import RandomizerSettings
from src.core.video_randomizer import (
    CRF_RANGE,
    NOISE_LEVELS,
    RandomizerError,
    build_command,
    build_filter,
    pick_params,
    randomize_video,
    resolve_ffmpeg,
    variant_filename,
)


class _Result:
    def __init__(self, returncode=0, stderr=""):
        self.returncode = returncode
        self.stderr = stderr


def _range(settings, field):
    params = pick_params(settings, random.Random(7))
    return getattr(params, field)


def test_params_stay_inside_intensity_ranges():
    for intensity in ("light", "medium", "strong", "random"):
        contrast = _range(RandomizerSettings(intensity=intensity), "contrast")
        brightness = _range(RandomizerSettings(intensity=intensity), "brightness")
        noise = _range(RandomizerSettings(intensity=intensity), "noise")
        crf = _range(RandomizerSettings(intensity=intensity), "crf")
        assert 0.85 <= contrast <= 1.2, (intensity, contrast)
        assert -0.12 <= brightness <= 0.12, (intensity, brightness)
        assert noise in NOISE_LEVELS, (intensity, noise)
        assert CRF_RANGE[0] <= crf <= CRF_RANGE[1], (intensity, crf)


def test_explicit_noise_and_crf_override_random_choice():
    settings = RandomizerSettings(intensity="strong", noise=5, crf=35)
    params = pick_params(settings, random.Random(1))
    assert params.noise == 5
    assert params.crf == 35


def test_unknown_intensity_falls_back_to_medium():
    params = pick_params(RandomizerSettings(intensity="turbo"), random.Random(3))
    assert CRF_RANGE[0] <= params.crf <= CRF_RANGE[1]


def test_filter_and_command_contain_randomization_parameters():
    params = pick_params(RandomizerSettings(intensity="medium"), random.Random(5))
    assert "eq=contrast=" in build_filter(params)
    assert f"noise=alls={params.noise}:allf=t+u" in build_filter(params)

    command = build_command("ffmpeg", "in.mp4", "out.mp4", params, keep_audio=True)
    assert command[0] == "ffmpeg"
    assert "-vf" in command
    assert f"libx264" in command
    assert str(params.crf) in command
    assert command[-1] == "out.mp4"
    assert "-an" not in command
    assert "aac" in command


def test_command_can_drop_audio():
    params = pick_params(RandomizerSettings(), random.Random(2))
    command = build_command("ffmpeg", "in.mp4", "out.mp4", params, keep_audio=False)
    assert "-an" in command
    assert "aac" not in command


def test_variant_filename_is_safe_for_filesystem():
    name = variant_filename("C:/video/my clip.mp4", 3, "@user/name:1")
    assert name == "my clip-03-user_name_1.mp4"


def test_randomize_video_rejects_missing_source(tmp_path):
    with pytest.raises(RandomizerError):
        randomize_video(str(tmp_path / "nope.mp4"), str(tmp_path / "out.mp4"))


def test_randomize_video_requires_ffmpeg(tmp_path, monkeypatch):
    source = tmp_path / "in.mp4"
    source.write_bytes(b"data")
    monkeypatch.setattr("src.core.video_randomizer.resolve_ffmpeg", lambda: None)
    with pytest.raises(RandomizerError) as error:
        randomize_video(str(source), str(tmp_path / "out.mp4"))
    assert "FFmpeg" in str(error.value)


def test_randomize_video_runs_ffmpeg_and_reports_variant(tmp_path):
    source = tmp_path / "in.mp4"
    source.write_bytes(b"0123456789")
    calls = []

    def runner(command):
        calls.append(command)
        Path(command[-1]).write_bytes(b"x" * 42)
        return _Result()

    variant = randomize_video(str(source), str(tmp_path / "out.mp4"),
                              RandomizerSettings(intensity="light"), random.Random(1),
                              runner=runner, ffmpeg="ffmpeg")

    assert calls and calls[0][0] == "ffmpeg"
    assert variant.path.endswith("out.mp4")
    assert variant.size == 42
    assert variant.noise in NOISE_LEVELS
    assert CRF_RANGE[0] <= variant.crf <= CRF_RANGE[1]


def test_randomize_video_surfaces_ffmpeg_error(tmp_path):
    source = tmp_path / "in.mp4"
    source.write_bytes(b"0123456789")

    def runner(command):
        return _Result(returncode=1, stderr="line one\nInvalid data found")

    with pytest.raises(RandomizerError) as error:
        randomize_video(str(source), str(tmp_path / "out.mp4"), runner=runner, ffmpeg="ffmpeg")
    assert "Invalid data found" in str(error.value)


def test_resolve_ffmpeg_finds_binary_on_this_machine():
    binary = resolve_ffmpeg()
    if binary is None:
        pytest.skip("FFmpeg не установлен")
    assert Path(binary).exists()
