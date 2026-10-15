import unittest

from verifier.model import Redaction
from verifier.redact import redact


def kinds(found):
    return [r.kind for r in found]


class PositiveTests(unittest.TestCase):
    def check(self, text, kind, secret):
        out, found = redact(text, "f.md")
        self.assertEqual(kinds(found), [kind])
        self.assertNotIn(secret, out)
        self.assertIn(f"[OCULTO:{kind}]", out)
        self.assertEqual(found[0], Redaction("f.md", 1, kind))

    def test_private_key(self):
        body = "Q" * 20
        text = ("-----BEGIN " + "RSA PRIVATE KEY-----\n" + body + "\n"
                + "-----END " + "RSA PRIVATE KEY-----")
        self.check(text, "private-key", body)

    def test_aws_secret(self):
        secret = "Z" * 40
        self.check(f"aws_secret_access_key = {secret}", "aws-secret", secret)

    def test_aws_key(self):
        secret = "AKIA" + "Q" * 16
        self.check(f"chave {secret} vazou", "aws-key", secret)

    def test_aws_key_asia(self):
        secret = "ASIA" + "Q" * 16
        self.check(f"chave {secret}", "aws-key", secret)

    def test_github_token(self):
        secret = "ghp_" + "a" * 36
        self.check(f"usou {secret} no CI", "github-token", secret)

    def test_github_pat(self):
        secret = "github_pat_" + "a" * 22
        self.check(f"usou {secret}", "github-token", secret)

    def test_slack_token(self):
        secret = "xoxb-" + "1" * 12
        self.check(f"slack {secret}", "slack-token", secret)

    def test_jwt(self):
        secret = "eyJ" + "a" * 8 + "." + "b" * 8 + "." + "c" * 8
        self.check(f"sessao {secret}", "jwt", secret)

    def test_bearer(self):
        secret = "z" * 20
        self.check(f"Authorization: Bearer {secret}", "bearer", secret)

    def test_url_credencial(self):
        out, found = redact("postgres://app:s3nh4@db:5432/x", "f.md")
        self.assertEqual(kinds(found), ["url-credencial"])
        self.assertNotIn("s3nh4", out)
        self.assertIn("@db", out)
        self.assertIn("[OCULTO:url-credencial]", out)

    def test_senha_chave(self):
        self.check("token=abc123segredo", "senha-chave", "abc123segredo")

    def test_senha_chave_json(self):
        out, found = redact('{"api_key": "abc123"}', "f.md")
        self.assertEqual(kinds(found), ["senha-chave"])
        self.assertNotIn("abc123", out)

    def test_senha_pt(self):
        self.check("senha: hunter22", "senha-chave", "hunter22")


class QuotedAndTruncatedTests(unittest.TestCase):
    def test_quoted_values_fully_masked(self):
        for texto, cauda in [
            ('password="a b c"', "b c"),
            ("senha: \"tail9 segredo longo\"", "segredo"),
            ("secret='x y'", "y"),
            ('{"token": "um dois tres"}', "tres"),
            ('password="abc def', "def"),
        ]:
            with self.subTest(texto=texto):
                out, found = redact(texto, "f.md")
                self.assertEqual(kinds(found), ["senha-chave"])
                self.assertNotIn(cauda, out)
                self.assertIn("[OCULTO:senha-chave]", out)

    def test_quote_characters_kept(self):
        out, _ = redact('password="a b c"', "f.md")
        self.assertEqual(out, 'password="[OCULTO:senha-chave]"')
        out, _ = redact("secret='x y' resto", "f.md")
        self.assertEqual(out, "secret='[OCULTO:senha-chave]' resto")

    def test_quoted_mask_idempotent(self):
        once, _ = redact('password="a b c"', "f.md")
        twice, found = redact(once, "f.md")
        self.assertEqual(once, twice)
        self.assertEqual(found, [])

    def test_empty_quotes_not_a_secret(self):
        out, found = redact('password=""', "f.md")
        self.assertEqual(found, [])

    def test_mask_prefix_does_not_hide_payload(self):
        out, found = redact("password=[OCULTO:x]REAL", "f.md")
        self.assertNotIn("REAL", out)
        self.assertEqual(kinds(found), ["senha-chave"])

    def test_truncated_private_key(self):
        cab = "-----BEGIN " + "RSA PRIVATE KEY-----"
        text = f"antes\n{cab}\nAAAA\nBBBB\n\ndepois"
        out, found = redact(text, "f.md")
        self.assertNotIn("AAAA", out)
        self.assertNotIn("BBBB", out)
        self.assertIn("depois", out)
        self.assertEqual(out.count("\n"), text.count("\n"))
        self.assertEqual([(r.line, r.kind) for r in found], [(2, "private-key")])

    def test_truncated_private_key_to_end(self):
        cab = "-----BEGIN " + "PRIVATE KEY-----"
        text = f"{cab}\nAAAA\nBBBB"
        out, found = redact(text, "f.md")
        self.assertNotIn("AAAA", out)
        self.assertNotIn("BBBB", out)
        self.assertEqual(out.count("\n"), 2)

    def test_full_block_still_wins(self):
        cab = "-----BEGIN " + "PRIVATE KEY-----"
        fim = "-----END " + "PRIVATE KEY-----"
        text = f"{cab}\nAAAA\n\nBBBB\n{fim}\ndepois"
        out, found = redact(text, "f.md")
        self.assertNotIn("BBBB", out)
        self.assertIn("depois", out)
        self.assertEqual(len(found), 1)


class NegativeTests(unittest.TestCase):
    def test_not_secrets(self):
        for text in [
            "AKIA123",
            "ghp_curto",
            "xoxb-1",
            "eyJabc",
            "Bearer x",
            "https://host:8080/p",
            "-----BEGIN PUBLIC KEY-----",
            "token_count: 5",
            "password reset flow",
            "max_tokens=100",
        ]:
            with self.subTest(text=text):
                out, found = redact(text, "f.md")
                self.assertEqual(found, [])
                self.assertEqual(out, text)


class BehaviorTests(unittest.TestCase):
    def test_multiline_key_preserves_lines(self):
        text = (
            "linha 1\n"
            "-----BEGIN " + "PRIVATE KEY-----\nAAAA\nBBBB\n"
            "-----END " + "PRIVATE KEY-----\n"
            "senha: x1\n"
        )
        out, found = redact(text, "f.md")
        self.assertEqual(
            [(r.line, r.kind) for r in found],
            [(2, "private-key"), (6, "senha-chave")],
        )
        self.assertEqual(out.count("\n"), text.count("\n"))
        self.assertNotIn("AAAA", out)
        self.assertNotIn("x1", out)

    def test_token_equals_github_single_finding(self):
        secret = "ghp_" + "a" * 36
        out, found = redact(f"token={secret}", "f.md")
        self.assertEqual(kinds(found), ["github-token"])
        self.assertNotIn(secret, out)

    def test_already_masked_not_counted(self):
        text = "senha: [OCULTO:senha-chave]"
        out, found = redact(text, "f.md")
        self.assertEqual(found, [])
        self.assertEqual(out, text)

    def test_idempotent(self):
        once, _ = redact("token=abc123segredo", "f.md")
        twice, found = redact(once, "f.md")
        self.assertEqual(once, twice)
        self.assertEqual(found, [])

    def test_sorted_by_line_then_kind(self):
        aws = "AKIA" + "Q" * 16
        text = f"senha: x1 {aws}\nsenha: y2"
        _, found = redact(text, "f.md")
        self.assertEqual(
            [(r.line, r.kind) for r in found],
            [(1, "aws-key"), (1, "senha-chave"), (2, "senha-chave")],
        )


if __name__ == "__main__":
    unittest.main()
