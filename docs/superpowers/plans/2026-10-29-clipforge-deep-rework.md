# ClipForge Deep Rework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Переработать Clipdeck в самостоятельный продукт ClipForge с новой айдентикой, application-слоем, обновлённым UI и документацией, сохранив рабочие TikTok-сценарии и локальные данные.

**Architecture:** Стабильный `tiktok_uploader/` остаётся изолированным интеграционным адаптером. В `src/app/` добавляется слой use cases/services между UI и существующими core-компонентами; UI получает новый shell, бренд и словарь интерфейса. Миграции SQLite версионируются и выполняются без удаления базы/cookies.

**Tech Stack:** Python 3.10+, PyQt6, SQLite, pytest, PyInstaller, текущий Node/Playwright signer.

**Spec:** `docs/superpowers/specs/2026-10-29-clipforge-deep-rework-design.md`

## Global Constraints

- Рабочее имя продукта: `ClipForge`.
- Сохраняются Python/PyQt6/SQLite и текущий TikTok-адаптер.
- Существующая база SQLite и cookies не удаляются.
- Старые self-test/launch entry points продолжают работать через совместимые алиасы.
- LICENSE, copyright и атрибуция `TikTokAutoUploader`/`tiktok-signature` сохраняются.
- Не добавлять сетевые сервисы и обязательные новые зависимости без необходимости.
- Реальный TikTok upload/login не считается локально проверенным без пользовательских аккаунтов.

## Review Focus

- Миграция старой базы: старая схема и пустая/повреждённая БД должны давать понятный результат и не уничтожать файл — тест в задаче 2.
- Частично успешная публикация: успехи, ошибки, остановка и retry должны сохранять прежнюю семантику — тест в задаче 4.
- Пропавший или неподдерживаемый видеофайл: публикация не стартует и UI возвращается в корректное состояние — тест в задаче 5.
- Пустые/неполные данные аккаунтов и дубли при импорте: импорт идемпотентен и не создаёт дубликаты — тест в задаче 3.
- Чистый запуск без `.env`, Node или Chrome: приложение открывается, диагностика сообщает проблему, а не падает при импорте — тест в задаче 7.

---

## File Map

- Create `src/app/__init__.py`, `src/app/contracts.py`, `src/app/services.py`: application DTO/use cases и фасад операций для UI.
- Create `src/ui/copy.py`: единый словарь бренда, навигации, статусов и пользовательских сообщений.
- Modify `src/core/database.py`: версия схемы и безопасная миграция с backup перед изменениями.
- Modify `src/core/app.py`, `src/ui/windows/main.py`, `src/ui/components/sidebar.py`, `src/ui/styles.py`: новый ClipForge shell и визуальная система.
- Modify `src/ui/pages/accounts.py`, `src/ui/pages/uploads.py`, `src/ui/pages/stats.py`, `src/ui/pages/settings.py`: подключение сервисов, обновлённые тексты и UX.
- Modify `src/ui/dialogs/*.py`, `src/ui/components/*.py`: единые тексты/статусы и новый бренд там, где отображается продукт.
- Modify `main.py`, `README.md`, `requirements.txt`: entry point, документация, сборка и диагностика.
- Create `docs/ARCHITECTURE.md`, `docs/RELEASE.md`, `docs/THIRD_PARTY.md`: архитектура, релиз и честная атрибуция.
- Modify/create `tests/test_app_services.py`, `tests/test_database.py`, `tests/smoke_gui.py`, `tests/shots_clipforge.py`: тесты use cases, миграций и UI.

---

### Task 1: Brand contract and application contracts

**Files:**
- Create: `src/ui/copy.py`
- Create: `src/app/__init__.py`
- Create: `src/app/contracts.py`
- Test: `tests/test_copy_and_contracts.py`

**Interfaces:**
- Produce `PRODUCT_NAME = "ClipForge"`, `PRODUCT_TAGLINE`, `NAV_ITEMS`, `STATUS_LABELS` and `message(key: str, **values) -> str`.
- Produce dataclasses `AccountSummary`, `UploadOutcome`, `UploadRunSummary` with explicit typed fields used by later services/pages.

- [ ] **Step 1: Write failing tests** for the exact brand name, four/five navigation labels, formatted error messages, and dataclass construction.
- [ ] **Step 2: Run** `pytest tests/test_copy_and_contracts.py -q`; expect failure because modules do not exist.
- [ ] **Step 3: Implement** the copy dictionary and immutable dataclasses without importing PyQt6.
- [ ] **Step 4: Run** the focused test and then `pytest tests -q` to ensure no existing regression.
- [ ] **Step 5: Commit** `feat: add ClipForge brand and application contracts`.

### Task 2: Versioned database migration

**Files:**
- Modify: `src/core/database.py`
- Modify: `tests/test_database.py`
- Create: `tests/test_database_migrations.py`

**Interfaces:**
- Add `Database.SCHEMA_VERSION` and `Database.schema_version() -> int`.
- Add `Database.backup_before_migration() -> Path | None`.
- Keep existing public methods (`save_account`, `log_upload`, `get_upload_log`, settings and stats methods) compatible.

- [ ] **Step 1: Write failing tests** for a fresh DB reaching current schema, an old DB migrating without losing accounts/upload log, and backup creation before a destructive schema change.
- [ ] **Step 2: Run** `pytest tests/test_database_migrations.py -q`; expect failure for missing version/backup behavior.
- [ ] **Step 3: Implement** `PRAGMA user_version`, ordered migrations, idempotent table/column creation, and a timestamped `.bak` beside the DB before migration.
- [ ] **Step 4: Run** migration tests plus `pytest tests/test_database.py -q` and verify all existing records remain queryable.
- [ ] **Step 5: Commit** `feat: version local database schema safely`.

### Task 3: Application service facade

**Files:**
- Create: `src/app/services.py`
- Modify: `src/core/account_import.py` only where a compatibility adapter is needed
- Create: `tests/test_app_services.py`

**Interfaces:**
- `class ClipForgeService` accepts optional `db: Database` and exposes:
  - `list_account_groups() -> list[tuple[str, int]]`
  - `import_accounts(text: str, default_tag: str | None = None) -> ImportSummary`
  - `prepare_upload(video_path: str, caption: str, tag: str) -> UploadRequest`
  - `record_upload(outcome: UploadOutcome) -> None`
  - `recent_uploads(limit: int = 100) -> list[UploadOutcome]`
  - `clear_upload_history() -> None`
  - `diagnostics() -> list[DiagnosticResult]`
- The service must delegate to existing DB/import/diagnostics behavior rather than duplicate SQL in pages.

- [ ] **Step 1: Write failing tests** for group listing, idempotent import, upload request validation, recording success/error, and history clearing.
- [ ] **Step 2: Run** `pytest tests/test_app_services.py -q`; expect failure.
- [ ] **Step 3: Implement** thin use cases and typed result objects, preserving current import and upload-log semantics.
- [ ] **Step 4: Run** focused tests and the complete existing suite.
- [ ] **Step 5: Commit** `feat: introduce ClipForge application services`.

### Task 4: New application shell and visual system

**Files:**
- Modify: `src/core/app.py`
- Modify: `src/ui/windows/main.py`
- Modify: `src/ui/components/sidebar.py`
- Modify: `src/ui/styles.py`
- Modify: `src/ui/copy.py`
- Test: `tests/smoke_gui.py`

**Interfaces:**
- `MainWindow` title is `ClipForge`; it uses the shared `ClipForgeService` instance and exposes pages in this order: overview, uploads, accounts, stats, settings.
- `Sidebar.ITEMS` comes from `NAV_ITEMS`; `Sidebar.set_connection(proxy: str)` remains compatible.
- Add an overview page at `src/ui/pages/overview.py` with `refresh()` and service-backed summary cards.

- [ ] **Step 1: Add a failing smoke assertion** that the main window title/brand is ClipForge and the overview is the first page.
- [ ] **Step 2: Run** `QT_QPA_PLATFORM=offscreen .venv\Scripts\python tests\smoke_gui.py`; expect assertion failure.
- [ ] **Step 3: Implement** the new shell, sidebar labels, overview page, violet/amber ClipForge palette, active navigation state, and shared service injection. Keep page signals compatible while changing page order through named indices/constants rather than magic numbers.
- [ ] **Step 4: Run** smoke GUI and screenshot script at offscreen plus compileall.
- [ ] **Step 5: Commit** `feat: build ClipForge application shell`.

### Task 5: Rework publication flow and history UX

**Files:**
- Modify: `src/ui/pages/uploads.py`
- Modify: `src/ui/dialogs/upload_history.py`
- Modify: `src/ui/dialogs/styled_dialogs.py`
- Modify: `src/ui/components/common.py`
- Test: `tests/test_upload_flow.py`, `tests/shots_clipforge.py`

**Interfaces:**
- Preserve `UploadThread`, `_start`, `_retry_failed`, drag/drop support and upload-log recording.
- Add service-backed validation `validate_video_file(path: str) -> VideoValidation` and keep accepted extensions/4 GB limit unchanged.
- History dialog continues to support `reload()` and clearing through the service/DB facade.

- [ ] **Step 1: Write failing tests** for missing file, unsupported extension, partial results, retry list and history status rendering.
- [ ] **Step 2: Run** `pytest tests/test_upload_flow.py -q`; expect failure for extracted validation/service behavior.
- [ ] **Step 3: Implement** the new guided publication layout, ClipForge copy, status cards, clear empty state, service delegation and regression-safe thread behavior.
- [ ] **Step 4: Run** focused tests, `tests/shots_clipforge.py`, and verify drag/drop remains enabled.
- [ ] **Step 5: Commit** `feat: redesign ClipForge publication workflow`.

### Task 6: Rework accounts, statistics and settings pages

**Files:**
- Modify: `src/ui/pages/accounts.py`
- Modify: `src/ui/pages/stats.py`
- Modify: `src/ui/pages/settings.py`
- Modify: `src/ui/components/accounts_table.py`
- Modify: `src/ui/dialogs/login.py`, `src/ui/dialogs/import_accounts.py`, `src/ui/dialogs/add_account.py`
- Tests: `tests/test_account_import.py`, `tests/shots_clipforge.py`

**Interfaces:**
- Preserve existing public page methods/signals (`refresh`, `accounts_changed`, `go_upload`, proxy changes, CSV export).
- All visible product strings come from `src/ui/copy.py` or page-local constants derived from it.
- Diagnostics must remain lazy: missing Chrome/Node/packages appears as a result, not an import-time crash.

- [ ] **Step 1: Extend failing tests** for duplicate import, empty account state, stats refresh/export, and missing runtime diagnostics.
- [ ] **Step 2: Run** focused tests; expect failures for new labels and service wiring.
- [ ] **Step 3: Implement** coherent empty states, account grouping/actions, stats cards/tables, settings diagnostics and consistent ClipForge terminology without changing data semantics.
- [ ] **Step 4: Run** all unit tests and screenshot/smoke checks.
- [ ] **Step 5: Commit** `feat: refresh ClipForge account stats and settings UX`.

### Task 7: Entry points, packaging and documentation

**Files:**
- Modify: `main.py`
- Modify: `README.md`
- Modify: `requirements.txt` only if a currently installed dependency is missing
- Create: `docs/ARCHITECTURE.md`
- Create: `docs/RELEASE.md`
- Create: `docs/THIRD_PARTY.md`
- Test: `tests/test_selftest.py`

**Interfaces:**
- `main.py --selftest` continues to create `selftest.log`; output starts with `ClipForge self-test` and retains actionable component checks.
- PyInstaller command uses `--name ClipForge` and the same signer/data collection requirements.
- README presents ClipForge as a substantially reworked fork and links to third-party attribution.

- [ ] **Step 1: Write failing tests** for self-test brand, clean-environment diagnostics and README/third-party references.
- [ ] **Step 2: Run** focused tests; expect failure on old Clipdeck strings.
- [ ] **Step 3: Implement** entry-point branding, docs, build command and explicit attribution without removing LICENSE.
- [ ] **Step 4: Run** `main.py --selftest`, verify `selftest.log`, and run a PyInstaller dry build if the environment has PyInstaller installed.
- [ ] **Step 5: Commit** `docs: publish ClipForge project and release guide`.

### Task 8: Final audit and release verification

**Files:**
- Modify: any files needed for stale user-facing references or compatibility fixes
- Test: `tests/smoke_gui.py`, `tests/shots_clipforge.py`, all existing tests

- [ ] **Step 1: Search** for `Clipdeck`, old window title, old sidebar labels and accidental copied product text; classify each remaining hit as required historical attribution or stale UI.
- [ ] **Step 2: Run** complete verification:
  - `.venv\Scripts\python -m pytest tests -q`
  - `.venv\Scripts\python -m compileall -q src tiktok_uploader main.py`
  - `$env:QT_QPA_PLATFORM='offscreen'; .venv\Scripts\python tests\smoke_gui.py`
  - `$env:QT_QPA_PLATFORM='offscreen'; .venv\Scripts\python tests\shots_clipforge.py`
  - `.venv\Scripts\python main.py --selftest`
- [ ] **Step 3: Inspect** `git diff --check`, clean working tree, generated artifacts and migration backup behavior.
- [ ] **Step 4: Commit** final compatibility/cleanup changes as `chore: finalize ClipForge rework`.

## Verification and handoff

After all tasks, report the exact test outputs, list any checks that require real TikTok accounts, and explicitly distinguish source-verified behavior from network behavior not run locally.
