import unittest

from verifier import numbers as nb


class NumberFormsTest(unittest.TestCase):
    def test_table(self):
        cases = {
            "1.240": {"1240", "1.24"},
            "12,5": {"12.5"},
            "10.0.0.7": {"10", "0", "7"},
            "1.234,5": {"1234.5"},
            "1,234.5": {"1234.5"},
            "42": {"42"},
            "007": {"7"},
            "1.240.000": {"1240000"},
        }
        for raw, forms in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(nb.number_forms(raw), frozenset(forms))

    def test_odd_input_does_not_raise(self):
        self.assertEqual(nb.number_forms(""), frozenset())
        self.assertIsInstance(nb.number_forms("9" * 5000), frozenset)
        self.assertIsInstance(nb.number_forms("1." * 3000 + "1"), frozenset)
        self.assertIsInstance(nb.number_forms("abc"), frozenset)
        self.assertEqual(nb.extract_quantities(""), [])
        self.assertEqual(nb.extract_numbers(""), frozenset())
        self.assertEqual(nb.extract_durations(""), [])
        self.assertIsInstance(nb.extract_durations("9" * 5000 + " min"), list)
        self.assertIsInstance(nb.extract_numbers("9" * 5000), frozenset)

    def test_long_digits_exact(self):
        self.assertEqual(nb.number_forms("1" * 40), frozenset({"1" * 40}))


class QuantitiesTest(unittest.TestCase):
    def raws(self, text):
        return [r for r, _ in nb.extract_quantities(text)]

    def test_units(self):
        self.assertEqual(
            self.raws("1.240 pedidos falharam, cerca de 18% do total. 3 clientes"),
            ["1.240 pedidos", "18%", "3 clientes"],
        )

    def test_forms_attached(self):
        q = nb.extract_quantities("1.240 pedidos")
        self.assertEqual(q[0][1], frozenset({"1240", "1.24"}))

    def test_no_quantities(self):
        self.assertEqual(self.raws("SEV2 v4.2 66 min às 14:54 em 2026-09-14"), [])

    def test_brl(self):
        self.assertEqual(self.raws("prejuízo de R$ 12.000"), ["R$ 12.000"])


class NumbersTest(unittest.TestCase):
    def test_extract_numbers(self):
        got = nb.extract_numbers("error_rate=3 version=4.2 at 2026-09-14T14:50:12Z")
        self.assertIn("3", got)
        self.assertIn("4.2", got)
        self.assertNotIn("2026", got)


class DurationsTest(unittest.TestCase):
    def test_labeled(self):
        self.assertEqual(
            nb.extract_durations("A duração do impacto foi de 66 min. TTD: 7 min. TTM: 42 min."),
            [("66 min", 66, "duracao"), ("7 min", 7, "TTD"), ("42 min", 42, "TTM")],
        )

    def test_unlabeled(self):
        self.assertEqual(nb.extract_durations("O rollback levou 30 min"), [("30 min", 30, None)])

    def test_clock_time_is_not_duration(self):
        self.assertEqual(nb.extract_durations("Começou às 15h30"), [])

    def test_hm_labeled(self):
        self.assertEqual(nb.extract_durations("TTR de 1h06"), [("1h06", 66, "TTR")])

    def test_hours(self):
        (raw, mins, label), = nb.extract_durations("durou 2 horas")
        self.assertEqual((mins, label), (120, "duracao"))

    def test_labeled_only(self):
        self.assertEqual(nb.extract_durations("cache expira em 5 min", labeled_only=True), [])

    def test_glued_hour_not_duration(self):
        self.assertEqual(nb.extract_durations("às 15h"), [])


if __name__ == "__main__":
    unittest.main()
