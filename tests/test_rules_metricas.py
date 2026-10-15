import unittest

from tests.helpers import check_case, ids


class MetricasTests(unittest.TestCase):
    def test_m1_marco_faltando(self):
        found, _ = check_case(replace={"[mitigacao] ": ""})
        self.assertIn("M1", ids(found))
        f = next(f for f in found if f.id == "M1")
        self.assertIn("[mitigacao]", f.mensagem)

    def test_m2_fora_de_ordem(self):
        found, _ = check_case(replace={"15:01 [deteccao]": "15:01 [mitigacao]",
                                       "15:36 [mitigacao]": "15:36 [deteccao]"})
        self.assertIn("M2", ids(found))

    def test_m3_rotulada(self):
        found, _ = check_case(replace={"TTD: 7 min": "TTD: 9 min"})
        self.assertIn("M3", ids(found))
        f = next(f for f in found if f.id == "M3")
        self.assertIn("9", f.mensagem)
        self.assertIn("7", f.mensagem)

    def test_m3_sem_rotulo(self):
        found, _ = check_case(replace={"TTM: 42 min.": "TTM: 42 min. O rollback levou 30 min."})
        self.assertIn("M3", ids(found))

    def test_m3_ignorada_se_metrica_ausente(self):
        found, _ = check_case(replace={"[mitigacao] ": ""})
        self.assertNotIn("M3", ids(found))


if __name__ == "__main__":
    unittest.main()
