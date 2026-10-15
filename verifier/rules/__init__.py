"""Regras do verificador."""
import dataclasses

from verifier.metrics import compute, milestones
from verifier.model import Document, Evidence, Finding
from verifier.config import Config
from verifier.rules import evidencias, metricas
from verifier.rules._base import Context

RULE_MODULES = (evidencias, metricas)


def build_context(doc: Document, ev: Evidence, cfg: Config) -> Context:
    ms = milestones(doc.timeline)
    return Context(doc, ev, cfg, ms, compute(ms))


def run_all(ctx: Context) -> list[Finding]:
    out: list[Finding] = []
    for mod in RULE_MODULES:
        for f in mod.check(ctx):
            nivel = ctx.cfg.niveis.get(f.id)
            if nivel == "desligada":
                continue
            if nivel is not None and nivel != f.nivel:
                f = dataclasses.replace(f, nivel=nivel)
            out.append(f)
    return out
