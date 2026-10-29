# ClipForge architecture

ClipForge is a Windows desktop application built with Python, PyQt6 and SQLite. The UI is organized as a shell with overview, publications, accounts, statistics and settings pages.

## Layers

- `src/ui/` contains pages, dialogs and reusable widgets. Pages keep user interaction and presentation logic.
- `src/app/` contains typed contracts and `ClipForgeService`, the application facade used by pages for validation, account groups, publication history and diagnostics.
- `src/core/` contains the local database, cookie storage, statistics store and compatibility-oriented infrastructure.
- `src/core/video_randomizer.py` builds per-account video variants with FFmpeg: it picks randomized contrast, brightness, noise and CRF values, runs the encoder in a temporary folder under `data/variants/` and removes it after the run. It has no PyQt6 or TikTok dependency, so it is testable on its own.
- `tiktok_uploader/` remains an isolated integration adapter for the unofficial TikTok operations and the existing Node signer.

## Data and compatibility

The database and cookie files remain local to the application directory. SQLite schema versioning uses `PRAGMA user_version` and creates a timestamped backup before migration. Existing public database methods and legacy entry points remain available so existing installations can be opened without a cloud service.

ClipForge does not add a mandatory server, account backend or telemetry service. Network access is limited to the existing TikTok adapter, optional proxy/IP check and statistics workflows.
