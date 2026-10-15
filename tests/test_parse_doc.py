import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from tests.helpers import APROVADO, copy_case
from verifier.config import Config
from verifier.model import InputError
from verifier.parse_doc import parse_document
from verifier.timestamps import UTC

TL_TITLE = "## Linha do tempo (todos os horários em UTC)"


class ParseDocTest(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.tmp = Path(self._t.name)

    def parse(self, replace=None, name="c"):
        doc, _, _ = copy_case(self.tmp / name, replace)
        return parse_document(doc, Config())

    def test_fixture(self):
        d = parse_document(APROVADO / "postmortem.md", Config())
        for k in ("resumo", "impacto", "causa", "timeline", "acoes"):
            self.assertIsNotNone(d.section(k), k)
        self.assertEqual(d.tz, UTC)
        self.assertEqual(d.incident_date, date(2026, 9, 14))
        self.assertEqual(d.severity, "SEV2")
        self.assertEqual(len(d.timeline), 6)
        self.assertEqual([e.marker for e in d.timeline],
                         [None, "inicio", "deteccao", "reconhecimento", "mitigacao", "fim"])
        self.assertTrue(all(e.stamp.precision == "minute" for e in d.timeline))
        self.assertEqual(len(d.actions), 3)
        a = d.actions[0]
        self.assertEqual(a.texto, "Adicionar teste de carga do pool de conexões no pipeline")
        self.assertEqual((a.dono, a.ticket, a.prioridade, a.tipo, a.prazo, a.componente),
                         ("ana.souza", "PAY-101", "P1", "prevent", "2026-09-28", "checkout-api"))
        self.assertEqual(len(d.factors), 2)
        self.assertEqual([f.stamps[0].when.strftime("%H:%M") for f in d.factors],
                         ["14:50", "15:01"])
        self.assertEqual([q.raw for q in d.quantities], ["1.240 pedidos", "18%", "3 clientes"])
        self.assertEqual([(m.minutes, m.label) for m in d.durations],
                         [(66, "duracao"), (7, "TTD"), (42, "TTM")])
        self.assertEqual(d.redactions, [])

    def test_sem_timeline(self):
        with self.assertRaises(InputError):
            self.parse({TL_TITLE: "## Notas"})

    def test_timeline_em_tabela(self):
        bloco = TL_TITLE + "\n\n- 14:50 Deploy da versão 4.2 do checkout-api concluído."
        d = self.parse({bloco: TL_TITLE + "\n\n| Horário | Evento |\n|---|---|\n| 14:50 | Deploy |"})
        self.assertEqual(d.timeline[0].text, "14:50 | Deploy")
        self.assertEqual(d.timeline[0].stamp.when, datetime(2026, 9, 14, 14, 50, tzinfo=UTC))

    def test_acao_em_lista(self):
        d = self.parse({"| Ação | Dono | Ticket | Prioridade | Tipo | Prazo | Componente |\n"
                        "|---|---|---|---|---|---|---|\n": "- Revisar alertas\n",
                        "| Adicionar teste de carga do pool de conexões no pipeline | ana.souza | PAY-101 | P1 | prevent | 2026-09-28 | checkout-api |\n": "",
                        "| Reduzir o limiar do alerta de erro para 5% | @joao | PAY-102 | P2 | detect | 2026-10-10 | checkout-api |\n": "",
                        "| Automatizar o rollback quando a taxa de erro passar de 10% | @maria | PLAT-55 | P1 | mitigate | 2026-09-28 | ingress |\n": ""})
        self.assertEqual(len(d.actions), 1)
        self.assertEqual(d.actions[0].texto, "Revisar alertas")
        self.assertEqual(d.actions[0].dono, "")

    def test_fuso_no_titulo(self):
        d = self.parse({TL_TITLE: "## Linha do tempo (UTC-3)"})
        self.assertEqual(d.timeline[0].stamp.when,
                         datetime(2026, 9, 14, 17, 50, tzinfo=UTC))

    def test_meia_noite_com_subtitulo(self):
        old = "- 16:00 [fim] Taxa de erro volta ao normal."
        d = self.parse({old: old + "\n- 23:50 Nota do fim do dia.\n\n### 2026-09-15\n\n- 00:10 Nota pós incidente."})
        a, b = d.timeline[-2:]
        self.assertEqual(a.stamp.when.date(), date(2026, 9, 14))
        self.assertEqual(b.stamp.when.date(), date(2026, 9, 15))
        whens = [e.stamp.when for e in d.timeline]
        self.assertEqual(whens, sorted(whens))
        self.assertEqual(d.unparsed, [])

    def test_bom_e_crlf(self):
        raw = (APROVADO / "postmortem.md").read_bytes()
        p = self.tmp / "crlf.md"
        p.write_bytes(b"\xef\xbb\xbf" + raw.replace(b"\n", b"\r\n"))
        x = parse_document(p, Config())
        y = parse_document(APROVADO / "postmortem.md", Config())
        self.assertEqual(x.timeline, y.timeline)
        self.assertEqual(x.tz, y.tz)
        self.assertEqual(x.actions, y.actions)
        self.assertEqual(x.incident_date, y.incident_date)
        self.assertEqual(x.severity, y.severity)

    def test_segredo_oculto(self):
        old = "- 15:05 [reconhecimento] Plantão reconheceu o alerta."
        d = self.parse({old: old + " token=abc123segredo"})
        self.assertEqual(len(d.redactions), 1)
        self.assertEqual(len(d.timeline), 6)
        self.assertNotIn("abc123segredo", "".join(t for _, t in d.lines))


if __name__ == "__main__":
    unittest.main()
