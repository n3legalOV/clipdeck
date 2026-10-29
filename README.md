# ClipForge

ClipForge — самостоятельное Windows-приложение для публикации одного видео на группу TikTok-аккаунтов и просмотра статистики роликов. Это substantially reworked open-source fork: новая айдентика, shell-навигация, application-слой, локальные миграции базы и обновлённый пользовательский сценарий при сохранении рабочих локальных данных и интеграционного адаптера.

## Возможности

**Обзор и аккаунты**
- Обзор числа аккаунтов, групп, публикаций и ошибок.
- Вход через браузер (интерфейс не замирает, вход можно отменить) или по кукам (`sessionid`, `tt-target-idc`).
- Массовый импорт списка: вставьте строки `логин  sessionid  tt-target-idc` — порядок полей и разделитель любые, данные из Excel тоже подходят.
- Группы по тегам, массовая смена тега и удаление, поиск по аккаунтам и фильтр по тегу.

**Публикации**
- Пошаговый сценарий: видео → подпись → группа аккаунтов.
- Одно видео на все аккаунты выбранной группы; пауза между аккаунтами настраивается в «Настройках».
- Уникализация: по желанию для каждого аккаунта собирается своя версия видео — FFmpeg меняет контраст, яркость, шум и качество сжатия (лёгкая, средняя, сильная или случайная интенсивность).
- Перетаскивание видео в окно, проверка формата, пустого файла и лимита 4 ГБ.
- Остановка на полпути, повтор ошибок, журнал с причиной по каждому аккаунту и копирование журнала.
- История публикаций в базе с временем, аккаунтом, видео, статусом и причиной ошибки.

**Статистика**
- Просмотры, лайки, комментарии, репосты и подписчики по аккаунтам и роликам.
- Прирост с прошлого обновления, пометки «Растёт», «Без роста», «Нет просмотров».
- Обновление вручную или автоматически (15, 30 минут, час), экспорт в CSV.

**Соединение и обслуживание**
- Необязательный прокси (SOCKS5 или HTTP) для запросов, проверка IP в настройках.
- Ленивые диагностики Node.js, Chrome, Python-пакетов и локальных cookie-файлов.
- Все данные (база, куки, настройки) лежат локально рядом с программой; схема SQLite версионируется и резервируется перед миграцией.

## Требования

Windows, Python 3.10+, Google Chrome, Node.js. Для уникализации видео нужен FFmpeg (в PATH или `ffmpeg\bin\ffmpeg.exe` рядом с программой).

## Запуск из исходников

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cd tiktok_uploader\tiktok-signature
npm install
npx playwright install chromium
cd ..\..
.venv\Scripts\python main.py
```

Скопируйте `.env.example` в `.env`, если нужен прокси.

Проверка окружения: `.venv\Scripts\python main.py --selftest` — результат в `selftest.log`. То же доступно в приложении: «Настройки» → «Проверить окружение».

## Сборка exe

```powershell
.venv\Scripts\pip install pyinstaller
.venv\Scripts\python -m PyInstaller --noconfirm --clean --windowed --onedir --name ClipForge `
  --icon src/ui/assets/icon.ico `
  --add-data "src/ui/assets;src/ui/assets" `
  --add-data "tiktok_uploader/tiktok-signature;tiktok_uploader/tiktok-signature" `
  --collect-data fake_useragent `
  --collect-submodules undetected_chromedriver `
  --hidden-import tiktok_uploader.tiktok --hidden-import tiktok_uploader.stats `
  --exclude-module playwright --exclude-module aiohttp --exclude-module tkinter main.py
```

Рядом с `ClipForge.exe` создаются `data/`, `CookiesDir/` и `.env`. Проверка сборки: `ClipForge.exe --selftest` пишет `selftest.log`.

## Тесты

```powershell
.venv\Scripts\python -m pytest tests -q
.venv\Scripts\python -m compileall -q src tiktok_uploader main.py
$env:QT_QPA_PLATFORM='offscreen'; .venv\Scripts\python tests\smoke_gui.py
$env:QT_QPA_PLATFORM='offscreen'; .venv\Scripts\python tests\shots_clipforge.py
```

## Если что-то не работает

| Симптом | Причина и решение |
| --- | --- |
| «Не удалось загрузить модуль загрузки» | не хватает пакета из `requirements.txt` — установите его |
| «Node.js не найден в PATH» | установите Node.js и перезапустите программу |
| Статистика падает с ошибкой Playwright | в `tiktok_uploader\tiktok-signature` выполните `npm install` и `npx playwright install chromium` |
| Вход через браузер не открывается | Chrome не найден или устарел: проверьте «Настройки» → «Проверить окружение» |
| «Для уникализации видео нужен FFmpeg» | установите FFmpeg и добавьте в PATH либо положите `ffmpeg.exe` в папку `ffmpeg\bin` рядом с программой |
| «сессия недействительна» | куки протухли, войдите в аккаунт заново |

## Ограничения

- Программа работает через неофициальные запросы TikTok, поэтому обновления платформы могут временно нарушить интеграцию.
- TikTok может блокировать публикацию на уровне аккаунта или региона.
- Массовая публикация одного видео на много аккаунтов повышает риск ограничений. Используйте только свои аккаунты и соблюдайте правила платформы.
- Куки аккаунтов хранятся в открытом виде в `CookiesDir/`. Не публикуйте эту папку и не передавайте её другим.
- Реальный login/upload требует пользовательских аккаунтов и не входит в локальный smoke-тест.

## Лицензия и авторство

MIT, см. [LICENSE](LICENSE). История переработки и сторонние компоненты описаны в [docs/THIRD_PARTY.md](docs/THIRD_PARTY.md). Архитектура — в [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), релизная проверка — в [docs/RELEASE.md](docs/RELEASE.md). ClipForge сохраняет атрибуцию [TikTokAutoUploader](https://github.com/y1ki/TikTokAutoUploader) (Y1ki) и [tiktok-signature](https://github.com/carcabot/tiktok-signature) (CarcaBot).
