#!/usr/bin/env bash
# Roda o sourced-postmortem dentro de um contêiner descartável e trancado.
#
#   scripts/verify.sh <postmortem.md> <evidencias/> [--config <arquivo>] [--out <pasta>]
#   scripts/verify.sh test                         roda a suíte de testes dentro do contêiner
#
# O contêiner roda sem rede, com sistema de arquivos raiz somente leitura, sem
# capabilities, com o código e as entradas montados somente leitura e só a pasta
# de saída gravável.
# Códigos de saída: 0 aprovado, 1 reprovado, 2 entrada inválida, 3 config inválida,
# 4 Docker indisponível ou contêiner que não pôde ser iniciado.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Fixada por digest para a imagem base não mudar por baixo de você. Troque com SOURCED_POSTMORTEM_IMAGE.
IMAGE="${SOURCED_POSTMORTEM_IMAGE:-python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1}"

die() { echo "erro: $*" >&2; exit 2; }

# Caminho absoluto de um arquivo ou pasta existente. Recusa caracteres que quebrariam o --mount.
abspath() {
  local p="$1"
  case "$p" in *,* | *$'\n'*) die "o caminho contém vírgula ou quebra de linha: $p" ;; esac
  [ -e "$p" ] || die "não foi possível ler $p: não encontrado"
  if [ -d "$p" ]; then (cd "$p" && pwd); else echo "$(cd "$(dirname "$p")" && pwd)/$(basename "$p")"; fi
}

bind() { echo "type=bind,src=$1,dst=$2$3"; }

SECURE=(
  --rm
  --network none
  --read-only
  --cap-drop ALL
  --security-opt no-new-privileges
  --pids-limit 256
  --memory 1g
  --tmpfs /tmp:rw,noexec,nosuid,size=128m
  --user "$(id -u):$(id -g)"
  -e HOME=/tmp
  -e PYTHONDONTWRITEBYTECODE=1
  --workdir /app
)

need_docker() {
  command -v docker >/dev/null 2>&1 || { echo "erro: o Docker é necessário e não foi encontrado no PATH" >&2; exit 4; }
  docker info >/dev/null 2>&1 || { echo "erro: o Docker não está disponível (docker info falhou)" >&2; exit 4; }
}

# Roda o contêiner; 125 ou mais significa que o próprio Docker falhou.
run_container() {
  local rc=0
  docker run "${SECURE[@]}" "$@" || rc=$?
  if [ "$rc" -ge 125 ]; then
    echo "erro: o contêiner não pôde ser iniciado (docker run devolveu $rc)" >&2
    exit 4
  fi
  return "$rc"
}

if [ "${1:-}" = test ] && [ $# -eq 1 ]; then
  need_docker
  rc=0
  run_container --mount "$(bind "$ROOT" /app ,readonly)" "$IMAGE" \
    python -m unittest discover -s tests -t . || rc=$?
  exit "$rc"
fi

doc="" ev="" cfg="" out="" cfg_set=0 out_set=0
while [ $# -gt 0 ]; do
  case "$1" in
    --config) [ $# -ge 2 ] || die "--config precisa de um arquivo"; cfg="$2"; cfg_set=1; shift 2 ;;
    --out) [ $# -ge 2 ] || die "--out precisa de uma pasta"; out="$2"; out_set=1; shift 2 ;;
    --*) die "opção desconhecida: $1" ;;
    *)
      if [ -z "$doc" ]; then doc="$1"
      elif [ -z "$ev" ]; then ev="$1"
      else die "argumento inesperado: $1"
      fi
      shift ;;
  esac
done
USO="uso: scripts/verify.sh <postmortem.md> <evidencias/> [--config <arquivo>] [--out <pasta>] | scripts/verify.sh test"
[ -n "$doc" ] || die "falta o documento. $USO"
[ -n "$ev" ] || die "faltam as evidências. $USO"

doc_abs="$(abspath "$doc")"
[ -f "$doc_abs" ] || die "não foi possível ler $doc: não é um arquivo"
ev_abs="$(abspath "$ev")"
[ -d "$ev_abs" ] || die "$ev não é uma pasta"

mounts=(
  --mount "$(bind "$ROOT" /app ,readonly)"
  --mount "$(bind "$(dirname "$doc_abs")" /in/doc ,readonly)"
  --mount "$(bind "$ev_abs" /in/ev ,readonly)"
)
args=(/in/doc/"$(basename "$doc_abs")" /in/ev --out /out)

if [ "$cfg_set" -eq 1 ]; then
  cfg_abs="$(abspath "$cfg")"
  [ -f "$cfg_abs" ] || die "não foi possível ler $cfg: não é um arquivo"
  mounts+=(--mount "$(bind "$(dirname "$cfg_abs")" /in/cfg ,readonly)")
  args+=(--config /in/cfg/"$(basename "$cfg_abs")")
fi

[ "$out_set" -eq 1 ] || out="sourced-postmortem-out"
case "$out" in *,* | *$'\n'*) die "o caminho contém vírgula ou quebra de linha: $out" ;; esac
mkdir -p "$out"
out_abs="$(cd "$out" && pwd)"
# A saída dentro das evidências viraria evidência na próxima execução.
case "$out_abs/" in
  "$ev_abs"/*) die "a pasta de saída não pode ficar dentro da pasta de evidências: $out_abs" ;;
esac
mounts+=(--mount "$(bind "$out_abs" /out "")")

need_docker

rc=0
run_container "${mounts[@]}" "$IMAGE" python -m verifier "${args[@]}" || rc=$?

if [ "$rc" -eq 0 ] || [ "$rc" -eq 1 ]; then
  echo "Relatório: $out_abs/relatorio.md"
  echo "Diagrama: $out_abs/diagrama.excalidraw"
fi
exit "$rc"
