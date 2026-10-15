import unittest

from verifier.text import norm, short, starts_word, word_in


class TextTests(unittest.TestCase):
    def test_norm(self):
        self.assertEqual(norm("**Ações** Corretivas"), "acoes corretivas")

    def test_word_in(self):
        self.assertFalse(word_in("ack", "rollback concluido"))
        self.assertTrue(word_in("ack", "on-call deu ack"))

    def test_starts_word(self):
        self.assertTrue(starts_word("negligen", "foi negligente"))
        self.assertFalse(starts_word("culpa", "desculpa"))

    def test_short(self):
        s = short("a" * 70)
        self.assertEqual(len(s), 60)
        self.assertTrue(s.endswith("..."))
        self.assertEqual(short("curto"), "curto")


if __name__ == "__main__":
    unittest.main()
