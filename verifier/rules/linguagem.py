"""L1 e L2: termos de culpa, nomes próprios e handles."""
import re

from verifier.rules._base import Context, finding
from verifier.text import norm, starts_word, word_in

BLAME = ("erro humano", "human error", "descuido", "careless", "negligen",
         "should have", "deveria ter", "falhou em", "failed to", "culpa",
         "fault", "ridiculo", "ridiculous", "needs to learn",
         "precisa aprender", "obviamente", "obviously")

HANDLE = re.compile(r"(?<![\w.@])@[A-Za-z][\w.-]*")


def _member_names(cfg) -> set[str]:
    names = set()
    for team in cfg.times:
        for m in team.membros:
            n = norm(m).lstrip("@")
            if len(n) >= 3:
                names.add(n)
    return names


def check(ctx: Context):
    out = []
    doc = ctx.doc

    for no, text in doc.lines:
        n = norm(text)
        found = [t for t in BLAME if starts_word(t, n)]
        if "!!!" in text:
            found.append("!!!")
        if found:
            out.append(finding(
                "L1", f"linha {no}",
                "linguagem de culpa (" + ", ".join(found) + "); descreva "
                "o fato e o sistema, não a pessoa", linha=no))

    names = _member_names(ctx.cfg)
    seen: set[int] = set()
    for key in ("causa", "timeline"):
        sec = doc.section(key)
        if sec is None:
            continue
        for no, text in sec.lines:
            if no in seen:
                continue
            handles = HANDLE.findall(text)
            n = norm(text)
            hits = sorted(x for x in names if word_in(x, n))
            if not handles and not hits:
                continue
            seen.add(no)
            achados = handles + hits
            out.append(finding(
                "L2", f"linha {no}",
                "nome próprio ou handle (" + ", ".join(achados) + "); use "
                "o papel (plantão, autor do deploy) em vez da pessoa",
                linha=no))
    return out
