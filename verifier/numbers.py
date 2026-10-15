"""Números, quantidades e durações citados em texto."""
import re

from .timestamps import mask_temporal

_UNITS = r"(?:%|por cento|usu[aá]rios|users|clientes|customers|requisi[cç][oõ]es|requests|reqs|erros|errors|pedidos|orders|transa[cç][oõ]es|transactions|ms|s)"
_QTY = re.compile(
    r"(?i)(?<![\w.,])(?P<brl>R\$\s?)?(?P<num>\d+(?:[.,]\d+)*)(?:\s?(?P<unit>" + _UNITS + r"))?(?![\w%])"
)
_NUM = re.compile(r"\d+(?:[.,]\d+)*")

_HM = re.compile(r"(?i)(?<![\w.,:])(?P<h>\d{1,3})\s?h\s?(?P<m>\d{1,2})(?:\s?min)?(?![\w])")
_MIN = re.compile(
    r"(?i)(?<![\w.,:])(?P<n>\d+(?:[.,]\d+)?)\s?(?:min|mins|minuto|minutos|minute|minutes)(?![\w])"
)
_HRS = re.compile(
    r"(?i)(?<![\w.,:])(?P<n>\d+(?:[.,]\d+)?)(?:\s(?:h|hr|hrs)|\s?(?:hora|horas|hour|hours))(?![\w])"
)

_LABELS = (
    ("TTD", re.compile(r"(?i)\bttd\b|time to detect|tempo (?:at[eé]|para) (?:a )?detec")),
    ("TTA", re.compile(r"(?i)\btta\b|time to ack|tempo (?:at[eé]|para) (?:o )?reconhec")),
    ("TTM", re.compile(r"(?i)\bttm\b|time to mitigat|tempo (?:at[eé]|para) (?:a )?mitiga")),
    ("TTR", re.compile(
        r"(?i)\bttr\b|time to resol|time to recover|tempo (?:at[eé]|para) (?:a )?(?:resolu|recupera)"
    )),
    ("duracao", re.compile(r"(?i)dura[cç][aã]o|duration|durou|lasted|\bimpacto\b|\bimpact\b")),
)
_SENTENCE_END = re.compile(r"[.;!?]\s")
_WINDOW = 40


def _canon(s: str) -> str:
    """Forma canônica de uma string de dígitos com ponto decimal opcional.

    Equivale a Decimal(s).normalize() formatado sem expoente, mas sem a
    precisão limitada do contexto Decimal (que arredondaria dígitos longos).
    """
    whole, _, frac = s.partition(".")
    whole = whole.lstrip("0") or "0"
    frac = frac.rstrip("0")
    return f"{whole}.{frac}" if frac else whole


def number_forms(raw: str) -> frozenset[str]:
    raw = raw.strip()
    if not raw or not re.fullmatch(r"\d+(?:[.,]\d+)*", raw):
        return frozenset()
    if raw.isdigit():
        return frozenset({_canon(raw)})
    seps = {c for c in raw if c in ".,"}
    if len(seps) == 2:
        last = max(raw.rfind("."), raw.rfind(","))
        dec_sep = raw[last]
        other = "," if dec_sep == "." else "."
        head, tail = raw[:last], raw[last + 1:]
        if dec_sep not in head and other in head and raw.rfind(other) < last:
            return frozenset({_canon(head.replace(other, "") + "." + tail)})
        return frozenset(_canon(p) for p in re.split(r"[.,]", raw))
    sep = seps.pop()
    parts = raw.split(sep)
    forms: set[str] = set()
    if 1 <= len(parts[0]) <= 3 and all(len(p) == 3 for p in parts[1:]):
        forms.add(_canon("".join(parts)))
    if len(parts) == 2:
        forms.add(_canon(parts[0] + "." + parts[1]))
    if not forms:
        forms = {_canon(p) for p in parts}
    return frozenset(forms)


def extract_quantities(text: str) -> list[tuple[str, frozenset[str]]]:
    out = []
    for m in _QTY.finditer(mask_temporal(text)):
        if not (m.group("unit") or m.group("brl")):
            continue
        out.append((m.group(0).strip(), number_forms(m.group("num"))))
    return out


def extract_numbers(text: str) -> frozenset[str]:
    forms: set[str] = set()
    for m in _NUM.finditer(mask_temporal(text)):
        forms |= number_forms(m.group(0))
    return frozenset(forms)


def _label_for(text: str, start: int) -> str | None:
    window = text[max(0, start - _WINDOW):start]
    cut = None
    for cut in _SENTENCE_END.finditer(window):
        pass
    if cut is not None:
        window = window[cut.end():]
    best: tuple[int, str] | None = None
    for name, rx in _LABELS:
        for m in rx.finditer(window):
            if best is None or m.end() >= best[0]:
                best = (m.end(), name)
    return best[1] if best else None


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def extract_durations(text: str, *, labeled_only: bool = False) -> list[tuple[str, float, str | None]]:
    taken = bytearray(len(text))
    found: list[tuple[int, str, float, str | None]] = []

    def free(s: int, e: int) -> bool:
        return taken.find(1, s, e) == -1

    for rx, kind in ((_HM, "hm"), (_MIN, "min"), (_HRS, "hrs")):
        for m in rx.finditer(text):
            s, e = m.span()
            if not free(s, e):
                continue
            taken[s:e] = b"\x01" * (e - s)
            label = _label_for(text, s)
            if kind == "hm":
                if label is None:
                    continue
                minutes = int(m.group("h")) * 60 + int(m.group("m"))
            elif kind == "min":
                minutes = _num(m.group("n"))
            else:
                minutes = _num(m.group("n")) * 60
            if labeled_only and label is None:
                continue
            found.append((s, m.group(0).strip(), minutes, label))
    found.sort(key=lambda t: t[0])
    return [(raw, minutes, label) for _, raw, minutes, label in found]
