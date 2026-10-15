"""Modelo de dados."""
from dataclasses import dataclass, field
from datetime import date, datetime, tzinfo


@dataclass(frozen=True)
class Stamp:
    when: datetime
    precision: str


@dataclass(frozen=True)
class Redaction:
    file: str
    line: int
    kind: str


@dataclass(frozen=True)
class Unparsed:
    file: str
    line: int
    reason: str


@dataclass(frozen=True)
class TimelineEntry:
    line: int
    text: str
    stamp: Stamp | None
    assumed_tz: bool
    marker: str | None
    vague: bool


@dataclass(frozen=True)
class Action:
    line: int
    texto: str
    dono: str = ""
    ticket: str = ""
    prioridade: str = ""
    tipo: str = ""
    prazo: str = ""
    componente: str = ""


@dataclass(frozen=True)
class Factor:
    line: int
    text: str
    stamps: tuple[Stamp, ...]


@dataclass(frozen=True)
class Quantity:
    line: int
    raw: str
    forms: frozenset[str]


@dataclass(frozen=True)
class Duration:
    line: int
    raw: str
    minutes: float
    label: str | None


@dataclass(frozen=True)
class Section:
    key: str | None
    title: str
    line: int
    level: int
    lines: tuple[tuple[int, str], ...]


@dataclass
class Document:
    path: str
    name: str
    lines: list[tuple[int, str]]
    sections: list[Section]
    tz: tzinfo | None
    incident_date: date | None
    severity: str | None
    timeline: list[TimelineEntry]
    actions: list[Action]
    factors: list[Factor]
    quantities: list[Quantity]
    durations: list[Duration]
    redactions: list[Redaction]
    unparsed: list[Unparsed]
    ambiguous: list[Unparsed]

    def section(self, key: str) -> Section | None:
        for s in self.sections:
            if s.key == key:
                return s
        return None


@dataclass(frozen=True)
class EvidenceRecord:
    file: str
    line: int
    stamps: tuple[Stamp, ...]
    excerpt: str
    numbers: frozenset[str]


@dataclass
class Evidence:
    records: list[EvidenceRecord]
    redactions: list[Redaction]
    unparsed: list[Unparsed]
    ambiguous: list[Unparsed]
    assumed_tz_files: list[str] = field(default_factory=list)

    @property
    def numbers(self) -> frozenset[str]:
        out: set[str] = set()
        for r in self.records:
            out |= r.numbers
        return frozenset(out)


@dataclass(frozen=True)
class Finding:
    id: str
    nivel: str
    local: str
    mensagem: str
    fonte: tuple[str, ...]
    linha: int | None = None
    evidencia: str | None = None


class InputError(Exception):
    """Entrada inválida (código 2)."""


class ConfigError(Exception):
    """Configuração inválida (código 3)."""
