"""Gera o diagrama de arquitetura (Excalidraw e SVG) em português e inglês.

Uso, da raiz do repositório: python3 docs/diagrams/build_architecture.py
A saída é determinística: rodar duas vezes dá os mesmos bytes.
"""
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from verifier.excalidraw import WRAP, anchors, arrow, dumps, labeled_box, scene  # noqa: E402

OUT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1080, 620
LINE_H = 20
FILL = {
    "entrada": "#ffffff",
    "container": "#e9ecef",
    "redact": "#ffc9c9",
    "parse": "#a5d8ff",
    "rules": "#a5d8ff",
    "report": "#b2f2bb",
    "diagram": "#b2f2bb",
    "skill": "#ffec99",
}

# (id, x, y, PT, EN)
NODES = [
    ("entrada", 40, 60, "postmortem.md, evidências e TOML",
     "postmortem.md, evidence and TOML"),
    ("container", 300, 60, "verify.sh: contêiner sem rede, entradas só leitura",
     "verify.sh: no-network container, read-only inputs"),
    ("redact", 560, 60, "redact: oculta credenciais", "redact: hides credentials"),
    ("parse", 820, 60, "parse_doc, evidence e timestamps: tudo em UTC",
     "parse_doc, evidence and timestamps: all in UTC"),
    ("rules", 820, 260, "regras E, M, T, A, O, L com fonte citada",
     "rules E, M, T, A, O, L with cited source"),
    ("report", 560, 260, "relatorio.json e relatorio.md",
     "relatorio.json and relatorio.md"),
    ("diagram", 820, 460, "diagrama.excalidraw: onde e por quê",
     "diagrama.excalidraw: where and why"),
    ("skill", 300, 260,
     "SKILL.md: conferido pelo script e opinião do modelo, separados",
     "SKILL.md: script-checked and model opinion, kept apart"),
]
EDGES = [("entrada", "container"), ("container", "redact"), ("redact", "parse"),
         ("parse", "rules"), ("rules", "report"), ("rules", "diagram"),
         ("report", "skill")]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(lang: str) -> tuple[str, str]:
    idx = 3 if lang == "pt" else 4
    boxes, elements = {}, []
    for node in NODES:
        key = node[0]
        box, label = labeled_box(key, node[1], node[2], node[idx], fill=FILL[key])
        boxes[key] = box
        elements += [box, label]
    for a, b in EDGES:
        elements.append(arrow(f"{a}>{b}", boxes[a], boxes[b]))
    excalidraw = dumps(scene(elements))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="sans-serif" font-size="16">',
        "<defs>",
        '<marker id="seta" markerWidth="10" markerHeight="8" refX="9" refY="4" '
        'orient="auto" markerUnits="userSpaceOnUse">'
        '<polygon points="0,0 10,4 0,8" fill="#1e1e1e"/></marker>',
        "</defs>",
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>',
    ]
    for node in NODES:
        key = node[0]
        box = boxes[key]
        x, y, w, h = box["x"], box["y"], box["width"], box["height"]
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" ry="12" '
            f'fill="{FILL[key]}" stroke="#1e1e1e" stroke-width="2"/>')
        lines = textwrap.wrap(node[idx], WRAP)
        top = y + (h - len(lines) * LINE_H) / 2 + 15
        tspans = "".join(
            f'<tspan x="{x + w / 2}" y="{top + i * LINE_H}">{esc(t)}</tspan>'
            for i, t in enumerate(lines))
        parts.append(f'<text text-anchor="middle" fill="#1e1e1e">{tspans}</text>')
    for a, b in EDGES:
        (x1, y1), (x2, y2) = anchors(boxes[a], boxes[b])
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#1e1e1e" '
            f'stroke-width="2" marker-end="url(#seta)"/>')
    parts.append("</svg>")
    return excalidraw, "\n".join(parts) + "\n"


def main() -> None:
    for lang in ("pt", "en"):
        excalidraw, svg = build(lang)
        (OUT / f"arquitetura.{lang}.excalidraw").write_text(excalidraw, encoding="utf-8")
        (OUT / f"arquitetura.{lang}.svg").write_text(svg, encoding="utf-8")
        print(f"arquitetura.{lang}.excalidraw e arquitetura.{lang}.svg")


if __name__ == "__main__":
    main()
