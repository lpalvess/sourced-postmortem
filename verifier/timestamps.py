"""Extração de horários, datas e fusos."""
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo

from .model import Stamp

UTC = timezone.utc

_TZ = r"(?:\s?(?P<tzname>Z|UTC|GMT)(?![A-Za-z])|\s?(?P<tzoff>[+-]\d{2}:?\d{2}))?"

_ISO = re.compile(
    r"(?<!\d)(?P<y>\d{4})-(?P<mo>\d{2})-(?P<d>\d{2})[T ](?P<h>\d{2}):(?P<mi>\d{2})"
    r"(?::(?P<s>\d{2})(?:[.,]\d+)?)?" + _TZ + r"(?!\d)"
)
_NGINX = re.compile(
    r"\[?(?P<d>\d{2})/(?P<mon>[A-Za-z]{3})/(?P<y>\d{4}):(?P<h>\d{2}):(?P<mi>\d{2}):(?P<s>\d{2})"
    r"\s(?P<tzoff>[+-]\d{4})\]?"
)
_SLASH = re.compile(
    r"(?<![\d/])(?P<a>\d{1,2})/(?P<b>\d{1,2})/(?P<y>\d{4})[ ,T]+(?P<h>\d{1,2}):(?P<mi>\d{2})"
    r"(?::(?P<s>\d{2}))?" + _TZ + r"(?!\d)"
)
_SYSLOG = re.compile(
    r"(?<![A-Za-z])(?P<mon>[A-Za-z]{3})\s{1,2}(?P<d>\d{1,2})\s(?P<h>\d{2}):(?P<mi>\d{2}):(?P<s>\d{2})(?!\d)"
)
_EPOCH = re.compile(
    r'"(?:startsAt|endsAt|timestamp|ts)"\s*:\s*"?(?P<n>\d{13}|\d{10})(?:\.\d+)?"?'
)
_BARE = re.compile(
    r"(?<![\d:/.])(?P<h>\d{1,2}):(?P<mi>\d{2})(?::(?P<s>\d{2}))?" + _TZ + r"(?![\d:])"
)

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "fev": 2, "abr": 4, "mai": 5, "ago": 8, "set": 9, "out": 10, "dez": 12,
}

_DATE_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_DATE_SLASH = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})/(\d{4})(?![\d/])")

_TZ_TOKEN = (
    r"(UTC\s*[+-]\s*\d{1,2}(?::?\d{2})?|GMT\s*[+-]\s*\d{1,2}(?::?\d{2})?|UTC|GMT"
    r"|[A-Za-z]+/[A-Za-z_]+(?:/[A-Za-z_]+)?)"
)
_TZ_PAREN = re.compile(r"\(\s*" + _TZ_TOKEN + r"\s*\)")
_TZ_DECL = re.compile(
    r"(?i)\b(?:hor[aá]rios?|times?)\b(?:\s+(?:est[aã]o|s[aã]o|are))?(?:\s+(?:em|in))?\s*:?\s*"
    + _TZ_TOKEN
)
_TZ_OFFSET_TOKEN = re.compile(r"(UTC|GMT)\s*([+-])\s*(\d{1,2})(?::?(\d{2}))?", re.I)


@dataclass(frozen=True)
class Hit:
    start: int
    end: int
    stamp: Stamp | None
    assumed_tz: bool = False
    ambiguous: bool = False
    reason: str = ""


def _day_month(a: int, b: int, order: str | None) -> tuple[int, int] | None:
    if order == "DMY":
        return a, b
    if order == "MDY":
        return b, a
    if a > 12 and b <= 12:
        return a, b
    if b > 12 and a <= 12:
        return b, a
    if a == b:
        return a, b
    return None


_BAD_TZ = object()


def _offset(text: str):
    sign = -1 if text[0] == "-" else 1
    digits = text[1:].replace(":", "")
    try:
        return timezone(sign * timedelta(hours=int(digits[:2]), minutes=int(digits[2:])))
    except ValueError:
        return _BAD_TZ


def _explicit_tz(m: re.Match) -> tzinfo | None:
    groups = m.groupdict()
    if groups.get("tzname"):
        return UTC
    if groups.get("tzoff"):
        return _offset(groups["tzoff"])
    return None


def _build(m: re.Match, day: date | None, hour: int, minute: int, second: int | None,
           tz: tzinfo | None, default_tz: tzinfo, precision_seconds: bool) -> Hit:
    if tz is _BAD_TZ:
        return Hit(m.start(), m.end(), None, reason="data inválida")
    assumed = tz is None
    try:
        naive = datetime(day.year, day.month, day.day, hour, minute, second or 0)
    except ValueError:
        return Hit(m.start(), m.end(), None, reason="data inválida")
    when = naive.replace(tzinfo=tz or default_tz).astimezone(UTC)
    return Hit(m.start(), m.end(),
               Stamp(when, "second" if precision_seconds else "minute"), assumed_tz=assumed)


def _int(v: str | None) -> int | None:
    return None if v is None else int(v)


def find_stamps(text: str, *, default_date: date | None = None,
                default_tz: tzinfo = UTC, date_order: str | None = None) -> list[Hit]:
    hits: list[Hit] = []
    taken: list[tuple[int, int]] = []

    def free(m: re.Match) -> bool:
        return not any(m.start() < e and m.end() > s for s, e in taken)

    def add(m: re.Match, hit: Hit) -> None:
        taken.append((m.start(), m.end()))
        hits.append(hit)

    for m in _ISO.finditer(text):
        if not free(m):
            continue
        try:
            day = date(int(m["y"]), int(m["mo"]), int(m["d"]))
        except ValueError:
            add(m, Hit(m.start(), m.end(), None, reason="data inválida"))
            continue
        add(m, _build(m, day, int(m["h"]), int(m["mi"]), _int(m["s"]),
                      _explicit_tz(m), default_tz, m["s"] is not None))

    for m in _NGINX.finditer(text):
        if not free(m):
            continue
        mon = _MONTHS.get(m["mon"].lower())
        try:
            if mon is None:
                raise ValueError
            day = date(int(m["y"]), mon, int(m["d"]))
        except ValueError:
            add(m, Hit(m.start(), m.end(), None, reason="data inválida"))
            continue
        add(m, _build(m, day, int(m["h"]), int(m["mi"]), int(m["s"]),
                      _offset(m["tzoff"]), default_tz, True))

    for m in _SLASH.finditer(text):
        if not free(m):
            continue
        dm = _day_month(int(m["a"]), int(m["b"]), date_order)
        if dm is None:
            add(m, Hit(m.start(), m.end(), None, ambiguous=True, reason="data ambígua"))
            continue
        try:
            day = date(int(m["y"]), dm[1], dm[0])
        except ValueError:
            add(m, Hit(m.start(), m.end(), None, reason="data inválida"))
            continue
        add(m, _build(m, day, int(m["h"]), int(m["mi"]), _int(m["s"]),
                      _explicit_tz(m), default_tz, m["s"] is not None))

    for m in _SYSLOG.finditer(text):
        mon = _MONTHS.get(m["mon"].lower())
        if mon is None or not free(m):
            continue
        if default_date is None:
            add(m, Hit(m.start(), m.end(), None, reason="horário sem ano"))
            continue
        try:
            day = date(default_date.year, mon, int(m["d"]))
        except ValueError:
            add(m, Hit(m.start(), m.end(), None, reason="data inválida"))
            continue
        add(m, _build(m, day, int(m["h"]), int(m["mi"]), int(m["s"]),
                      None, default_tz, True))

    for m in _EPOCH.finditer(text):
        if not free(m):
            continue
        n = int(m["n"])
        if len(m["n"]) == 13:
            n //= 1000
        try:
            when = datetime.fromtimestamp(n, UTC)
        except (OverflowError, OSError, ValueError):
            add(m, Hit(m.start(), m.end(), None, reason="data inválida"))
            continue
        add(m, Hit(m.start(), m.end(), Stamp(when, "second")))

    for m in _BARE.finditer(text):
        if not free(m):
            continue
        h, mi = int(m["h"]), int(m["mi"])
        if h > 23 or mi > 59:
            continue
        if default_date is None:
            add(m, Hit(m.start(), m.end(), None, reason="horário sem data"))
            continue
        add(m, _build(m, default_date, h, mi, _int(m["s"]),
                      _explicit_tz(m), default_tz, m["s"] is not None))

    hits.sort(key=lambda x: x.start)
    return hits


def _dates(text: str, date_order: str | None):
    """Devolve (start, end, date | None) para cada data solta, em ordem."""
    out = []
    for m in _DATE_ISO.finditer(text):
        try:
            d = date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            d = None
        out.append((m.start(), m.end(), d))
    for m in _DATE_SLASH.finditer(text):
        dm = _day_month(int(m[1]), int(m[2]), date_order)
        d = None
        if dm is not None:
            try:
                d = date(int(m[3]), dm[1], dm[0])
            except ValueError:
                d = None
        out.append((m.start(), m.end(), d))
    out.sort(key=lambda x: x[0])
    return out


def find_date(text: str, date_order: str | None = None) -> date | None:
    for _, _, d in _dates(text, date_order):
        if d is not None:
            return d
    return None


def mask_temporal(text: str) -> str:
    spans = [(h.start, h.end) for h in find_stamps(text, default_date=date(2000, 1, 1))]
    spans += [(s, e) for s, e, _ in _dates(text, None)]
    chars = list(text)
    for s, e in spans:
        chars[s:e] = " " * (e - s)
    return "".join(chars)


def tz_from_token(token: str) -> tzinfo | None:
    token = token.strip()
    m = _TZ_OFFSET_TOKEN.fullmatch(token)
    if m:
        hours, minutes = int(m[3]), int(m[4] or 0)
        if hours > 23 or minutes > 59:
            return None
        delta = timedelta(hours=hours, minutes=minutes)
        return timezone(-delta if m[2] == "-" else delta)
    if token.upper() in ("UTC", "GMT"):
        return UTC
    try:
        return ZoneInfo(token)
    except (ValueError, KeyError, OSError):
        return None


def parse_tz_decl(text: str) -> tzinfo | None:
    for rx in (_TZ_PAREN, _TZ_DECL):
        for m in rx.finditer(text):
            tz = tz_from_token(m.group(1))
            if tz is not None:
                return tz
    return None


def tz_name(tz: tzinfo | None) -> str:
    if tz is None:
        return "não declarado (lido como UTC)"
    if tz == UTC:
        return "UTC"
    return str(tz)
