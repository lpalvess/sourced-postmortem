"""Ocultação de credenciais antes de qualquer leitura do texto."""
import re

from verifier.model import Redaction

PREFIXO = "[OCULTO:"

# (kind, regex compilada, grupo trocado pela máscara; 0 = trecho inteiro)
PADROES = [
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
        r"((?<![A-Za-z0-9+.-])[a-zA-Z][a-zA-Z0-9+.-]{0,31}://[^/\s:@]+:)([^@\s/]+)(?=@)"), 2),
    ("senha-chave", re.compile(
        r"(?i)(\b[\w-]{0,40}(?:password|passwd|senha|secret|token|api_key|apikey)"
        r"\b[\"']?\s*[=:]\s*)(\"[^\"\n]*\"?|'[^'\n]*'?|[^\s\"',;]+)"), 2),
]


_MASCARA = re.compile(r"\[OCULTO:[a-z-]+\]")
_CAB_CHAVE = re.compile(r"-----BEGIN [A-Z ]{0,30}PRIVATE KEY-----")
_FIM_CHAVE = re.compile(r"-----END [A-Z ]{0,30}PRIVATE KEY-----")
_LINHA_VAZIA = re.compile(r"\n[ \t\r]*\n")


def _aplicar(padrao, kind, grupo, texto, file, achados):
    def repl(m):
        valor = m.group(grupo)
        abre = fecha = ""
        if kind == "senha-chave" and valor[:1] in ("'", '"'):
            q = valor[0]
            fechado = len(valor) > 1 and valor.endswith(q)
            valor = valor[1:-1] if fechado else valor[1:]
            abre, fecha = q, (q if fechado else "")
            if not valor:
                return m.group(0)
        if _MASCARA.fullmatch(valor):
            return m.group(0)
        linha = m.string.count("\n", 0, m.start()) + 1
        achados.append(Redaction(file, linha, kind))
        mascara = f"{PREFIXO}{kind}]" + "\n" * valor.count("\n")
        ini = m.start(grupo) - m.start()
        fim = m.end(grupo) - m.start()
        bruto = m.group(0)
        return bruto[:ini] + abre + mascara + fecha + bruto[fim:]

    return padrao.sub(repl, texto)


def _chaves_privadas(texto, file, achados):
    """Bloco completo BEGIN..END; sem END (log truncado), do cabeçalho até a
    próxima linha em branco ou o fim do texto. Varredura linear."""
    partes = []
    pos = 0
    linha = 1
    cursor = 0
    sem_fim = False
    while True:
        cab = _CAB_CHAVE.search(texto, pos)
        if not cab:
            break
        fim = None if sem_fim else _FIM_CHAVE.search(texto, cab.end())
        if fim is not None:
            fim_pos = fim.end()
        else:
            sem_fim = True
            vazia = _LINHA_VAZIA.search(texto, cab.end())
            fim_pos = vazia.start() if vazia else len(texto)
        trecho = texto[cab.start():fim_pos]
        linha += texto.count("\n", cursor, cab.start())
        cursor = cab.start()
        achados.append(Redaction(file, linha, "private-key"))
        partes.append(texto[pos:cab.start()])
        partes.append(f"{PREFIXO}private-key]" + "\n" * trecho.count("\n"))
        pos = fim_pos
    partes.append(texto[pos:])
    return "".join(partes)


def redact(text: str, file: str) -> tuple[str, list[Redaction]]:
    achados: list[Redaction] = []
    text = _chaves_privadas(text, file, achados)
    for kind, padrao, grupo in PADROES:
        text = _aplicar(padrao, kind, grupo, text, file, achados)
    achados.sort(key=lambda r: (r.line, r.kind))
    return text, achados
