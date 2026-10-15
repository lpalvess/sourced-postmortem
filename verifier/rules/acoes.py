"""A1 a A6: dono, ticket, prioridade, tipo, prazo e verbo vago."""
import re
from datetime import timedelta

from verifier.rules._base import Context, finding
from verifier.text import norm
from verifier.timestamps import find_date

EMPTY = {"", "-", "—", "–", "n/a", "na", "tbd", "a definir", "?",
         "pendente"}

TEAMLIKE = re.compile(
    r"(?i)\b(time|team|squad|equipe|tribo|tribe|grupo|group)\b"
    r"|^@?[\w.-]*-(team|squad|time|sre|ops|eng)$"
    r"|^(team|squad|time|equipe|sre|ops|eng|dev|infra|plataforma|platform|all)"
    r"[\w.+-]*@")

PRIORITY = re.compile(r"(?i)^p([0-3])$")

USER_IMPACT = re.compile(
    r"(?i)usu[aá]rio|users?\b|client|customer|requisi|request|erro|error"
    r"|pedido|order")

TYPES = {
    "investigate": "investigate", "investigar": "investigate",
    "investigacao": "investigate",
    "mitigate": "mitigate", "mitigar": "mitigate", "mitigacao": "mitigate",
    "repair": "repair", "reparar": "repair", "corrigir": "repair",
    "correcao": "repair",
    "detect": "detect", "detectar": "detect", "deteccao": "detect",
    "prevent": "prevent", "prevenir": "prevent", "prevencao": "prevent",
}

VAGUE = ("improve", "make better", "investigate", "review", "explore",
         "look into", "consider", "evaluate", "discuss", "melhorar",
         "investigar", "revisar", "verificar", "avaliar", "analisar",
         "considerar", "discutir")


def _empty(value: str) -> bool:
    return norm(value) in EMPTY


def _vague(texto: str) -> bool:
    t = norm(texto)
    return any(t == v or t.startswith(v + " ") for v in VAGUE)


def check(ctx: Context):
    out = []
    doc, cfg = ctx.doc, ctx.cfg
    acts = doc.actions
    sec = doc.section("acoes")
    sec_line = sec.line if sec else 1

    if not acts:
        out.append(finding(
            "A1", f"ações, linha {sec_line}",
            "Nenhuma ação encontrada; liste as ações corretivas com dono, "
            "ticket, prioridade, tipo e prazo", linha=sec_line))
        return out

    team_names = {t.name.lower() for t in cfg.times}
    for a in acts:
        local = f"ações, linha {a.line}"
        if _empty(a.dono):
            out.append(finding(
                "A1", local, "a ação não tem dono; indique uma pessoa",
                linha=a.line))
        elif TEAMLIKE.search(a.dono.strip()) or a.dono.strip().lower() in team_names:
            out.append(finding(
                "A1", local,
                f"o dono {a.dono.strip()} parece um time; indique uma pessoa",
                linha=a.line, nivel="aviso"))
        if _empty(a.ticket):
            out.append(finding(
                "A2", local, "a ação não tem ticket; registre o link ou o "
                "identificador do ticket", linha=a.line))
        if not PRIORITY.match(a.prioridade.strip()):
            out.append(finding(
                "A3", local,
                f"prioridade inválida ({a.prioridade.strip() or 'vazia'}); "
                "use P0, P1, P2 ou P3", linha=a.line))
        if TYPES.get(norm(a.tipo)) is None:
            out.append(finding(
                "A4", local,
                f"tipo de ação inválido ({a.tipo.strip() or 'vazio'}); use "
                "investigate, mitigate, repair, detect ou prevent",
                linha=a.line))
        d = find_date(a.prazo, cfg.formato_data)
        if d is None:
            out.append(finding(
                "A5", local, "a ação não tem um prazo com data válida",
                linha=a.line))
        else:
            dias = cfg.prazo_dias.get(doc.severity) if doc.severity else None
            if dias is not None and doc.incident_date is not None:
                limite = doc.incident_date + timedelta(days=dias)
                if d > limite:
                    out.append(finding(
                        "A5", local,
                        f"o prazo {d.isoformat()} passa de {dias} dias após o "
                        f"incidente (limite {limite.isoformat()}, "
                        f"{doc.severity})", linha=a.line, nivel="aviso"))
        if _vague(a.texto):
            out.append(finding(
                "A6", local,
                "a ação começa com um verbo vago; descreva o que será feito "
                "e como saber que terminou", linha=a.line))

    valid = [m.group(1).upper() for a in acts
             if (m := PRIORITY.match(a.prioridade.strip()))]
    imp = doc.section("impacto")
    impact_text = " ".join(t for _, t in imp.lines) if imp else ""
    user_impact = bool(USER_IMPACT.search(impact_text)) \
        or doc.severity in ("SEV0", "SEV1", "SEV2")
    if user_impact and not any(p in ("0", "1") for p in valid):
        out.append(finding(
            "A3", f"ações, linha {sec_line}",
            "o incidente teve impacto ao usuário, mas nenhuma ação tem "
            "prioridade P0 ou P1", linha=sec_line))
    if len(acts) >= 2 and len(valid) == len(acts) and len(set(valid)) == 1:
        out.append(finding(
            "A3", f"ações, linha {sec_line}",
            f"todas as ações têm a mesma prioridade (P{valid[0]}); "
            "diferencie por urgência", linha=sec_line, nivel="aviso"))

    kinds = {TYPES[k] for a in acts if (k := norm(a.tipo)) in TYPES}
    missing = [k for k in ("mitigate", "prevent") if k not in kinds]
    if missing:
        out.append(finding(
            "A4", f"ações, linha {sec_line}",
            "faltam ações dos tipos: " + ", ".join(missing),
            linha=sec_line, nivel="aviso"))
    return out
