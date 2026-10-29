import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_selftest_log_starts_with_clipforge_brand(tmp_path):
    env = os.environ.copy()
    env["CLIPFORGE_DATA_DIR"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "main.py", "--selftest"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert result.returncode == 0
    log = (ROOT / "selftest.log").read_text(encoding="utf-8")
    assert log.startswith("ClipForge self-test\n")
    assert "database" in log.lower()
    (ROOT / "selftest.log").unlink(missing_ok=True)


def test_docs_and_readme_present_clipforge_identity_and_attribution():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# ClipForge")
    assert "substantially reworked" in readme
    assert "THIRD_PARTY.md" in readme
    assert "--name ClipForge" in readme
    assert "TikTokAutoUploader" in readme
    assert (ROOT / "docs" / "ARCHITECTURE.md").exists()
    assert (ROOT / "docs" / "RELEASE.md").exists()
    assert (ROOT / "docs" / "THIRD_PARTY.md").exists()
