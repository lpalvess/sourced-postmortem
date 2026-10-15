"""M1, M2 e M3: marcos e métricas."""
from verifier.catalog import MARKERS
from verifier.metrics import METRICS, tolerance_minutes
from verifier.rules._base import Context, finding, hhmm

REQUIRED = ("inicio", "deteccao", "mitigacao", "fim")


def _timeline_title(ctx: Context) -> tuple[str, int | None]:
    sec = ctx.doc.section("timeline")
    if sec is None:
        return "timeline", None
    return f"timeline, linha {sec.line}", sec.line


def check(ctx: Context):
    out = []
    local, linha = _timeline_title(ctx)
    for m in REQUIRED:
        if m not in ctx.milestones:
            out.append(finding(
                "M1", local,
                f"falta o marco '{m}' na timeline; marque a entrada com a tag [{m}]",
                linha=linha))

    present = [m for m in MARKERS if m in ctx.milestones]
    for a, b in zip(present, present[1:]):
        ea, eb = ctx.milestones[a], ctx.milestones[b]
        if eb.stamp.when < ea.stamp.when:
            out.append(finding(
                "M2", f"timeline, linha {eb.line}",
                f"'{b}' ({hhmm(eb)}) vem antes de '{a}' ({hhmm(ea)})",
                linha=eb.line))

    tol = tolerance_minutes(ctx.cfg.tolerancia_segundos)
    for d in ctx.doc.durations:
        if d.label is not None:
            calc = ctx.metrics.get(d.label)
            if calc is None or abs(d.minutes - calc) < tol:
                continue
            out.append(finding(
                "M3", f"linha {d.line}",
                f"{d.label} citado '{d.raw}' ({d.minutes:g} min), recalculado "
                f"{calc:g} min a partir dos marcos",
                linha=d.line))
        else:
            if not ctx.metrics:
                continue
            if any(abs(d.minutes - v) < tol for v in ctx.metrics.values()):
                continue
            calc = ", ".join(f"{k} {v:g}" for k, v in ctx.metrics.items() if k in METRICS)
            out.append(finding(
                "M3", f"linha {d.line}",
                f"duração '{d.raw}' ({d.minutes:g} min) não bate com nenhuma "
                f"métrica recalculada ({calc} min)",
                linha=d.line))
    return out
