"""Leitura do postmortem: seções, metadados, timeline, ações e fatores."""
import re
from datetime import date
from pathlib import Path

from verifier.config import Config
from verifier.model import (Action, Document, Duration, Factor, InputError,
                            Quantity, Section, TimelineEntry, Unparsed)
from verifier.numbers import extract_durations, extract_quantities
from verifier.redact import redact
from verifier.text import norm, strip_markup, word_in
from verifier.timestamps import UTC, find_date, find_stamps, mask_temporal, parse_tz_decl

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
TABLE_ROW = re.compile(r"^\s*\|(.*)\|\s*$")
SEP_ROW = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?\s*$")
TAG = re.compile(r"\[(in[ií]cio|detec[cç][aã]o|reconhecimento|mitiga[cç][aã]o|fim)\]", re.I)
_META = re.compile(r"(?i)^\s*(?:[-*+]\s*)?\**\s*(data do incidente|incident date|data|date|severidade|severity)\s*\**\s*:\s*\**\s*(.+?)\s*$")
_SEV = re.compile(r"(?i)\bsev\s*-?\s*([0-4])\b")
_VAGUE = re.compile(r"(?i)(cerca de|aproximadamente|\baprox\b|~\s*\d|\baround\b|\bapprox\b|por volta)")
_PREFIX_OK = re.compile(r"(?i)^[\s|*_~-]*(?:(?:cerca de|aproximadamente|aprox\.?|around|approx\.?|por volta d[ae]s?)\s*)?[\s~]*$")
_LABEL_HINT = re.compile(r"(?i)\b(?:ttd|tta|ttm|ttr)\b|time to |tempo (?:at[eé]|para) ")

_MARCO_ORDER = ("fim", "mitigacao", "reconhecimento", "deteccao", "inicio")
_COLUMNS = {
    "texto": ("acao", "action", "item", "follow"),
    "dono": ("dono", "owner", "responsavel", "responsible"),
    "ticket": ("ticket", "bug", "link", "issue", "jira"),
    "prioridade": ("prioridade", "priority"),
    "tipo": ("tipo", "type", "categoria", "category"),
    "prazo": ("prazo", "due", "deadline", "data limite"),
    "componente": ("componente", "component", "servico", "service"),
}


def _section_key(title: str, cfg: Config) -> str | None:
    t = re.sub(r"^[\d.\s)-]+", "", norm(title))
    for key, terms in cfg.secoes.items():
        if any(t.startswith(x) for x in terms):
            return key
    return None


def _build_sections(lines: list[tuple[int, str]], cfg: Config) -> list[Section]:
    heads = []
    for i, (n, t) in enumerate(lines):
        m = HEADING.match(t)
        if m:
            heads.append((i, n, len(m.group(1)), m.group(2)))
    out = []
    for k, (i, n, level, title) in enumerate(heads):
        end = len(lines)
        for j, _, lv, _ in heads[k + 1:]:
            if lv <= level:
                end = j
                break
        out.append(Section(_section_key(title, cfg), title, n, level,
                           tuple(lines[i + 1:end])))
    return out


def _content(text: str, next_text: str | None) -> str | None:
    """Conteúdo de uma linha de seção, ou None se deve ser ignorada."""
    if SEP_ROW.match(text) and "|" in text:
        return None
    if TABLE_ROW.match(text):
        if next_text is not None and SEP_ROW.match(next_text) and "|" in next_text:
            return None
        cells = [c.strip() for c in TABLE_ROW.match(text).group(1).split("|")]
        return strip_markup(" | ".join(cells))
    m = LIST_ITEM.match(text)
    return strip_markup(m.group(1) if m else text)


def _only_date(content: str, order: str | None) -> bool:
    if find_date(content, order) is None:
        return False
    return not re.search(r"\w", mask_temporal(content))


def _cells(text: str) -> list[str]:
    return [strip_markup(c.strip()) for c in TABLE_ROW.match(text).group(1).split("|")]


def _parse_actions(sec: Section) -> list[Action]:
    out: list[Action] = []
    cols: dict[str, int] | None = None
    ls = sec.lines
    for i, (n, t) in enumerate(ls):
        nxt = ls[i + 1][1] if i + 1 < len(ls) else None
        if SEP_ROW.match(t) and "|" in t:
            continue
        if TABLE_ROW.match(t):
            cells = _cells(t)
            if nxt is not None and SEP_ROW.match(nxt) and "|" in nxt:
                cols = {}
                for idx, c in enumerate(cells):
                    h = norm(c)
                    for field, prefixes in _COLUMNS.items():
                        if field not in cols and any(h.startswith(p) for p in prefixes):
                            cols[field] = idx
                            break
                if "texto" not in cols:
                    cols["texto"] = 0
                continue
            if cols is None or not any(cells):
                continue
            vals = {f: (cells[i2] if i2 < len(cells) else "") for f, i2 in cols.items()}
            if not vals.get("texto"):
                continue
            out.append(Action(n, **vals))
            continue
        m = LIST_ITEM.match(t)
        if m:
            cols = None
            out.append(Action(n, strip_markup(m.group(1)).strip()))
    return out


def parse_document(path, cfg: Config) -> Document:
    p = Path(path)
    raw = p.read_text(encoding="utf-8-sig", errors="replace")
    text, redactions = redact(raw.replace("\r\n", "\n").replace("\r", "\n"), p.name)
    lines = [(i + 1, t) for i, t in enumerate(text.split("\n"))]
    if lines and lines[-1][1] == "":
        lines.pop()

    sections = _build_sections(lines, cfg)
    tl = next((s for s in sections if s.key == "timeline"), None)
    if tl is None:
        aceitos = ", ".join(cfg.secoes["timeline"])
        raise InputError(f"{p.name}: nenhuma seção de linha do tempo encontrada "
                         f"(cabeçalhos aceitos: {aceitos})")

    tz = parse_tz_decl(tl.title)
    if tz is None:
        for _, t in lines:
            tz = parse_tz_decl(t)
            if tz is not None:
                break
    use_tz = tz or UTC

    order = cfg.formato_data
    inc_date: date | None = None
    severity: str | None = None
    for _, t in lines:
        m = _META.match(t)
        if not m:
            continue
        key, val = norm(m.group(1)), m.group(2)
        if key in ("severidade", "severity"):
            s = _SEV.search(val)
            if severity is None and s:
                severity = f"SEV{s.group(1)}"
        elif inc_date is None:
            inc_date = find_date(val, order)
    if inc_date is None:
        for _, t in lines:
            inc_date = find_date(t, order)
            if inc_date:
                break
    if severity is None:
        for _, t in lines:
            s = _SEV.search(t)
            if s:
                severity = f"SEV{s.group(1)}"
                break

    unparsed: list[Unparsed] = []
    ambiguous: list[Unparsed] = []

    # timeline
    timeline: list[TimelineEntry] = []
    cur = inc_date
    ls = tl.lines
    for i, (n, t) in enumerate(ls):
        h = HEADING.match(t)
        if h:
            d = find_date(h.group(2), order)
            if d:
                cur = d
            continue
        nxt = ls[i + 1][1] if i + 1 < len(ls) else None
        content = _content(t, nxt)
        if not content or not content.strip():
            continue
        if _only_date(content, order):
            cur = find_date(content, order)
            continue
        hits = find_stamps(content, default_date=cur, default_tz=use_tz, date_order=order)
        if not hits:
            continue
        hit = hits[0]
        if not _PREFIX_OK.match(content[:hit.start]):
            continue
        if hit.stamp is None:
            (ambiguous if hit.ambiguous else unparsed).append(Unparsed(p.name, n, hit.reason))
            continue
        tag = TAG.search(content)
        marker = None
        if tag:
            marker = norm(tag.group(1))
        else:
            nc = norm(content)
            for mk in _MARCO_ORDER:
                if any(word_in(norm(w), nc) for w in cfg.marcos.get(mk, ())):
                    marker = mk
                    break
        timeline.append(TimelineEntry(n, content, hit.stamp, hit.assumed_tz,
                                      marker, bool(_VAGUE.search(content))))
        cur = hit.stamp.when.astimezone(use_tz).date()

    # ações
    actions: list[Action] = []
    for s in sections:
        if s.key == "acoes":
            actions.extend(_parse_actions(s))

    # fatores
    factors: list[Factor] = []
    for s in sections:
        if s.key != "causa":
            continue
        for n, t in s.lines:
            m = LIST_ITEM.match(t)
            if not m:
                continue
            c = strip_markup(m.group(1))
            stamps = tuple(h.stamp for h in find_stamps(
                c, default_date=inc_date, default_tz=use_tz, date_order=order)
                if h.stamp is not None)
            factors.append(Factor(n, c, stamps))

    # quantidades e durações
    quantities: list[Quantity] = []
    durations: list[Duration] = []
    covered: set[int] = set()
    seen_in_ri: set[int] = set()
    for s in sections:
        if s.key in ("resumo", "impacto", "timeline", "acoes"):
            covered.update(n for n, _ in s.lines)
        if s.key in ("resumo", "impacto"):
            for n, t in s.lines:
                if HEADING.match(t) or n in seen_in_ri:
                    continue
                seen_in_ri.add(n)
                for r, forms in extract_quantities(t):
                    quantities.append(Quantity(n, r, forms))
                for r, minutes, label in extract_durations(t):
                    durations.append(Duration(n, r, minutes, label))
    for n, t in lines:
        if n in covered or HEADING.match(t) or not _LABEL_HINT.search(t):
            continue
        for r, minutes, label in extract_durations(t, labeled_only=True):
            durations.append(Duration(n, r, minutes, label))
    durations.sort(key=lambda d: d.line)

    return Document(str(p), p.name, lines, sections, tz, inc_date, severity,
                    timeline, actions, factors, quantities, durations,
                    redactions, unparsed, ambiguous)
