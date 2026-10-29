import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tiktok_uploader.tiktok import assert_success


class Response:
    def __init__(self, status_code):
        self.status_code = status_code
        self.content = b""


def test_upload_module_exposes_snake_case_success_helper():
    assert assert_success("https://example.test", Response(200)) is True
    assert assert_success("https://example.test", Response(500)) is False
