import unittest

from tests.helpers import check_case
from verifier.metrics import DEFINITIONS, METRICS, compute, milestones, tolerance_minutes


class MetricsTests(unittest.TestCase):
    def test_compute_fixture(self):
        _, ctx = check_case()
        self.assertEqual(compute(ctx.milestones),
                         {"TTD": 7, "TTA": 11, "TTM": 42, "TTR": 66, "duracao": 66})
        self.assertEqual(ctx.metrics, compute(ctx.milestones))

    def test_milestones_first_with_stamp(self):
        _, ctx = check_case()
        ms = milestones(ctx.doc.timeline)
        self.assertEqual(set(ms), {"inicio", "deteccao", "reconhecimento", "mitigacao", "fim"})
        self.assertEqual(ms["inicio"].line, ctx.milestones["inicio"].line)

    def test_compute_partial(self):
        _, ctx = check_case(replace={"[mitigacao] ": ""})
        self.assertNotIn("TTM", ctx.metrics)
        self.assertIn("TTD", ctx.metrics)

    def test_tolerance(self):
        self.assertEqual(tolerance_minutes(0), 1.0)
        self.assertEqual(tolerance_minutes(60), 2.0)

    def test_definitions(self):
        self.assertEqual(set(DEFINITIONS), set(METRICS))
        self.assertIn("G2", DEFINITIONS["duracao"])


if __name__ == "__main__":
    unittest.main()
