import unittest

from tests.helpers import check_case, ids


def a_ids(found, nivel=None):
    return [i for i in ids(found, nivel) if i.startswith("A")]


class AcoesTests(unittest.TestCase):
    def test_baseline_sem_a_nem_o(self):
        found, _ = check_case()
        self.assertEqual([i for i in ids(found) if i[0] in "AO"], [])

    def test_a1_dono_vazio(self):
        found, _ = check_case(replace={"| ana.souza |": "|  |"})
        self.assertEqual(a_ids(found, "reprova"), ["A1"])

    def test_a1_dono_com_cara_de_time(self):
        found, _ = check_case(replace={"| ana.souza |": "| time-pagamentos |"})
        self.assertEqual(a_ids(found, "aviso"), ["A1"])
        self.assertEqual(a_ids(found, "reprova"), [])

    def test_a1_nenhuma_acao(self):
        found, _ = check_case(replace={"## Ações": "## Próximos passos"})
        a1 = [f for f in found if f.id == "A1"]
        self.assertEqual(len(a1), 1)
        self.assertEqual(a1[0].nivel, "reprova")
        self.assertIn("Nenhuma ação encontrada", a1[0].mensagem)

    def test_a2_ticket_vazio(self):
        found, _ = check_case(replace={"| PAY-101 |": "| - |"})
        self.assertEqual(a_ids(found), ["A2"])

    def test_a3_prioridade_invalida(self):
        found, _ = check_case(replace={"| P1 | prevent": "| alta | prevent"})
        self.assertEqual(a_ids(found, "reprova"), ["A3"])

    def test_a3_impacto_sem_p0_p1(self):
        found, _ = check_case(replace={"| P1 | prevent": "| P2 | prevent",
                                       "| P1 | mitigate": "| P3 | mitigate"})
        self.assertEqual(a_ids(found, "reprova"), ["A3"])

    def test_a3_todas_iguais_aviso(self):
        found, _ = check_case(replace={"| P2 | detect": "| P1 | detect"})
        self.assertEqual(a_ids(found, "aviso"), ["A3"])
        self.assertEqual(a_ids(found, "reprova"), [])

    def test_a4_tipo_invalido(self):
        found, _ = check_case(replace={"| detect |": "| melhoria |"})
        self.assertEqual(a_ids(found, "reprova"), ["A4"])

    def test_a4_falta_prevent(self):
        found, _ = check_case(replace={"| prevent |": "| repair |"})
        a4 = [f for f in found if f.id == "A4"]
        self.assertEqual(len(a4), 1)
        self.assertEqual(a4[0].nivel, "aviso")
        self.assertIn("prevent", a4[0].mensagem)

    def test_a5_prazo_invalido(self):
        found, _ = check_case(replace={"| 2026-10-10 |": "| logo |"})
        self.assertEqual(a_ids(found, "reprova"), ["A5"])

    def test_a5_prazo_longo(self):
        found, _ = check_case(replace={"| 2026-10-10 |": "| 2026-11-30 |"})
        self.assertEqual(a_ids(found, "aviso"), ["A5"])

    def test_a5_severidade_fora_da_tabela_nao_levanta(self):
        found, _ = check_case(
            replace={"| 2026-10-10 |": "| 2026-11-30 |"},
            config_text="[perfil]\nprazo_dias = { SEV1 = 15 }\n")
        self.assertEqual(a_ids(found), [])

    def test_a6_verbo_vago(self):
        found, _ = check_case(replace={"Reduzir o limiar": "Revisar o limiar"})
        self.assertEqual(a_ids(found, "reprova"), ["A6"])


if __name__ == "__main__":
    unittest.main()
