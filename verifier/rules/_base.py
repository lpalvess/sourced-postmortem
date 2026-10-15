"""Base comum das regras."""
from dataclasses import dataclass

from verifier.catalog import RULES
from verifier.config import Config
from verifier.model import Document, Evidence, Finding, TimelineEntry


@dataclass
class Context:
    doc: Document
    ev: Evidence
    cfg: Config
    milestones: dict[str, TimelineEntry]
    metrics: dict[str, float]


def finding(rule_id: str, local: str, mensagem: str, *, linha: int | None = None,
            nivel: str | None = None, evidencia: str | None = None) -> Finding:
    _, padrao, fontes, _ = RULES[rule_id]
    return Finding(rule_id, nivel or padrao, local, mensagem, tuple(fontes),
                   linha, evidencia)


def hhmm(entry: TimelineEntry) -> str:
    return entry.stamp.when.strftime("%H:%M")
