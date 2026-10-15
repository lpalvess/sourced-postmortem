"""T1 a T6: fuso, ordem, horários vagos, lead-up e datas ambíguas."""
from collections import Counter

from verifier.rules._base import Context, finding, hhmm
from verifier.timestamps import tz_name


def check(ctx: Context):
    out = []
    doc = ctx.doc
    sec = doc.section("timeline")
    title_local = f"timeline, linha {sec.line}" if sec else "timeline"
    title_line = sec.line if sec else None

    if doc.tz is None and any(e.assumed_tz for e in doc.timeline):
        out.append(finding(
            "T1", title_local,
            "o documento não declara o fuso horário; os horários da timeline "
            "foram lidos como UTC. Declare o fuso no título da timeline",
            linha=title_line))

    prev = None
    for e in doc.timeline:
        if e.stamp is None:
            continue
        if prev is not None and e.stamp.when < prev.stamp.when:
            out.append(finding(
                "T2", f"timeline, linha {e.line}",
                f"a entrada das {hhmm(e)} vem depois de {hhmm(prev)} "
                f"(linha {prev.line}) e está fora de ordem",
                linha=e.line))
        prev = e

    for e in doc.timeline:
        if e.vague:
            out.append(finding(
                "T3", f"timeline, linha {e.line}",
                "horário vago na entrada; use um horário exato (HH:MM)",
                linha=e.line))

    inicio = ctx.milestones.get("inicio")
    first = next((e for e in doc.timeline if e.stamp is not None), None)
    if inicio is not None and inicio.stamp is not None and first is not None \
            and not first.stamp.when < inicio.stamp.when:
        out.append(finding(
            "T4", f"timeline, linha {first.line}",
            f"a primeira entrada ({hhmm(first)}) não é anterior ao início "
            f"({hhmm(inicio)}); registre o que aconteceu antes do início "
            "(deploy, mudança, alerta)",
            linha=first.line))

    for a in doc.ambiguous:
        out.append(finding(
            "T5", f"linha {a.line}",
            f"data ambígua não interpretada: {a.reason}",
            linha=a.line))
    counts = Counter(a.file for a in ctx.ev.ambiguous)
    for fname, n in counts.items():
        out.append(finding(
            "T5", fname,
            f"{n} data(s) ambígua(s) não interpretada(s) em {fname}"))

    for fname in ctx.ev.assumed_tz_files:
        out.append(finding(
            "T6", fname,
            f"os horários de {fname} não têm fuso; foram lidos como "
            f"{tz_name(doc.tz)}"))
    return out
