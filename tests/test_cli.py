import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import copy_case
from verifier.cli import main
from verifier.report import render_markdown


def run(argv):
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def args(doc, ev, cfg, out):
    return [str(doc), str(ev), "--config", str(cfg), "--out", str(out)]


def secrets() -> dict[str, str]:
    jwt = "eyJ" + "h" * 12 + "." + "p" * 12 + "." + "s" * 12
    return {
        "aws-key": "AKIA" + "Q" * 16,
        "github-token": "ghp_" + "a" * 36,
        "slack-token": "xoxb-" + "1" * 12 + "-" + "2" * 12 + "-" + "c" * 12,
        "jwt": jwt,
        "bearer": "zZ9" * 6 + "yY8",
        "private-key": "MIIE" + "k" * 30,
        "senha-chave": "hunter" + "9" * 4 + "pw",
        "url-credencial": "p4ss" + "w" * 8 + "xyz",
        "aws-secret": "A1b2C3d4E5" * 4,
        "impacto": "hunter22segredo",
    }


class CliTest(unittest.TestCase):
    def case(self, replace=None, evidence_extra=None):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        tmp = Path(t.name)
        doc, ev, cfg = copy_case(tmp / "caso", replace, evidence_extra)
        return doc, ev, cfg, tmp / "saida"

    def test_aprovado(self):
        doc, ev, cfg, out = self.case()
        code, stdout, _ = run(args(doc, ev, cfg, out))
        self.assertEqual(code, 0)
        self.assertIn("aprovado: 0 reprovações", stdout)
        for name in ("relatorio.json", "relatorio.md", "diagrama.excalidraw"):
            self.assertTrue((out / name).is_file(), name)
        rep = json.loads((out / "relatorio.json").read_text(encoding="utf-8"))
        self.assertEqual(rep["resultado"], "aprovado")
        self.assertEqual(rep["marcos"]["inicio"], "2026-09-14T14:54:00Z")
        self.assertEqual(rep["metricas_min"]["TTD"], 7.0)
        for chave in ("versao", "documento", "fuso_do_documento", "definicoes",
                      "achados", "credenciais_ocultadas", "nao_interpretado",
                      "acoes", "mapa_de_times", "fontes"):
            self.assertIn(chave, rep)
        self.assertEqual(rep["acoes"][0]["time_sugerido"], "pagamentos")

    def test_e2_reprova(self):
        doc, ev, cfg, out = self.case(replace={"3 clientes": "5 clientes"})
        code, stdout, _ = run(args(doc, ev, cfg, out))
        self.assertEqual(code, 1)
        self.assertIn("reprovado:", stdout)
        rep = json.loads((out / "relatorio.json").read_text(encoding="utf-8"))
        self.assertEqual(rep["resultado"], "reprovado")
        e2 = next(a for a in rep["achados"] if a["id"] == "E2")
        self.assertEqual(e2["fonte"], ["G3"])
        self.assertIn("G3", rep["fontes"])

    def test_documento_inexistente(self):
        doc, ev, cfg, out = self.case()
        code, _, err = run(args(doc.with_name("nao-existe.md"), ev, cfg, out))
        self.assertEqual(code, 2)
        self.assertIn("não encontrado", err)

    def test_toml_quebrado(self):
        doc, ev, cfg, out = self.case()
        cfg.write_text("[times\nquebrado", encoding="utf-8")
        code, _, _ = run(args(doc, ev, cfg, out))
        self.assertEqual(code, 3)

    def test_vazamento(self):
        s = secrets()
        evid = "\n".join([
            "2026-09-14T15:01:30Z token=" + s["senha-chave"],
            "chave " + s["aws-key"],
            "gh " + s["github-token"],
            "slack " + s["slack-token"],
            "jwt " + s["jwt"],
            "Authorization: Bearer " + s["bearer"],
            "-----BEGIN RSA PRIVATE KEY-----",
            s["private-key"],
            "-----END RSA PRIVATE KEY-----",
            "mysql://admin:" + s["url-credencial"] + "@db.interno:3306/app",
            "aws_secret_access_key = " + s["aws-secret"],
            "",
        ])
        doc, ev, cfg, out = self.case(
            replace={"## Impacto\n": "## Impacto\n\nsenha: hunter22segredo\n"},
            evidence_extra={"segredos.log": evid})
        code, _, _ = run(args(doc, ev, cfg, out))
        self.assertIn(code, (0, 1))
        textos = [(out / n).read_text(encoding="utf-8") for n in
                  ("relatorio.json", "relatorio.md", "diagrama.excalidraw")]
        for chave, valor in s.items():
            for texto in textos:
                self.assertNotIn(valor, texto, chave)
        rep = json.loads(textos[0])
        tipos = {c["tipo"] for c in rep["credenciais_ocultadas"]}
        self.assertTrue(tipos)
        for esperado in ("aws-key", "github-token", "slack-token", "jwt",
                         "bearer", "private-key", "senha-chave",
                         "url-credencial", "aws-secret"):
            self.assertIn(esperado, tipos)
        for c in rep["credenciais_ocultadas"]:
            self.assertEqual(set(c), {"arquivo", "linha", "tipo"})
        self.assertIn("postmortem.md", {c["arquivo"] for c in
                                        rep["credenciais_ocultadas"]})

    def test_markdown_sem_travessao_nem_seta(self):
        doc, ev, cfg, out = self.case(replace={"3 clientes": "5 clientes"})
        run(args(doc, ev, cfg, out))
        rep = json.loads((out / "relatorio.json").read_text(encoding="utf-8"))
        for r in (rep, dict(rep, achados=[], acoes=[], mapa_de_times={},
                            credenciais_ocultadas=[], nao_interpretado=[])):
            md = render_markdown(r)
            for ruim in ("—", "–", "->"):
                self.assertNotIn(ruim, md)
        self.assertIn("[times]", render_markdown(dict(rep, mapa_de_times={})))


if __name__ == "__main__":
    unittest.main()
