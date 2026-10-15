"""E1 e E2: horários e números precisam de evidência."""
from bisect import bisect_left
from datetime import timedelta, timezone

from verifier.rules._base import Context, finding

UTC = timezone.utc


def _fmt(dt) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def check(ctx: Context):
    out = []
    stamps = sorted(s.when for r in ctx.ev.records for s in r.stamps)
    tol = timedelta(seconds=ctx.cfg.tolerancia_segundos)
    for e in ctx.doc.timeline:
        if e.stamp is None:
            continue
        width = timedelta(seconds=1 if e.stamp.precision == "second" else 60)
        start = e.stamp.when - tol
        end = e.stamp.when + width + tol
        i = bisect_left(stamps, start)
        if i < len(stamps) and stamps[i] < end:
            continue
        out.append(finding(
            "E1", f"timeline, linha {e.line}",
            f"nenhuma evidência perto de {_fmt(e.stamp.when)} UTC "
            f"(janela {_fmt(start)} a {_fmt(end)} UTC, fim exclusivo)",
            linha=e.line))
    ev_numbers = ctx.ev.numbers
    for q in ctx.doc.quantities:
        if q.forms & ev_numbers:
            continue
        out.append(finding(
            "E2", f"linha {q.line}",
            f"o número '{q.raw}' não aparece em nenhuma evidência",
            linha=q.line))
    return out
