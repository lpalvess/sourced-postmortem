import re
import unittest
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from verifier import timestamps as ts
from verifier.timestamps import UTC


def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


class FindStampsTest(unittest.TestCase):
    def one(self, text, **kw):
        hits = ts.find_stamps(text, **kw)
        self.assertEqual(len(hits), 1, hits)
        return hits[0]

    def test_iso_z(self):
        h = self.one("2026-09-14T14:50:12Z")
        self.assertEqual(h.stamp.when, utc(2026, 9, 14, 14, 50, 12))
        self.assertEqual(h.stamp.precision, "second")
        self.assertFalse(h.assumed_tz)

    def test_iso_offset(self):
        h = self.one("2026-09-14T11:54:03-03:00")
        self.assertEqual(h.stamp.when, utc(2026, 9, 14, 14, 54, 3))

    def test_iso_space_utc_comma(self):
        h = self.one("2026-09-14 15:05:22 UTC,Ack")
        self.assertEqual(h.stamp.when, utc(2026, 9, 14, 15, 5, 22))

    def test_nginx(self):
        h = self.one("[14/Sep/2026:16:00:41 +0000]")
        self.assertEqual(h.stamp.when, utc(2026, 9, 14, 16, 0, 41))

    def test_syslog(self):
        h = self.one("Sep 14 15:01:30 host", default_date=date(2026, 9, 14))
        self.assertEqual(h.stamp.when, utc(2026, 9, 14, 15, 1, 30))
        self.assertTrue(h.assumed_tz)
        h = self.one("Sep 14 15:01:30 host")
        self.assertIsNone(h.stamp)
        self.assertEqual(h.reason, "horário sem ano")

    def test_epoch(self):
        exp = datetime(2026, 9, 14, 15, 0, 0, tzinfo=timezone.utc)
        s = int(exp.timestamp())
        h = self.one('{"timestamp": %d}' % s)
        self.assertEqual(h.stamp.when, exp)
        self.assertEqual(h.stamp.precision, "second")
        h = self.one('"startsAt": "%d"' % (s * 1000))
        self.assertEqual(h.stamp.when, exp)

    def test_bare_time(self):
        tz = timezone(timedelta(hours=-3))
        h = self.one("14:54", default_date=date(2026, 9, 14), default_tz=tz)
        self.assertEqual(h.stamp.when, utc(2026, 9, 14, 17, 54))
        self.assertEqual(h.stamp.precision, "minute")
        self.assertTrue(h.assumed_tz)
        h = self.one("14:54")
        self.assertIsNone(h.stamp)
        self.assertEqual(h.reason, "horário sem data")

    def test_no_duplicate_bare_time(self):
        self.one("2026-09-14T14:50:12Z", default_date=date(2026, 9, 14))

    def test_slash_dates(self):
        h = self.one("03/04/2026 10:00")
        self.assertIsNone(h.stamp)
        self.assertTrue(h.ambiguous)
        self.assertEqual(h.reason, "data ambígua")
        h = self.one("03/04/2026 10:00", date_order="DMY")
        self.assertEqual(h.stamp.when, utc(2026, 4, 3, 10, 0))
        h = self.one("25/09/2026 10:00")
        self.assertEqual(h.stamp.when, utc(2026, 9, 25, 10, 0))

    def test_invalid_time(self):
        self.assertEqual(ts.find_stamps("25:99"), [])

    def test_sorted(self):
        hits = ts.find_stamps("14:00 e 2026-09-14T10:00Z", default_date=date(2026, 9, 14))
        self.assertEqual([h.start for h in hits], sorted(h.start for h in hits))


class DateTest(unittest.TestCase):
    def test_find_date(self):
        self.assertEqual(ts.find_date("10/25/2026"), date(2026, 10, 25))
        self.assertIsNone(ts.find_date("03/04/2026"))
        self.assertEqual(ts.find_date("Prazo 2026-10-10"), date(2026, 10, 10))

    def test_mask(self):
        out = ts.mask_temporal("às 14:54 em 2026-09-14 foram 3")
        self.assertEqual(re.findall(r"\d+", out), ["3"])


class TzDeclTest(unittest.TestCase):
    def test_decl(self):
        self.assertEqual(ts.parse_tz_decl("Linha do tempo (todos os horários em UTC)"), UTC)
        self.assertEqual(ts.parse_tz_decl("Timeline (UTC-3)").utcoffset(None), timedelta(hours=-3))
        self.assertIsInstance(ts.parse_tz_decl("All times are in America/Sao_Paulo"), ZoneInfo)
        self.assertIsNone(ts.parse_tz_decl("horários de pico"))
        self.assertIsNone(ts.parse_tz_decl("(e/ou)"))

    def test_name(self):
        self.assertEqual(ts.tz_name(UTC), "UTC")
        self.assertEqual(ts.tz_name(None), "não declarado (lido como UTC)")
        self.assertEqual(ts.tz_name(ZoneInfo("America/Sao_Paulo")), "America/Sao_Paulo")


if __name__ == "__main__":
    unittest.main()
