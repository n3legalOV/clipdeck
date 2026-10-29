"""Разбор списка аккаунтов, вставленного текстом.

Поддерживаются строки, скопированные из таблиц (табуляция), из Excel/CSV
(запятая или точка с запятой), а также «сырые» строки вида
`username sessionid useast5`. Порядок первых двух полей может быть любым:
sessionid узнаётся по длине и hex-содержимому, dc — по виду `useast2a`.
"""

import re

_SESSION_RE = re.compile(r"^[0-9a-f]{20,}$", re.IGNORECASE)
_DC_RE = re.compile(r"^(useast\d{0,2}[a-z]?|maliva\d{0,2}|alisg\d{0,2}|euw?\d{0,2}[a-z]?|va\d{0,2}[a-z]?|sg\d{0,2}[a-z]?|jp\d{0,2}[a-z]?)$",
                    re.IGNORECASE)
_SPLIT_RE = re.compile(r"[\t;|,]+")
_USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{1,40}$")


def _tokens(line):
    parts = [p.strip() for p in _SPLIT_RE.split(line)]
    parts = [p for p in parts if p]
    if len(parts) > 1:
        return parts
    return [p for p in line.split() if p]


def parse_line(line):
    """Возвращает dict(username, sessionid, dc_id) или None, если строку не разобрать."""
    tokens = [t.strip().strip('"').strip("'") for t in _tokens(line)]
    tokens = [t for t in tokens if t]
    if not tokens:
        return None

    username = None
    sessionid = None
    dc_id = None
    rest = []

    for token in tokens:
        if token.startswith("@"):
            username = token[1:].strip()
        elif _SESSION_RE.match(token) and len(token) >= 24:
            sessionid = token
        elif _DC_RE.match(token) and not _SESSION_RE.match(token):
            dc_id = token
        else:
            rest.append(token)

    if username is None and rest:
        username = rest.pop(0)
    if username is None and dc_id:
        # Строка из одного "похожего на dc" слова — это, скорее, логин.
        username, dc_id = dc_id, None
    if username is not None:
        username = username.lstrip("@").strip()

    if not username or not _USERNAME_RE.match(username):
        return None
    if sessionid is None:
        return None
    return {"username": username, "sessionid": sessionid, "dc_id": dc_id or "useast5"}


def parse_accounts(text):
    """Разбирает многострочный текст.

    Возвращает (аккаунты, ошибки) — аккаунты уникальны по username,
    ошибки — номера строк, которые не удалось разобрать.
    """
    accounts = []
    errors = []
    seen = set()
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        item = parse_line(line)
        if not item:
            errors.append(number)
            continue
        key = item["username"].lower()
        if key in seen:
            continue
        seen.add(key)
        accounts.append(item)
    return accounts, errors
