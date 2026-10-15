"""Diagrama Excalidraw: onde (faixas por componente) e por quê (fatores)."""
import hashlib
import json
import re
import textwrap
from datetime import timezone

from verifier.config import Config
from verifier.model import Document, Finding
from verifier.parse_doc import TAG
from verifier.rules.donos import component_of
from verifier.text import short, strip_markup

SOURCE = "https://github.com/lpalvess/sourced-postmortem"
WHITE = "#ffffff"
LANE_FILL = "#f8f9fa"
LANE_STROKE = "#868e96"
FACTOR_FILL = "#e9ecef"
ROLE_FILL = {
    "inicio": "#ffc9c9",
    "deteccao": "#a5d8ff",
    "reconhecimento": "#a5d8ff",
    "mitigacao": "#b2f2bb",
    "fim": "#b2f2bb",
}
NO_COMPONENT = "sem componente"
NO_EVIDENCE = "sem evidência"
TITLE = "Linha do tempo (UTC): onde aconteceu"
FACTORS_TITLE = "Por quê: fatores contribuintes"

LEAD = re.compile(
    r"^[\s|~\-]*(?:cerca de|aprox\.?|around)?[\s~]*[\d/:.\-T ]+"
    r"(?:Z|UTC|GMT|[+-]\d{2}:?\d{2})?[\s|\-:]*", re.I)

BOX_W = 200
LANE_H = 150
LANE_X = 20


def _id(kind: str, key: str) -> str:
    return hashlib.sha256((kind + "\x1f" + key).encode("utf-8")).hexdigest()[:20]


def _common(kind: str, key: str) -> dict:
    eid = _id(kind, key)
    return {
        "id": eid,
        "type": kind,
        "angle": 0,
        "strokeColor": "#1e1e1e",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "seed": int(eid[:8], 16) % 2_000_000_000,
        "version": 1,
        "versionNonce": int(eid[::-1][:8], 16) % 2_000_000_000,
        "updated": 1,
        "isDeleted": False,
        "link": None,
        "locked": False,
    }


def rect(key, x, y, w, h, *, fill, dashed=False) -> dict:
    el = _common("rectangle", key)
    el.update({
        "x": x, "y": y, "width": w, "height": h,
        "backgroundColor": fill,
        "fillStyle": "solid" if fill.lower() == WHITE else "hachure",
        "roundness": {"type": 3},
        "boundElements": [],
    })
    if dashed:
        el["strokeStyle"] = "dashed"
    return el


def text(key, x, y, w, content, *, container=None, size=16, align="center") -> dict:
    el = _common("text", key)
    lines = content.count("\n") + 1
    el.update({
        "x": x, "y": y, "width": w, "height": lines * size * 1.25,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "roundness": None,
        "boundElements": None,
        "text": content,
        "originalText": content,
        "fontSize": size,
        "fontFamily": 5,
        "textAlign": align,
        "verticalAlign": "middle" if container else "top",
        "containerId": container,
        "lineHeight": 1.25,
        "autoResize": True,
    })
    return el


def _wrap(content: str) -> list[str]:
    out: list[str] = []
    for part in content.split("\n"):
        out.extend(textwrap.wrap(part, 24) or [""])
    return out


def labeled_box(key, x, y, content, *, fill, dashed=False, width=BOX_W):
    lines = _wrap(content)
    height = max(80, len(lines) * 20 + 20)
    box = rect(key, x, y, width, height, fill=fill, dashed=dashed)
    label = text(key, x + 10, y + (height - len(lines) * 20) / 2, width - 20,
                 "\n".join(lines), container=box["id"])
    box["boundElements"].append({"id": label["id"], "type": "text"})
    return box, label


def anchors(src, dst):
    sx, sy = src["x"], src["y"] + src["height"] / 2
    dx, dy = dst["x"], dst["y"] + dst["height"] / 2
    if abs(sy - dy) < 1:
        if dx >= sx:
            return ((src["x"] + src["width"], sy), (dst["x"], dy))
        return ((src["x"], sy), (dst["x"] + dst["width"], dy))
    scx = src["x"] + src["width"] / 2
    dcx = dst["x"] + dst["width"] / 2
    if dy > sy:
        return ((scx, src["y"] + src["height"]), (dcx, dst["y"]))
    return ((scx, src["y"]), (dcx, dst["y"] + dst["height"]))


def arrow(key, src, dst) -> dict:
    (x1, y1), (x2, y2) = anchors(src, dst)
    el = _common("arrow", key)
    el.update({
        "x": x1, "y": y1,
        "width": abs(x2 - x1), "height": abs(y2 - y1),
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "roundness": {"type": 2},
        "boundElements": None,
        "points": [[0, 0], [x2 - x1, y2 - y1]],
        "lastCommittedPoint": None,
        "startBinding": {"elementId": src["id"], "focus": 0, "gap": 1},
        "endBinding": {"elementId": dst["id"], "focus": 0, "gap": 1},
        "startArrowhead": None,
        "endArrowhead": "arrow",
        "elbowed": False,
    })
    ref = {"id": el["id"], "type": "arrow"}
    src["boundElements"].append(dict(ref))
    dst["boundElements"].append(dict(ref))
    return el


def scene(elements) -> dict:
    return {
        "type": "excalidraw",
        "version": 2,
        "source": SOURCE,
        "elements": list(elements),
        "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
        "files": {},
    }


def dumps(sc) -> str:
    return json.dumps(sc, ensure_ascii=False, indent=2) + "\n"


def _utc(stamp):
    when = stamp.when
    return when.astimezone(timezone.utc) if when.tzinfo else when


def _clean(entry_text: str) -> str:
    body = LEAD.sub("", strip_markup(entry_text), count=1)
    body = TAG.sub("", body)
    return body.strip(" |-:")


def _lane(key, y, width, name, height=LANE_H):
    lane = rect("lane:" + key, LANE_X, y, width, height, fill=LANE_FILL)
    lane["strokeColor"] = LANE_STROKE
    lane["strokeWidth"] = 1
    lane["fillStyle"] = "solid"
    label = text("lane-name:" + key, LANE_X + 10, y + 8, 160, name, align="left")
    return lane, label


def build_diagram(doc: Document, cfg: Config, findings: list[Finding]) -> dict:
    e1_lines = {f.linha for f in findings if f.id == "E1"}
    entries = [e for e in doc.timeline if e.stamp is not None]

    comps: list[str] = []
    comp_of: dict[int, str] = {}
    for e in entries:
        c = component_of(e.text, "", cfg) or NO_COMPONENT
        comp_of[e.line] = c
        if c not in comps:
            comps.append(c)

    top = 70
    lane_y = {c: top + i * LANE_H for i, c in enumerate(comps)}

    boxes, labels, entry_box = [], [], []
    x = 180
    prev = None
    for e in entries:
        when = _utc(e.stamp)
        if prev is not None:
            gap = max(0, int((when - prev).total_seconds() // 60))
            x += BOX_W + 40 + min(gap, 120) * 2
        prev = when
        no_ev = e.line in e1_lines
        content = f"{when:%H:%M} UTC\n" + short(_clean(e.text), 60)
        if no_ev:
            content += "\n" + NO_EVIDENCE
        fill = ROLE_FILL.get(e.marker or "", WHITE)
        key = f"entry:{e.line}"
        box, label = labeled_box(key, x, 0, content, fill=fill, dashed=no_ev)
        ly = lane_y[comp_of[e.line]]
        box["y"] = ly + (LANE_H - box["height"]) / 2
        label["y"] = box["y"] + (box["height"] - label["height"]) / 2
        boxes.append(box)
        labels.append(label)
        entry_box.append((e, box))

    timeline_right = x + BOX_W if entries else 180 + BOX_W
    factors_top = top + len(comps) * LANE_H + 60
    n = len(doc.factors)
    factors_right = 180 + max(n - 1, 0) * 280 + 240 if n else 0
    width = max(timeline_right, factors_right) + 20 - LANE_X

    elements = [text("title", 40, 20, 600, TITLE, size=24, align="left")]
    for c in comps:
        lane, name = _lane(c, lane_y[c], width, c)
        elements += [lane, name]

    f_boxes, f_labels, arrows = [], [], []
    if n:
        pairs = []
        for i, f in enumerate(doc.factors):
            minutes = {_utc(s).replace(second=0, microsecond=0) for s in f.stamps}
            target = next((b for e, b in entry_box
                           if _utc(e.stamp).replace(second=0, microsecond=0) in minutes), None)
            linked_ok = target is not None and next(
                e.line for e, b in entry_box if b is target) not in e1_lines
            comp = component_of(f.text, "", cfg)
            content = short(strip_markup(f.text), 90)
            if comp:
                content += f"\n[{comp}]"
            if not linked_ok:
                content += "\n" + NO_EVIDENCE
            box, label = labeled_box(f"factor:{i}", 180 + i * 280, 0, content,
                                     fill=FACTOR_FILL, dashed=not linked_ok,
                                     width=240)
            pairs.append((box, label, target))
        tallest = max(b["height"] for b, _, _ in pairs)
        lane_h = max(LANE_H, 40 + tallest + 20)
        lane, name = _lane("factors", factors_top, width, FACTORS_TITLE, lane_h)
        elements += [lane, name]
        for box, label, target in pairs:
            box["y"] = factors_top + 40
            label["y"] = box["y"] + (box["height"] - label["height"]) / 2
            f_boxes.append(box)
            f_labels.append(label)
        for i, (box, _, target) in enumerate(pairs):
            if target is not None:
                arrows.append(arrow(f"factor:{i}", box, target))

    for b, lb in zip(boxes, labels):
        elements += [b, lb]
    for b, lb in zip(f_boxes, f_labels):
        elements += [b, lb]
    elements += arrows
    return scene(elements)
