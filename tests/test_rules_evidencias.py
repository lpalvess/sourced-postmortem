import unittest

from tests.helpers import check_case, ids

FIXTURE_TOML = """[times.pagamentos]
componentes = ["checkout-api"]
membros = ["ana.souza", "@joao"]

[times.plataforma]
componentes = ["ingress"]
membros = ["@maria"]
"""
ACK = "- 15:05 [reconhecimento]"


class EvidenciasTests(unittest.TestCase):
    def test_baseline_sem_achados_e_m(self):
        found, _ = check_case()
        self.assertEqual([i for i in ids(found) if i[0] in "EM"], [])

    def test_e1_horario_sem_evidencia(self):
        found, _ = check_case(replace={ACK: "- 15:07 [reconhecimento]"})
        self.assertIn("E1", ids(found))
        f = next(f for f in found if f.id == "E1")
        self.assertIn("15:07", f.mensagem)
        self.assertEqual(f.nivel, "reprova")
        self.assertEqual(f.fonte, ("P4",))

    def test_e1_evidencia_traz_registro_mais_proximo(self):
        valor = "SEGREDO" + "E1"
        linha = "2026-09-14T15:09:30Z token=" + valor + " " + "x" * 400
        found, _ = check_case(replace={ACK: "- 15:12 [reconhecimento]"},
                              evidence_extra={"perto.log": linha + "\n"})
        f = next(f for f in found if f.id == "E1")
        self.assertIsNotNone(f.evidencia)
        self.assertTrue(f.evidencia.startswith("perto.log:1: 2026-09-14T15:09:30Z"))
        self.assertNotIn(valor, f.evidencia)
        self.assertIn("[OCULTO:senha-chave]", f.evidencia)
        prefixo = "perto.log:1: "
        self.assertLessEqual(len(f.evidencia) - len(prefixo), 200)

    def test_e2_sem_evidencia_campo_vazio(self):
        found, _ = check_case(replace={"1.240 pedidos": "9.999 pedidos"})
        self.assertIsNone(next(f for f in found if f.id == "E2").evidencia)

    def test_e1_evidencia_local_com_offset(self):
        found, _ = check_case(
            replace={ACK: "- 15:09 [reconhecimento]"},
            evidence_extra={"ack.log": "2026-09-14T12:09:30-03:00 ack\n"})
        self.assertNotIn("E1", ids(found))

    def test_e1_desligada(self):
        found, _ = check_case(replace={ACK: "- 15:12 [reconhecimento]"},
                              config_text=FIXTURE_TOML + '\n[niveis]\nE1 = "desligada"\n')
        self.assertNotIn("E1", ids(found))

    def test_e1_nivel_aviso(self):
        found, _ = check_case(replace={ACK: "- 15:12 [reconhecimento]"},
                              config_text=FIXTURE_TOML + '\n[niveis]\nE1 = "aviso"\n')
        self.assertEqual(ids(found, "aviso"), ["E1"])

    def test_e2_numero_sem_evidencia(self):
        found, _ = check_case(replace={"3 clientes": "5 clientes"})
        self.assertIn("E2", ids(found))
        f = next(f for f in found if f.id == "E2")
        self.assertIn("5 clientes", f.mensagem)


if __name__ == "__main__":
    unittest.main()
