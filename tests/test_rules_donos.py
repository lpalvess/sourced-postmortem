import unittest

from tests.helpers import check_case, ids
from verifier.rules.donos import component_of, team_for


def o_ids(found):
    return [i for i in ids(found) if i.startswith("O")]


class DonosTests(unittest.TestCase):
    def test_baseline_sem_o(self):
        found, _ = check_case()
        self.assertEqual(o_ids(found), [])

    def test_o1_dono_fora_do_time(self):
        found, _ = check_case(replace={"| @joao |": "| @maria |"})
        o1 = [f for f in found if f.id == "O1"]
        self.assertEqual(len(o1), 1)
        self.assertEqual(o1[0].nivel, "aviso")
        self.assertIn("pagamentos", o1[0].mensagem)

    def test_o1_componente_sem_time(self):
        found, _ = check_case(replace={"| ingress |": "| kafka |"})
        self.assertEqual(o_ids(found), ["O1"])

    def test_sem_times_sem_o1(self):
        found, _ = check_case(config_text="")
        self.assertEqual(o_ids(found), [])

    def test_component_of_e_team_for(self):
        _, ctx = check_case()
        cfg = ctx.cfg
        self.assertEqual(component_of(
            "Automatizar o rollback no ingress", "", cfg), "ingress")
        self.assertEqual(component_of("x", " kafka ", cfg), "kafka")
        self.assertIsNone(component_of("nada aqui", "", cfg))
        self.assertEqual(team_for("Checkout-API", cfg).name, "pagamentos")
        self.assertIsNone(team_for("kafka", cfg))


if __name__ == "__main__":
    unittest.main()
