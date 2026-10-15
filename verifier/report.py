"""Relatório JSON e Markdown. Nunca inclui o valor de uma credencial."""
import json
from datetime import timezone
from pathlib import Path

from verifier import __version__
from verifier.catalog import RULES, SOURCES
from verifier.excalidraw import dumps
from verifier.metrics import DEFINITIONS
from verifier.model import Finding
from verifier.rules._base import Context
from verifier.rules.donos import component_of, team_for


def _iso_z(stamp) -> str:
    when = stamp.when
    when = (when.astimezone(timezone.utc) if when.tzinfo
            else when.replace(tzinfo=timezone.utc))
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_report(ctx: Context, findings: list[Finding]) -> dict:
    doc, ev, cfg = ctx.doc, ctx.ev, ctx.cfg
    reprovado = any(f.nivel == "reprova" for f in findings)
    achados = [{
        "id": f.id, "nivel": f.nivel, "local": f.local,
        "mensagem": f.mensagem, "fonte": list(f.fonte) or ["interno"],
        "evidencia": f.evidencia,
    } for f in findings]
    usadas = sorted({c for f in findings for c in f.fonte if c in SOURCES})
    reds = [r for r in (*doc.redactions, *ev.redactions)]
    unp = [u for u in (*doc.unparsed, *ev.unparsed)]
    acoes = []
    for a in doc.actions:
        comp = component_of(a.texto, a.componente, cfg)
        team = team_for(comp, cfg) if comp else None
        acoes.append({"linha": a.line, "texto": a.texto, "dono": a.dono,
                      "componente": comp or "",
                      "time_sugerido": team.name if team else ""})
    return {
        "versao": __version__,
        "documento": doc.name,
        "resultado": "reprovado" if reprovado else "aprovado",
        "fuso_do_documento": str(doc.tz) if doc.tz is not None else None,
        "definicoes": dict(DEFINITIONS),
        "marcos": {k: _iso_z(e.stamp) for k, e in ctx.milestones.items()},
        "metricas_min": {k: round(v, 2) for k, v in ctx.metrics.items()},
        "achados": achados,
        "credenciais_ocultadas": [
            {"arquivo": r.file, "linha": r.line, "tipo": r.kind} for r in reds],
        "nao_interpretado": [
            {"arquivo": u.file, "linha": u.line, "motivo": u.reason}
            for u in unp],
        "acoes": acoes,
        "mapa_de_times": {t.name: {"componentes": list(t.componentes),
                                   "membros": list(t.membros)}
                          for t in cfg.times},
        "fontes": {c: SOURCES[c] for c in usadas},
    }


def _num(v) -> str:
    return f"{v:g}"


def render_markdown(report: dict) -> str:
    achados = report["achados"]
    reprovas = [a for a in achados if a["nivel"] == "reprova"]
    avisos = [a for a in achados if a["nivel"] == "aviso"]
    L: list[str] = []
    L += [f"# Relatório de verificação: {report['documento']}", ""]
    L += [f"Resultado: **{report['resultado']}**", ""]
    L += [f"{len(reprovas)} reprovações, {len(avisos)} avisos.", ""]
    fuso = report["fuso_do_documento"] or "não declarado"
    L += [f"Fuso do documento: {fuso}", ""]

    L += ["## Definições", ""]
    for k, v in report["definicoes"].items():
        L.append(f"- {k}: {v}")
    L.append("")

    L += ["## Métricas (minutos)", "", "| Métrica | Minutos |", "|---|---|"]
    for k in report["definicoes"]:
        if k in report["metricas_min"]:
            L.append(f"| {k} | {_num(report['metricas_min'][k])} |")
        else:
            L.append(f"| {k} | n/d |")
    L.append("")
    if report["marcos"]:
        L += ["Marcos (UTC):", ""]
        L += [f"- {k}: {v}" for k, v in report["marcos"].items()]
        L.append("")

    def lista(titulo, itens, vazio):
        L.extend([f"## {titulo}", ""])
        if not itens:
            L.extend([vazio, ""])
            return
        for a in itens:
            fontes = ", ".join(a["fonte"])
            L.append(f"- {a['id']} ({a['local']}): {a['mensagem']} "
                     f"[fonte: {fontes}]")
            if a.get("evidencia"):
                L.append(f"  - evidência: {a['evidencia']}")
        L.append("")

    lista("Reprovações", reprovas, "Nenhuma.")
    lista("Avisos", avisos, "Nenhum.")

    L += ["## Credenciais ocultadas", ""]
    if report["credenciais_ocultadas"]:
        L.append("Os valores foram removidos antes da leitura e não constam "
                 "neste relatório.")
        L.append("")
        for c in report["credenciais_ocultadas"]:
            L.append(f"- {c['tipo']}: {c['arquivo']}, linha {c['linha']}")
    else:
        L.append("Nenhuma.")
    L.append("")

    L += ["## Linhas não interpretadas", ""]
    if report["nao_interpretado"]:
        for u in report["nao_interpretado"]:
            L.append(f"- {u['arquivo']}, linha {u['linha']}: {u['motivo']}")
    else:
        L.append("Nenhuma.")
    L.append("")

    L += ["## Ações e times", ""]
    if not report["mapa_de_times"]:
        L += ["Nenhum mapa de times configurado. Para sugerir o time de cada "
              "ação, configure a seção [times] (tabelas [times.nome] com "
              "componentes e membros) no sourced-postmortem.toml.", ""]
    if report["acoes"]:
        L += ["| Linha | Ação | Dono | Componente | Time sugerido |",
              "|---|---|---|---|---|"]
        for a in report["acoes"]:
            cells = [str(a["linha"]), a["texto"], a["dono"], a["componente"],
                     a["time_sugerido"]]
            L.append("| " + " | ".join(
                (c or "-").replace("|", "\\|") for c in cells) + " |")
    else:
        L.append("Nenhuma.")
    L.append("")

    L += ["## Fontes", ""]
    if report["fontes"]:
        L += [f"- {c}: {u}" for c, u in report["fontes"].items()]
    else:
        L.append("Nenhuma.")
    L.append("")
    return "\n".join(L)


def write_outputs(out_dir: Path, report: dict, scene: dict) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "relatorio.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (out / "relatorio.md").write_text(render_markdown(report), encoding="utf-8")
    (out / "diagrama.excalidraw").write_text(dumps(scene), encoding="utf-8")
