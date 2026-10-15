import unittest

from verifier.catalog import LEVELS, MARKERS, RULES, SECTION_KEYS, SOURCES

EXPECTED_IDS = {
    "E1", "E2", "M1", "M2", "M3", "T1", "T2", "T3", "T4", "T5", "T6",
    "A1", "A2", "A3", "A4", "A5", "A6", "O1", "L1", "L2",
}


class CatalogTests(unittest.TestCase):
    def test_rule_ids(self):
        self.assertEqual(set(RULES), EXPECTED_IDS)
        self.assertEqual(len(RULES), 20)

    def test_sources_known(self):
        for rid, (_id, _level, fontes, _title) in RULES.items():
            for code in fontes:
                self.assertTrue(code in SOURCES or code == "config", (rid, code))

    def test_levels(self):
        for rid, (_id, level, _f, _t) in RULES.items():
            self.assertIn(level, LEVELS, rid)

    def test_special_cases(self):
        self.assertEqual(RULES["T5"][2], ())
        self.assertEqual(RULES["T6"][2], ())
        self.assertEqual(RULES["O1"][2], ("config",))
        for rid in ("A1", "A3", "A4", "A5"):
            self.assertEqual(RULES[rid][1], "reprova")

    def test_sources_complete(self):
        codes = ([f"G{i}" for i in range(1, 5)] + [f"P{i}" for i in range(1, 7)]
                 + [f"A{i}" for i in range(1, 6)] + [f"I{i}" for i in range(1, 9)]
                 + ["F1", "F2", "E1", "D1"])
        self.assertEqual(set(SOURCES), set(codes))
        for url in SOURCES.values():
            self.assertTrue(url.startswith("https://"))

    def test_constants(self):
        self.assertEqual(LEVELS, ("reprova", "aviso", "desligada"))
        self.assertEqual(len(MARKERS), 5)
        self.assertEqual(len(SECTION_KEYS), 5)


if __name__ == "__main__":
    unittest.main()
