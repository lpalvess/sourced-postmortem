"""Catálogo de regras, níveis e fontes."""

LEVELS = ("reprova", "aviso", "desligada")
MARKERS = ("inicio", "deteccao", "reconhecimento", "mitigacao", "fim")
SECTION_KEYS = ("resumo", "impacto", "causa", "timeline", "acoes")

# id: (id, nível padrão, fontes, título curto)
RULES: dict[str, tuple[str, str, tuple[str, ...], str]] = {
    "E1": ("E1", "reprova", ("P4",), "Horário da timeline sem evidência"),
    "E2": ("E2", "reprova", ("G3",), "Número sem evidência"),
    "M1": ("M1", "reprova", ("G2", "A2", "P6", "F1"), "Marcos faltando"),
    "M2": ("M2", "reprova", ("F1",), "Marcos fora de ordem"),
    "M3": ("M3", "reprova", ("F1", "G2"), "Duração diferente da recalculada"),
    "T1": ("T1", "reprova", ("G2", "A2", "I2"), "Fuso horário não declarado"),
    "T2": ("T2", "reprova", ("A2",), "Timeline fora de ordem"),
    "T3": ("T3", "aviso", ("A1",), "Horário vago"),
    "T4": ("T4", "aviso", ("P4", "G2"), "Sem lead-up antes do início"),
    "T5": ("T5", "aviso", (), "Data ambígua não interpretada"),
    "T6": ("T6", "aviso", (), "Evidência sem fuso"),
    "A1": ("A1", "reprova", ("G3", "I4"), "Ação sem dono"),
    "A2": ("A2", "reprova", ("G3", "P4", "A2", "I4"), "Ação sem ticket"),
    "A3": ("A3", "reprova", ("G3", "G4"), "Prioridade inválida"),
    "A4": ("A4", "reprova", ("G4", "A2"), "Tipo de ação inválido"),
    "A5": ("A5", "reprova", ("P3", "A3", "I4"), "Prazo ausente ou longo"),
    "A6": ("A6", "reprova", ("G4", "I4"), "Ação com verbo vago"),
    "O1": ("O1", "aviso", ("config",), "Dono fora do time do componente"),
    "L1": ("L1", "aviso", ("G3", "G4", "P5", "E1"), "Termo de culpa"),
    "L2": ("L2", "aviso", ("A2",), "Nome próprio ou handle"),
}

SOURCES: dict[str, str] = {
    "G1": "https://sre.google/sre-book/postmortem-culture/",
    "G2": "https://sre.google/sre-book/example-postmortem/",
    "G3": "https://sre.google/workbook/postmortem-culture/",
    "G4": "https://www.usenix.org/system/files/login/articles/login_spring17_09_lunney.pdf",
    "P1": "https://postmortems.pagerduty.com/what_is/",
    "P2": "https://postmortems.pagerduty.com/culture/blameless/",
    "P3": "https://postmortems.pagerduty.com/culture/accountability/",
    "P4": "https://postmortems.pagerduty.com/how_to_write/writing/",
    "P5": "https://postmortems.pagerduty.com/how_to_write/effective_postmortems/",
    "P6": "https://postmortems.pagerduty.com/assets/pdf/PostmortemTemplate.pdf",
    "A1": "https://www.atlassian.com/incident-management/postmortem",
    "A2": "https://www.atlassian.com/incident-management/handbook/postmortems",
    "A3": "https://www.atlassian.com/incident-management/postmortem/templates",
    "A4": "https://www.atlassian.com/incident-management/kpis/common-metrics",
    "A5": "https://www.atlassian.com/incident-management/postmortem/blameless",
    "I1": "https://incident.io/guide/learn-and-improve/post-mortem-documents",
    "I2": "https://incident.io/hubs/post-mortem/incident-post-mortem-template",
    "I3": "https://docs.incident.io/post-incident/postmortem-templates",
    "I4": "https://incident.io/blog/why-do-post-mortem-action-items-fail-how-to-make-incident-follow-ups-actually-get-done",
    "I5": "https://docs.incident.io/incidents/lifecycle",
    "I6": "https://docs.incident.io/insights/supported-measures",
    "I7": "https://incident.io/blog/how-to-measure-mtta",
    "I8": "https://incident.io/blog/blameless-post-mortems",
    "F1": "https://firehydrant.com/docs/managing-incidents/incident-milestones",
    "F2": "https://firehydrant.com/blog/incident-retrospective-postmortem-template/",
    "E1": "https://extfiles.etsy.com/DebriefingFacilitationGuide.pdf",
    "D1": "https://github.com/dastergon/postmortem-templates",
}
