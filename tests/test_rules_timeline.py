import unittest

from tests.helpers import check_case, ids

TITULO = "## Linha do tempo (todos os horários em UTC)"


class TimelineTests(unittest.TestCase):
    def test_baseline_sem_t(self):
        found, _ = check_case()
        self.assertEqual([i for i in ids(found) if i.startswith("T")], [])

    def test_t1_sem_fuso(self):
        found, _ = check_case(replace={TITULO: "## Linha do tempo"})
        t1 = [f for f in found if f.id == "T1"]
        self.assertEqual(len(t1), 1)
        self.assertEqual(t1[0].linha, 21)
        self.assertIn("UTC", t1[0].mensagem)

    def test_t2_fora_de_ordem(self):
        found, _ = check_case(replace={"- 14:50 Deploy": "- 14:58 Deploy"})
        t2 = [f for f in found if f.id == "T2"]
        self.assertEqual(len(t2), 1)
        self.assertEqual(t2[0].linha, 24)

    def test_t3_vago(self):
        found, ctx = check_case(replace={"- 14:50 Deploy": "- cerca de 14:50 Deploy"})
        t3 = [f for f in found if f.id == "T3"]
        self.assertEqual(len(t3), 1)
        self.assertEqual(t3[0].nivel, "aviso")
        self.assertEqual(t3[0].linha, 23)
        self.assertEqual(ctx.doc.timeline[0].stamp.when.strftime("%H:%M"), "14:50")

    def test_t4_sem_lead_up(self):
        found, _ = check_case(replace={
            "- 14:50 Deploy da versão 4.2 do checkout-api concluído.\n": ""})
        t4 = [f for f in found if f.id == "T4"]
        self.assertEqual(len(t4), 1)
        self.assertEqual(t4[0].nivel, "aviso")

    def test_t5_data_ambigua(self):
        found, _ = check_case(replace={
            "- 16:00 [fim]": "- 03/04/2026 10:00 Nota.\n- 16:00 [fim]"})
        t5 = [f for f in found if f.id == "T5"]
        self.assertEqual(len(t5), 1)
        self.assertEqual(t5[0].nivel, "aviso")

    def test_t5_evidencia_um_por_arquivo_com_contagem(self):
        found, _ = check_case(evidence_extra={
            "amb.log": "03/04/2026 10:00:00 a\n05/06/2026 11:00:00 b\n"})
        t5 = [f for f in found if f.id == "T5"]
        self.assertEqual(len(t5), 1)
        self.assertIn("amb.log", t5[0].local)
        self.assertIn("2", t5[0].mensagem)

    def test_t6_evidencia_sem_fuso(self):
        found, _ = check_case(evidence_extra={
            "extra.log": "2026-09-14 15:10:00 nota\n"})
        t6 = [f for f in found if f.id == "T6"]
        self.assertEqual(len(t6), 1)
        self.assertEqual(t6[0].nivel, "aviso")
        self.assertIn("extra.log", t6[0].local)
        self.assertIn("UTC", t6[0].mensagem)


if __name__ == "__main__":
    unittest.main()
