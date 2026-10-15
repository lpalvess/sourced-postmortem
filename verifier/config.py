"""Configuração: perfil padrão e leitura do TOML."""
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from verifier.catalog import LEVELS, MARKERS, RULES, SECTION_KEYS
from verifier.model import ConfigError
from verifier.text import norm


def _syn(*terms: str) -> tuple[str, ...]:
    out: list[str] = []
    for t in terms:
        n = norm(t)
        if n not in out:
            out.append(n)
    return tuple(out)


DEFAULT_MARCOS: dict[str, tuple[str, ...]] = {
    "inicio": _syn("início do impacto", "impacto começa", "impact started",
                   "outage begins", "started"),
    "deteccao": _syn("detectado", "detecção", "alerta disparou", "detected",
                     "alert fired", "reported"),
    "reconhecimento": _syn("reconhecido", "ack", "acknowledged",
                           "on-call assumiu"),
    "mitigacao": _syn("mitigado", "mitigação", "mitigated", "outage mitigated"),
    "fim": _syn("fim do impacto", "impacto encerrado", "resolvido",
                "outage ends", "resolved", "impact ended"),
}

DEFAULT_SECOES: dict[str, tuple[str, ...]] = {
    "resumo": _syn("Resumo", "Summary", "Executive Summary", "Overview",
                   "Visão geral"),
    "impacto": _syn("Impacto", "Impact"),
    "causa": _syn("Causa", "Causa raiz", "Causas", "Fatores contribuintes",
                  "Root cause", "Root causes", "Contributing factors",
                  "Contributors", "Trigger", "Gatilho"),
    "timeline": _syn("Linha do tempo", "Timeline", "Cronologia"),
    "acoes": _syn("Ações", "Acoes", "Action items", "Follow-ups", "Follow ups",
                  "Corrective actions", "Ações corretivas", "Itens de ação"),
}


@dataclass(frozen=True)
class Team:
    name: str
    componentes: tuple[str, ...]
    membros: tuple[str, ...]


def _default_prazo() -> dict[str, int]:
    return {"SEV1": 15, "SEV2": 30}


@dataclass
class Config:
    tolerancia_segundos: int = 0
    prazo_dias: dict[str, int] = field(default_factory=_default_prazo)
    limite_evidencias_mb: int = 50
    formato_data: str | None = None
    niveis: dict[str, str] = field(default_factory=dict)
    marcos: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: dict(DEFAULT_MARCOS))
    secoes: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: dict(DEFAULT_SECOES))
    times: tuple[Team, ...] = ()


TOP_KEYS = ("perfil", "niveis", "marcos", "secoes", "times")
PERFIL_KEYS = ("tolerancia_segundos", "prazo_dias", "limite_evidencias_mb",
               "formato_data")
TEAM_KEYS = ("componentes", "membros")


def _is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _str_list(err, key: str, v: object) -> tuple[str, ...]:
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise err(key, "deve ser uma lista de textos")
    return tuple(v)


def _table(err, key: str, v: object) -> dict:
    if not isinstance(v, dict):
        raise err(key, "deve ser uma tabela")
    return v


def load_config(path: "str | Path | None") -> Config:
    cfg = Config()
    if path is None:
        return cfg
    p = Path(path)
    name = p.name

    def err(key: str, msg: str) -> ConfigError:
        return ConfigError(f"{name}: chave '{key}': {msg}")

    try:
        raw = p.read_bytes()
    except OSError as e:
        raise ConfigError(f"{name}: não foi possível ler o arquivo ({e.strerror or e})")
    try:
        data = tomllib.loads(raw.decode("utf-8-sig", errors="replace"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{name}: TOML inválido: {e}")

    for k in data:
        if k not in TOP_KEYS:
            raise err(k, f"chave desconhecida (aceitas: {', '.join(TOP_KEYS)})")

    perfil = _table(err, "perfil", data.get("perfil", {}))
    for k, v in perfil.items():
        key = f"perfil.{k}"
        if k not in PERFIL_KEYS:
            raise err(key, f"chave desconhecida (aceitas: {', '.join(PERFIL_KEYS)})")
        if k == "tolerancia_segundos":
            if not _is_int(v) or v < 0:
                raise err(key, "deve ser inteiro de 0 ou mais")
            cfg.tolerancia_segundos = v
        elif k == "limite_evidencias_mb":
            if not _is_int(v) or v <= 0:
                raise err(key, "deve ser inteiro maior que 0")
            cfg.limite_evidencias_mb = v
        elif k == "formato_data":
            if v not in ("DMY", "MDY"):
                raise err(key, 'deve ser "DMY" ou "MDY"')
            cfg.formato_data = v
        else:
            t = _table(err, key, v)
            prazos: dict[str, int] = {}
            for sev, dias in t.items():
                if not _is_int(dias) or dias <= 0:
                    raise err(f"{key}.{sev}", "deve ser inteiro maior que 0")
                prazos[sev.upper()] = dias
            cfg.prazo_dias = prazos

    for rid, lvl in _table(err, "niveis", data.get("niveis", {})).items():
        if rid not in RULES:
            raise err(f"niveis.{rid}", "regra inexistente")
        if lvl not in LEVELS:
            raise err(f"niveis.{rid}", f"nível inválido (aceitos: {', '.join(LEVELS)})")
        cfg.niveis[rid] = lvl

    for table, valid, target in (("marcos", MARKERS, cfg.marcos),
                                 ("secoes", SECTION_KEYS, cfg.secoes)):
        for k, v in _table(err, table, data.get(table, {})).items():
            key = f"{table}.{k}"
            if k not in valid:
                raise err(key, f"chave desconhecida (aceitas: {', '.join(valid)})")
            extra = [norm(x) for x in _str_list(err, key, v)]
            merged = list(target[k])
            merged += [x for x in extra if x and x not in merged]
            target[k] = tuple(merged)

    teams: list[Team] = []
    for tname, t in _table(err, "times", data.get("times", {})).items():
        base = f"times.{tname}"
        t = _table(err, base, t)
        for k in t:
            if k not in TEAM_KEYS:
                raise err(f"{base}.{k}",
                          f"chave desconhecida (aceitas: {', '.join(TEAM_KEYS)})")
        teams.append(Team(
            tname,
            _str_list(err, f"{base}.componentes", t.get("componentes", [])),
            _str_list(err, f"{base}.membros", t.get("membros", [])),
        ))
    cfg.times = tuple(teams)
    return cfg
