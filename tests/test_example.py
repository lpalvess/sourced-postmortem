import json
import tempfile
import unittest
from pathlib import Path

from tests.test_cli import run

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples" / "checkout"


class ExampleCheckoutTest(unittest.TestCase):
    def test_exemplo_reprova_com_e2_e_m3(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, _ = run([str(EX / "postmortem.md"), str(EX / "evidencias"),
                              "--config", str(EX / "sourced-postmortem.toml"),
                              "--out", tmp])
            report = json.loads((Path(tmp) / "relatorio.json").read_text(encoding="utf-8"))
        reprova = sorted(a["id"] for a in report["achados"] if a["nivel"] == "reprova")
        self.assertEqual(code, 1)
        self.assertEqual(reprova, ["E2", "M3"])


if __name__ == "__main__":
    unittest.main()
