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
