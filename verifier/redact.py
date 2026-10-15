"""Ocultação de credenciais antes de qualquer leitura do texto."""
import re

from verifier.model import Redaction

PREFIXO = "[OCULTO:"

# (kind, regex compilada, grupo trocado pela máscara; 0 = trecho inteiro)
PADROES = [
    ("private-key", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        re.S), 0),
    ("aws-secret", re.compile(
        r"(?i)(aws_secret_access_key[\"']?\s*[=:]\s*[\"']?)"
        r"([A-Za-z0-9/+=]{40})(?![A-Za-z0-9/+=])"), 2),
    ("aws-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), 0),
    ("github-token", re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})"), 0),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), 0),
    ("jwt", re.compile(
        r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), 0),
    ("bearer", re.compile(r"(?i)(\bbearer\s+)([A-Za-z0-9._~+/=-]{8,})"), 2),
    ("url-credencial", re.compile(
        r"(\b[a-zA-Z][a-zA-Z0-9+.-]*://[^/\s:@]+:)([^@\s/]+)(?=@)"), 2),
    ("senha-chave", re.compile(
        r"(?i)(\b[\w-]*(?:password|passwd|senha|secret|token|api_key|apikey)"
        r"\b[\"']?\s*[=:]\s*[\"']?)([^\s\"',;]+)"), 2),
]


def _aplicar(padrao, kind, grupo, texto, file, achados):
    def repl(m):
        valor = m.group(grupo)
        if valor.startswith(PREFIXO):
            return m.group(0)
        linha = m.string.count("\n", 0, m.start()) + 1
        achados.append(Redaction(file, linha, kind))
        mascara = f"{PREFIXO}{kind}]" + "\n" * valor.count("\n")
        ini = m.start(grupo) - m.start()
        fim = m.end(grupo) - m.start()
        bruto = m.group(0)
        return bruto[:ini] + mascara + bruto[fim:]

    return padrao.sub(repl, texto)


def redact(text: str, file: str) -> tuple[str, list[Redaction]]:
    achados: list[Redaction] = []
    for kind, padrao, grupo in PADROES:
        text = _aplicar(padrao, kind, grupo, text, file, achados)
    achados.sort(key=lambda r: (r.line, r.kind))
    return text, achados
