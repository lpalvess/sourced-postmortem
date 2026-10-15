import tempfile
import unittest
from datetime import date
from pathlib import Path

from tests.helpers import APROVADO
from verifier.config import Config
from verifier.evidence import EXCERPT_CHARS, load_evidence
from verifier.model import InputError
from verifier.timestamps import UTC

KW = dict(default_date=date(2026, 9, 14), default_tz=UTC)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def folder(self, files: dict[str, str]) -> Path:
        for name, content in files.items():
            p = self.tmp / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        return self.tmp

    def test_fixture(self):
        ev = load_evidence(APROVADO / "evidencias", Config(), **KW)
        by_file: dict[str, list] = {}
        for r in ev.records:
            by_file.setdefault(r.file, []).append(r)
        for name in ("app.log", "access.log", "alertmanager.json", "incident-timeline.csv"):
            self.assertTrue(any(r.stamps for r in by_file[name]), name)
        self.assertFalse(any(r.stamps for r in by_file.get("chamados.txt", [])))
        am = by_file["alertmanager.json"]
        self.assertEqual(len(am), 1)
        self.assertEqual(len(am[0].stamps), 2)
        for n in ("1240", "18", "3"):
            self.assertIn(n, ev.numbers)
        self.assertEqual(ev.assumed_tz_files, [])

    def test_limit(self):
        folder = self.folder({"big.log": "x" * (2 * 1024 * 1024)})
        with self.assertRaises(InputError) as cm:
            load_evidence(folder, Config(limite_evidencias_mb=1), **KW)
        self.assertIn("limite_evidencias_mb", str(cm.exception))

    def test_hidden_ignored(self):
        folder = self.folder({".oculto/x.log": "2026-09-14T15:00:00Z a=1\n",
                              "ok.log": "2026-09-14T15:00:00Z b=2\n"})
        ev = load_evidence(folder, Config(), **KW)
        self.assertEqual({r.file for r in ev.records}, {"ok.log"})

    def test_empty_and_missing(self):
        with self.assertRaises(InputError) as cm:
            load_evidence(self.tmp, Config(), **KW)
        self.assertIn("vazia", str(cm.exception))
        with self.assertRaises(InputError):
            load_evidence(self.tmp / "nao-existe", Config(), **KW)
        f = self.folder({"a.log": "x"}) / "a.log"
        with self.assertRaises(InputError):
            load_evidence(f, Config(), **KW)

    def test_assumed_tz(self):
        folder = self.folder({"a.log": "2026-09-14 15:10:00 sem fuso\n"})
        ev = load_evidence(folder, Config(), **KW)
        self.assertEqual(ev.assumed_tz_files, ["a.log"])

    def test_secret_same_line_as_stamp(self):
        segredo = "abc123" + "segredo"
        folder = self.folder({"s.log": f"2026-09-14T15:01:30Z token={segredo}\n"})
        ev = load_evidence(folder, Config(), **KW)
        self.assertEqual(len(ev.records), 1)
        r = ev.records[0]
        self.assertEqual(len(r.stamps), 1)
        self.assertIn("[OCULTO:senha-chave]", r.excerpt)
        self.assertNotIn(segredo, r.excerpt)
        self.assertEqual([(x.file, x.line, x.kind) for x in ev.redactions],
                         [("s.log", 1, "senha-chave")])

    def test_excerpt_truncated_and_line_numbers(self):
        folder = self.folder({"a.log": "\n\n  2026-09-14T15:00:00Z " + "y" * 500 + "\n"})
        ev = load_evidence(folder, Config(), **KW)
        self.assertEqual(ev.records[0].line, 3)
        self.assertEqual(len(ev.records[0].excerpt), EXCERPT_CHARS)

    def test_ambiguous_and_unparsed(self):
        folder = self.folder({"a.log": "03/04/2026 10:00:00 a\n2026-13-45T10:00:00Z b\n"})
        ev = load_evidence(folder, Config(), **KW)
        self.assertEqual(len(ev.ambiguous), 1)
        self.assertEqual(len(ev.unparsed), 1)
        self.assertEqual(ev.unparsed[0].file, "a.log")


if __name__ == "__main__":
    unittest.main()
