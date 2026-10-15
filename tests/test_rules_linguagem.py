import unittest
from pathlib import Path

from tests.helpers import APROVADO, check_case, ids


def l_ids(found, nivel=None):
    return [i for i in ids(found, nivel) if i.startswith("L")]


class LinguagemTests(unittest.TestCase):
    def test_baseline_vazio(self):
        found, _ = check_case()
        self.assertEqual(found, [])

    def test_l1_termo_de_culpa(self):
        found, _ = check_case(
            replace={"trocou o pool": "por descuido trocou o pool"})
        self.assertEqual(l_ids(found), ["L1"])
        self.assertEqual(l_ids(found, "aviso"), ["L1"])

    def test_l1_nivel_configurado(self):
        toml = (APROVADO / "sourced-postmortem.toml").read_text(
            encoding="utf-8")
        found, _ = check_case(
            replace={"trocou o pool": "por descuido trocou o pool"},
            config_text=toml + '\n[niveis]\nL1 = "reprova"\n')
        self.assertEqual(l_ids(found, "reprova"), ["L1"])

    def test_l1_desculpa_nao_dispara(self):
        found, _ = check_case(
            replace={"trocou o pool": "pediu desculpa e trocou o pool"})
        self.assertEqual(l_ids(found), [])

    def test_l1_exclamacoes_e_um_aviso_por_linha(self):
        found, _ = check_case(
            replace={"trocou o pool": "obviamente culpa dele!!! trocou o pool"})
        l1 = [f for f in found if f.id == "L1"]
        self.assertEqual(len(l1), 1)
        for t in ("obviamente", "culpa", "!!!"):
            self.assertIn(t, l1[0].mensagem)

    def test_l2_handle(self):
        found, _ = check_case(
            replace={"Plantão reconheceu o alerta.":
                     "@joao reconheceu o alerta."})
        self.assertEqual(l_ids(found), ["L2"])

    def test_l2_nome_de_membro(self):
        found, ctx = check_case()
        membro = next(m for t in ctx.cfg.times for m in t.membros)
        nome = membro.lstrip("@")
        found, _ = check_case(
            replace={"Plantão reconheceu o alerta.":
                     f"{nome} reconheceu o alerta."})
        self.assertEqual(l_ids(found), ["L2"])


if __name__ == "__main__":
    unittest.main()
