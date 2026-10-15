"""O1: dono fora do time do componente; mapa de componentes e times."""
from verifier.config import Config, Team
from verifier.rules._base import Context, finding
from verifier.text import norm, word_in


def component_of(text: str, explicit: str, cfg: Config) -> str | None:
    if explicit.strip():
        return explicit.strip()
    low = text.lower()
    for team in cfg.times:
        for comp in team.componentes:
            if word_in(comp.lower(), low):
                return comp
    return None


def team_for(component: str, cfg: Config) -> Team | None:
    wanted = component.strip().lower()
    for team in cfg.times:
        if any(c.lower() == wanted for c in team.componentes):
            return team
    return None


def _handle(value: str) -> str:
    return norm(value).lstrip("@")


def check(ctx: Context):
    cfg = ctx.cfg
    if not cfg.times:
        return []
    out = []
    for a in ctx.doc.actions:
        local = f"ações, linha {a.line}"
        comp = component_of(a.texto, a.componente, cfg)
        if comp is None:
            out.append(finding(
                "O1", local,
                "não foi possível identificar o componente da ação; preencha "
                "a coluna Componente", linha=a.line))
            continue
        team = team_for(comp, cfg)
        if team is None:
            out.append(finding(
                "O1", local,
                f"o componente {comp} não pertence a nenhum time do mapa",
                linha=a.line))
            continue
        dono = _handle(a.dono)
        if not dono:
            continue
        if dono not in {_handle(m) for m in team.membros}:
            out.append(finding(
                "O1", local,
                f"o dono {a.dono.strip()} não é membro do time {team.name}, "
                f"indicado para o componente {comp}", linha=a.line))
    return out
