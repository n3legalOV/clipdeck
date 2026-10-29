# Task 5 brief — Rework publication flow and history UX

Plan: `docs/superpowers/plans/2026-10-29-clipforge-deep-rework.md`; BASE at task start: `8d510ea` (progress-ledger commit).

Preserve UploadThread, `_start`, `_retry_failed`, drag/drop and upload-log behavior. Implement `validate_video_file(path: str) -> VideoValidation` in `src/app/services.py`, shared by UI and service validation; keep extensions `.mp4/.mov/.m4v/.webm` and 4GB limit. History dialog must retain reload and clear behavior using service. Improve publication layout/copy/status and preserve retries/partial results.

Expected verification: focused upload-flow tests; screenshot script `tests/shots_clipforge.py`; drag/drop enabled; full tests/smoke/compile. Plan step uses Unix-style helper scripts, unavailable in this Windows environment; use ledger and direct pytest equivalents.
