import os
import tempfile
import unittest

from verifier.config import DEFAULT_MARCOS, DEFAULT_SECOES, Config, load_config
from verifier.model import ConfigError

SPEC_TOML = """
[perfil]
tolerancia_segundos = 0
prazo_dias = { SEV1 = 15, SEV2 = 30 }
limite_evidencias_mb = 50
formato_data = "DMY"

[niveis]
L2 = "desligada"

[marcos]
deteccao = ["pagerduty acionou"]

[times.pagamentos]
componentes = ["checkout-api", "payment-worker"]
membros = ["ana.souza", "@joao"]

[times.plataforma]
componentes = ["ingress", "kafka"]
membros = ["@maria"]
"""


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, text):
        path = os.path.join(self.tmp.name, "sourced-postmortem.toml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def assertRejects(self, text, *needles):
        path = self.write(text)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        msg = str(cm.exception)
        self.assertIn("sourced-postmortem.toml", msg)
        for n in needles:
            self.assertIn(n, msg)

    def test_defaults(self):
        c = load_config(None)
        self.assertIsInstance(c, Config)
        self.assertEqual(c.prazo_dias["SEV1"], 15)
        self.assertEqual(c.tolerancia_segundos, 0)
        self.assertEqual(c.limite_evidencias_mb, 50)
        self.assertIsNone(c.formato_data)
        self.assertEqual(c.times, ())

    def test_default_dicts_not_shared(self):
        a = load_config(None)
        a.prazo_dias["SEV1"] = 1
        self.assertEqual(load_config(None).prazo_dias["SEV1"], 15)

    def test_default_synonyms_normalized(self):
        self.assertIn("inicio do impacto", DEFAULT_MARCOS["inicio"])
        self.assertIn("acoes corretivas", DEFAULT_SECOES["acoes"])
        self.assertIn("visao geral", DEFAULT_SECOES["resumo"])
        self.assertIn("gatilho", DEFAULT_SECOES["causa"])

    def test_spec_example(self):
        c = load_config(self.write(SPEC_TOML))
        self.assertEqual(c.niveis["L2"], "desligada")
        self.assertIn("pagerduty acionou", c.marcos["deteccao"])
        self.assertIn("detectado", c.marcos["deteccao"])
        self.assertEqual(len(c.times), 2)
        self.assertEqual(c.formato_data, "DMY")

    def test_additions_are_normalized(self):
        c = load_config(self.write('[secoes]\nresumo = ["Visão Geral", "Sumário"]\n'))
        self.assertIn("sumario", c.secoes["resumo"])

    def test_prazo_keys_uppercased(self):
        c = load_config(self.write("[perfil]\nprazo_dias = { sev3 = 60 }\n"))
        self.assertEqual(c.prazo_dias["SEV3"], 60)

    def test_unknown_top_key(self):
        self.assertRejects("[outra]\na = 1\n", "outra")

    def test_unknown_rule(self):
        self.assertRejects('[niveis]\nX9 = "aviso"\n', "X9")

    def test_invalid_level(self):
        self.assertRejects('[niveis]\nE1 = "talvez"\n', "E1")

    def test_broken_toml(self):
        self.assertRejects("[perfil\n", "line")

    def test_bad_date_format(self):
        self.assertRejects('[perfil]\nformato_data = "YMD"\n', "formato_data")

    def test_bad_team_key(self):
        self.assertRejects('[times.a]\nchefe = "x"\n', "chefe")

    def test_negative_tolerance(self):
        self.assertRejects("[perfil]\ntolerancia_segundos = -1\n", "tolerancia_segundos")

    def test_bool_not_int(self):
        self.assertRejects("[perfil]\ntolerancia_segundos = true\n", "tolerancia_segundos")

    def test_bad_marker_key(self):
        self.assertRejects('[marcos]\nzzz = ["a"]\n', "zzz")

    def test_marker_not_strings(self):
        self.assertRejects("[marcos]\ndeteccao = [1]\n", "deteccao")

    def test_bad_prazo(self):
        self.assertRejects("[perfil]\nprazo_dias = { SEV1 = 0 }\n", "prazo_dias")

    def test_missing_file(self):
        with self.assertRaises(ConfigError) as cm:
            load_config(os.path.join(self.tmp.name, "nao-existe.toml"))
        self.assertIn("nao-existe.toml", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
