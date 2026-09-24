# Clipdeck

Десктопное приложение для Windows: публикует одно видео сразу на группу TikTok-аккаунтов и показывает статистику роликов.

## Возможности

**Аккаунты**
- Вход через браузер или по кукам (`sessionid`, `tt-target-idc`).
- Группы по тегам, массовая смена тега и удаление.

**Публикация**
- Одно видео на все аккаунты выбранной группы.
- Подпись и хэштеги в одном поле, счётчик до 2200 символов.
- Журнал с причиной ошибки по каждому аккаунту, остановка между аккаунтами.

**Статистика**
- Просмотры, лайки, комментарии, репосты и подписчики по аккаунтам и по каждому ролику.
- Прирост с прошлого обновления, пометки «Растёт», «Без роста», «Нет просмотров».
- Обновление вручную или автоматически (15, 30 минут, час), история за 30 дней.

**Соединение**
- Необязательный прокси (SOCKS5 или HTTP), проверка IP в настройках.
- Все данные (база, куки, настройки) лежат локально рядом с программой.

## Требования

Windows, Python 3.10+, Google Chrome, Node.js.

## Запуск из исходников

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
cd tiktok_uploader\tiktok-signature
npm install
npx playwright install chromium
cd ..\..
venv\Scripts\python main.py
```

Скопируйте `.env.example` в `.env`, если нужен прокси.

## Сборка exe

```bash
venv\Scripts\pip install pyinstaller
venv\Scripts\python -m PyInstaller --noconfirm --clean --windowed --onedir --name Clipdeck ^
  --icon src/ui/assets/icon.ico ^
  --add-data "src/ui/assets;src/ui/assets" ^
  --add-data "tiktok_uploader/tiktok-signature;tiktok_uploader/tiktok-signature" ^
  --collect-all imageio_ffmpeg --collect-data fake_useragent ^
  --collect-submodules moviepy --collect-submodules undetected_chromedriver ^
  --copy-metadata imageio --copy-metadata imageio-ffmpeg --copy-metadata moviepy ^
  --copy-metadata proglog --copy-metadata tqdm --copy-metadata decorator ^
  --copy-metadata numpy --copy-metadata pillow ^
  --hidden-import tiktok_uploader.tiktok --hidden-import tiktok_uploader.stats ^
  --exclude-module playwright --exclude-module aiohttp --exclude-module tkinter main.py
```

Рядом с `Clipdeck.exe` создаются `data/`, `CookiesDir/` и `.env`. Проверка сборки: `Clipdeck.exe --selftest` пишет `selftest.log`.

## Ограничения

- Программа работает через неофициальные запросы TikTok, после его обновлений что-то может перестать работать.
- TikTok может блокировать публикацию на уровне аккаунта или региона.
- Массовая публикация одного видео на много аккаунтов повышает риск ограничений. Используйте только свои аккаунты и соблюдайте правила платформы.
- Куки аккаунтов хранятся в открытом виде в `CookiesDir/`. Не публикуйте эту папку и не передавайте её другим.

## Лицензия и авторство

MIT, см. [LICENSE](LICENSE). Проект основан на [TikTokAutoUploader](https://github.com/y1ki/TikTokAutoUploader) (Y1ki) и использует [tiktok-signature](https://github.com/carcabot/tiktok-signature) (CarcaBot).
