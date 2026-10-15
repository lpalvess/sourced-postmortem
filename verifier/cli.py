"""Linha de comando do verificador."""
import argparse
import sys
import traceback
from pathlib import Path

from verifier.config import load_config
from verifier.evidence import load_evidence
from verifier.excalidraw import build_diagram
from verifier.model import ConfigError, InputError
from verifier.parse_doc import parse_document
from verifier.report import build_report, write_outputs
from verifier.rules import build_context, run_all


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="verifier",
        description="Verifica um postmortem de incidente contra as evidências.")
    p.add_argument("postmortem", help="arquivo Markdown do postmortem")
    p.add_argument("evidencias", help="pasta com as evidências")
    p.add_argument("--config", help="arquivo sourced-postmortem.toml")
    p.add_argument("--out", default="sourced-postmortem-out",
                   help="pasta de saída (padrão: sourced-postmortem-out)")
    return p


def main(argv: list[str] | None = None) -> int:
    a = _parser().parse_args(argv)
    try:
        cfg = load_config(a.config)
        if not Path(a.postmortem).is_file():
            raise InputError(f"postmortem não encontrado: {a.postmortem}")
        doc = parse_document(a.postmortem, cfg)
        ev = load_evidence(a.evidencias, cfg, default_date=doc.incident_date,
                           default_tz=doc.tz)
        ctx = build_context(doc, ev, cfg)
        findings = run_all(ctx)
        report = build_report(ctx, findings)
        scene = build_diagram(doc, cfg, findings)
        write_outputs(Path(a.out), report, scene)
    except ConfigError as e:
        print(f"Configuração inválida: {e}", file=sys.stderr)
        return 3
    except InputError as e:
        print(f"Entrada inválida: {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"Erro ao ler ou gravar arquivo: {e}", file=sys.stderr)
        return 2
    except Exception:
        traceback.print_exc()
        return 2
    nivel = [f.nivel for f in findings]
    print(f"{report['resultado']}: {nivel.count('reprova')} reprovações, "
          f"{nivel.count('aviso')} avisos.")
    return 1 if report["resultado"] == "reprovado" else 0
