"""Entradas patológicas de 100 mil caracteres não podem travar o verificador."""
import time
import unittest
from datetime import date

from verifier.numbers import extract_durations
from verifier.parse_doc import _META, SEP_ROW
from verifier.redact import redact
from verifier.timestamps import find_stamps

LIMITE_S = 2.0
N = 100_000
CAB = "-----BEGIN " + "RSA PRIVATE KEY-----"


def cortar(texto: str, n: int = N) -> str:
    return texto[:n]


SHAPES = {
    "redact url pontos": lambda: redact(cortar("a." * N), "f"),
    "redact url hifen": lambda: redact(cortar("ab-cd" * N), "f"),
    "redact senha prefixo": lambda: redact(cortar("2026-" * N), "f"),
    "redact varias BEGIN sem END": lambda: redact(cortar((CAB + "\n") * N), "f"),
    "meta espacos": lambda: _META.match(" " * N + "x"),
    "meta espacos apos dois pontos": lambda: _META.match("data:" + " " * N + "x"),
    "sep_row espacos": lambda: SEP_ROW.match(" " * N + "x"),
    "sep_row celulas": lambda: SEP_ROW.match("|---" * (N // 4) + "x"),
    "stamps bare": lambda: find_stamps(cortar("10:00 " * N),
                                       default_date=date(2026, 9, 14)),
    "stamps iso": lambda: find_stamps(cortar("2026-09-14T10:00:00Z " * N)),
    "duracoes": lambda: extract_durations(cortar("1 h " * N)),
}


class RobustnessTest(unittest.TestCase):
    def test_formas_patologicas(self):
        for nome, fn in SHAPES.items():
            with self.subTest(nome):
                t0 = time.perf_counter()
                fn()
                gasto = time.perf_counter() - t0
                self.assertLess(gasto, LIMITE_S, f"{nome}: {gasto:.2f}s")

    def test_resultado_continua_correto(self):
        out, found = redact("senha: x1 e postgres://u:pw@h/db", "f")
        self.assertEqual(len(found), 2)
        self.assertEqual(len(find_stamps("10:00 10:05", default_date=date(2026, 9, 14))), 2)


if __name__ == "__main__":
    unittest.main()
