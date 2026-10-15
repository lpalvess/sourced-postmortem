"""Apoio aos testes: copia o fixture aprovado com trocas pontuais."""
import shutil
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
APROVADO = FIXTURES / "aprovado"


def copy_case(tmp: Path, replace: dict[str, str] | None = None,
              evidence_extra: dict[str, str] | None = None) -> tuple[Path, Path, Path]:
    tmp = Path(tmp)
    shutil.copytree(APROVADO, tmp, dirs_exist_ok=True)
    doc = tmp / "postmortem.md"
    text = doc.read_text(encoding="utf-8")
    for old, new in (replace or {}).items():
        assert old in text, old
        text = text.replace(old, new)
    doc.write_text(text, encoding="utf-8")
    ev = tmp / "evidencias"
    ev.mkdir(exist_ok=True)
    for name, content in (evidence_extra or {}).items():
        (ev / name).write_text(content, encoding="utf-8")
    return doc, ev, tmp / "sourced-postmortem.toml"


def ids(findings, nivel=None) -> list[str]:
    return [f.id for f in findings if nivel is None or f.nivel == nivel]


def check_case(replace=None, evidence_extra=None, config_text=None):
    import tempfile

    from verifier.config import load_config
    from verifier.evidence import load_evidence
    from verifier.parse_doc import parse_document
    from verifier.rules import build_context, run_all

    with tempfile.TemporaryDirectory() as t:
        doc_path, ev_path, cfg_path = copy_case(Path(t), replace, evidence_extra)
        if config_text is not None:
            cfg_path.write_text(config_text, encoding="utf-8")
        cfg = load_config(cfg_path)
        doc = parse_document(doc_path, cfg)
        ev = load_evidence(ev_path, cfg, default_date=doc.incident_date,
                           default_tz=doc.tz)
        ctx = build_context(doc, ev, cfg)
        return run_all(ctx), ctx
