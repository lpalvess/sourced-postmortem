"""Índice das evidências: horários e números por linha, já sem credenciais."""
from datetime import date, tzinfo
from pathlib import Path

from verifier.config import Config
from verifier.model import (Evidence, EvidenceRecord, InputError, Redaction,
                            Unparsed)
from verifier.numbers import extract_numbers
from verifier.redact import redact
from verifier.timestamps import UTC, find_stamps

EXCERPT_CHARS = 200


def _files(root: Path) -> list[Path]:
    out = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if p.is_file():
            out.append(p)
    return out


def load_evidence(folder: str | Path, cfg: Config, *, default_date: date | None,
                  default_tz: tzinfo | None) -> Evidence:
    root = Path(folder)
    if not root.is_dir():
        raise InputError(f"pasta de evidências não encontrada: {root}")
    files = _files(root)
    if not files:
        raise InputError("pasta de evidências vazia")
    total = sum(p.stat().st_size for p in files)
    limite = cfg.limite_evidencias_mb
    if total > limite * 1024 * 1024:
        raise InputError(
            f"evidências somam {total / (1024 * 1024):.1f} MB, acima do limite de "
            f"{limite} MB (opção limite_evidencias_mb)")

    tz = default_tz if default_tz is not None else UTC
    records: list[EvidenceRecord] = []
    redactions: list[Redaction] = []
    unparsed: list[Unparsed] = []
    ambiguous: list[Unparsed] = []
    assumed: list[str] = []

    for p in files:
        rel = redact(p.relative_to(root).as_posix(), "")[0]
        raw = p.read_text(encoding="utf-8-sig", errors="replace")
        text, found = redact(raw.replace("\r\n", "\n").replace("\r", "\n"), rel)
        redactions.extend(found)
        file_assumed = False
        for n, line in enumerate(text.split("\n"), 1):
            hits = find_stamps(line, default_date=default_date, default_tz=tz,
                               date_order=cfg.formato_data)
            stamps = []
            for h in hits:
                if h.stamp is not None:
                    stamps.append(h.stamp)
                    file_assumed = file_assumed or h.assumed_tz
                elif h.ambiguous:
                    ambiguous.append(Unparsed(rel, n, h.reason))
                else:
                    unparsed.append(Unparsed(rel, n, h.reason))
            numbers = extract_numbers(line)
            if stamps or numbers:
                records.append(EvidenceRecord(
                    rel, n, tuple(stamps), line.strip()[:EXCERPT_CHARS], numbers))
        if file_assumed:
            assumed.append(rel)

    return Evidence(records, redactions, unparsed, ambiguous, assumed)
