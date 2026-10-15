import json
import os
import unittest
from pathlib import Path

from tests.helpers import check_case
from verifier import excalidraw as ex

GOLDEN = Path(__file__).parent / "golden" / "aprovado.excalidraw"
ACK = "- 15:05 [reconhecimento]"


def build(replace=None):
    found, ctx = check_case(replace=replace)
    return ex.build_diagram(ctx.doc, ctx.cfg, found), ctx, found


def by_id(elements):
    return {e["id"]: e for e in elements}


class ExcalidrawTests(unittest.TestCase):
    def test_deterministico(self):
        a = ex.dumps(build()[0])
        b = ex.dumps(build()[0])
        self.assertEqual(a, b)
        self.assertTrue(a.endswith("}\n"))

    def test_estilo_manual(self):
        els = build()[0]["elements"]
        for e in els:
            self.assertEqual(e["roughness"], 1)
            if e["type"] == "text":
                self.assertEqual(e["fontFamily"], 5)

    def test_cena_e_ids(self):
        sc = build()[0]
        self.assertEqual(sc["type"], "excalidraw")
        self.assertEqual(sc["version"], 2)
        self.assertEqual(sc["files"], {})
        ids = [e["id"] for e in sc["elements"]]
        self.assertEqual(len(ids), len(set(ids)))
        title = sc["elements"][0]
        self.assertEqual(title["text"], "Linha do tempo (UTC): onde aconteceu")
        self.assertEqual((title["x"], title["y"], title["fontSize"]), (40, 20, 24))
        self.assertEqual(title["textAlign"], "left")

    def test_faixas_de_150(self):
        els = build()[0]["elements"]
        lanes = [e for e in els if e["type"] == "rectangle"
                 and e["backgroundColor"] == "#f8f9fa"]
        self.assertEqual(len(lanes), 3)
        self.assertEqual(lanes[2]["y"], lanes[1]["y"] + 150 + 60)
        self.assertEqual([ln["height"] for ln in lanes[:2]], [150, 150])
        self.assertGreaterEqual(lanes[2]["height"], 150)
        for ln in lanes:
            self.assertEqual(ln["strokeColor"], "#868e96")
            self.assertEqual(ln["strokeWidth"], 1)

    def test_eixo_x_e_cores(self):
        els = build()[0]["elements"]
        texts = [e for e in els if e["type"] == "text" and e["text"].startswith("14:50 UTC")]
        self.assertEqual(texts[0]["text"].splitlines()[0], "14:50 UTC")
        boxes = [e for e in els if e["type"] == "rectangle"
                 and e["backgroundColor"] not in ("#f8f9fa", "#e9ecef")]
        self.assertEqual(boxes[0]["x"], 180)
        self.assertEqual(boxes[1]["x"], 180 + 240 + 4 * 2)
        self.assertEqual(boxes[1]["backgroundColor"], "#ffc9c9")
        self.assertEqual(boxes[2]["backgroundColor"], "#a5d8ff")
        self.assertEqual(boxes[0]["fillStyle"], "solid")
        self.assertEqual(boxes[1]["fillStyle"], "hachure")

    def test_e1_tracejado_com_rotulo(self):
        sc, ctx, found = build({ACK: "- 15:07 [reconhecimento]"})
        e1 = next(f for f in found if f.id == "E1")
        entry = next(t for t in ctx.doc.timeline if t.line == e1.linha)
        self.assertEqual(entry.marker, "reconhecimento")
        txt = next(e for e in sc["elements"] if e["type"] == "text"
                   and e["text"].startswith("15:07 UTC"))
        self.assertIn("sem evidência", txt["text"])
        box = by_id(sc["elements"])[txt["containerId"]]
        self.assertEqual(box["strokeStyle"], "dashed")

    def test_aprovado_sem_tracejado(self):
        els = build()[0]["elements"]
        self.assertFalse([e for e in els if e.get("strokeStyle") == "dashed"])
        self.assertFalse([e for e in els if e["type"] == "text"
                          and "sem evidência" in e["text"]])

    def test_fatores_com_seta(self):
        sc, ctx, _ = build()
        els = by_id(sc["elements"])
        arrows = [e for e in sc["elements"] if e["type"] == "arrow"]
        self.assertEqual(len(arrows), 2)
        factor_boxes = [e for e in sc["elements"] if e["type"] == "rectangle"
                        and e["backgroundColor"] == "#e9ecef"]
        self.assertEqual(len(factor_boxes), 2)
        for a in arrows:
            src = els[a["startBinding"]["elementId"]]
            dst = els[a["endBinding"]["elementId"]]
            self.assertIn(src, factor_boxes)
            self.assertNotIn(dst, factor_boxes)
            self.assertIn({"id": a["id"], "type": "arrow"}, src["boundElements"])
            self.assertIn({"id": a["id"], "type": "arrow"}, dst["boundElements"])
            self.assertEqual(a["endArrowhead"], "arrow")
            self.assertEqual(a["points"][0], [0, 0])

    def test_anchors(self):
        a = ex.rect("a", 0, 0, 200, 80, fill="#ffffff")
        right = ex.rect("b", 400, 0, 200, 80, fill="#ffffff")
        below = ex.rect("c", 0, 300, 200, 80, fill="#ffffff")
        self.assertEqual(ex.anchors(a, right), ((200, 40), (400, 40)))
        self.assertEqual(ex.anchors(right, a), ((400, 40), (200, 40)))
        self.assertEqual(ex.anchors(a, below), ((100, 80), (100, 300)))
        self.assertEqual(ex.anchors(below, a), ((100, 300), (100, 80)))

    def test_golden(self):
        out = ex.dumps(build()[0])
        if os.environ.get("UPDATE_GOLDEN") == "1":
            GOLDEN.write_text(out, encoding="utf-8")
        self.assertEqual(GOLDEN.read_text(encoding="utf-8"), out)
        json.loads(out)


if __name__ == "__main__":
    unittest.main()
