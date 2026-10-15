"""Métricas de incidente calculadas a partir dos marcos da timeline."""
from verifier.model import TimelineEntry

METRICS: dict[str, tuple[str, str]] = {
    "TTD": ("inicio", "deteccao"),
    "TTA": ("inicio", "reconhecimento"),
    "TTM": ("inicio", "mitigacao"),
    "TTR": ("inicio", "fim"),
    "duracao": ("inicio", "fim"),
}

DEFINITIONS: dict[str, str] = {
    "TTD": "deteccao menos inicio (FireHydrant, F1)",
    "TTA": "reconhecimento menos inicio (FireHydrant, F1)",
    "TTM": "mitigacao menos inicio (FireHydrant, F1)",
    "TTR": "fim menos inicio (FireHydrant, F1)",
    "duracao": "fim menos inicio (Google SRE, G2)",
}


def milestones(timeline: list[TimelineEntry]) -> dict[str, TimelineEntry]:
    out: dict[str, TimelineEntry] = {}
    for e in timeline:
        if e.marker and e.stamp is not None and e.marker not in out:
            out[e.marker] = e
    return out


def compute(ms: dict[str, TimelineEntry]) -> dict[str, float]:
    out: dict[str, float] = {}
    for name, (a, b) in METRICS.items():
        if a in ms and b in ms:
            delta = ms[b].stamp.when - ms[a].stamp.when
            out[name] = delta.total_seconds() / 60
    return out


def tolerance_minutes(tolerancia_segundos: int) -> float:
    return 1.0 + tolerancia_segundos / 60
