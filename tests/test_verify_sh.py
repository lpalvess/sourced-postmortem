import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.helpers import copy_case

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "verify.sh"
BASH = shutil.which("bash")


def docker_ok() -> bool:
    docker = shutil.which("docker")
    if not docker:
        return False
    try:
        return subprocess.run([docker, "info"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def image() -> str:
    text = SCRIPT.read_text(encoding="utf-8")
    m = re.search(r'IMAGE="\$\{SOURCED_POSTMORTEM_IMAGE:-([^}]+)\}"', text)
    assert m, "IMAGE não encontrada em verify.sh"
    return os.environ.get("SOURCED_POSTMORTEM_IMAGE", m.group(1))


class Base(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(t.name)
        self.doc, self.ev, self.cfg = copy_case(self.tmp / "caso")

    def run_script(self, args, path=None):
        env = dict(os.environ)
        if path is not None:
            env["PATH"] = str(path)
        return subprocess.run([BASH, str(SCRIPT), *args], capture_output=True,
                              text=True, env=env, timeout=300)


class SemDockerTest(Base):
    def setUp(self):
        super().setUp()
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        for name in ("dirname", "basename", "mkdir", "id"):
            (self.bin / name).symlink_to(shutil.which(name))

    def test_script_executavel(self):
        self.assertTrue(os.access(SCRIPT, os.X_OK))

    def test_sem_argumentos_sai_2(self):
        r = self.run_script([], self.bin)
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_so_um_posicional_sai_2(self):
        r = self.run_script([str(self.doc)], self.bin)
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_opcao_desconhecida_sai_2(self):
        r = self.run_script([str(self.doc), str(self.ev), "--foo"], self.bin)
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_documento_que_nao_e_arquivo_sai_2(self):
        r = self.run_script([str(self.ev), str(self.ev)], self.bin)
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_evidencias_que_nao_sao_pasta_sai_2(self):
        r = self.run_script([str(self.doc), str(self.doc)], self.bin)
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_config_que_nao_e_arquivo_sai_2(self):
        r = self.run_script([str(self.doc), str(self.ev), "--config", str(self.ev)], self.bin)
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_caminho_com_virgula_sai_2(self):
        ev = self.tmp / "ev,idencias"
        ev.mkdir()
        r = self.run_script([str(self.doc), str(ev)], self.bin)
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_saida_dentro_das_evidencias_sai_2(self):
        out = self.ev / "saida"
        r = self.run_script([str(self.doc), str(self.ev), "--out", str(out)], self.bin)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("evidências", r.stderr)

    def test_saida_dentro_das_evidencias_via_relativo_sai_2(self):
        r = subprocess.run(
            [BASH, str(SCRIPT), str(self.doc), str(self.ev), "--out", "../evidencias/x/../saida"],
            capture_output=True, text=True, cwd=self.ev, timeout=60,
            env={**os.environ, "PATH": str(self.bin)})
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_argumentos_validos_sem_docker_sai_4(self):
        out = self.tmp / "saida"
        r = self.run_script([str(self.doc), str(self.ev), "--config", str(self.cfg),
                             "--out", str(out)], self.bin)
        self.assertEqual(r.returncode, 4, r.stderr)
        self.assertIn("Docker", r.stderr)


@unittest.skipUnless(docker_ok(), "Docker indisponível")
class ComDockerTest(Base):
    def test_aprovado(self):
        out = self.tmp / "saida"
        r = self.run_script([str(self.doc), str(self.ev), "--config", str(self.cfg),
                             "--out", str(out)])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for name in ("relatorio.json", "relatorio.md", "diagrama.excalidraw"):
            self.assertTrue((out / name).is_file(), name)
        self.assertIn(f"Relatório: {out}/relatorio.md", r.stdout)
        self.assertIn(f"Diagrama: {out}/diagrama.excalidraw", r.stdout)

    def test_e2_reprova(self):
        doc, ev, cfg = copy_case(self.tmp / "e2", {"3 clientes": "5 clientes"})
        out = self.tmp / "saida-e2"
        r = self.run_script([str(doc), str(ev), "--config", str(cfg), "--out", str(out)])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("Relatório:", r.stdout)

    def test_contêiner_sem_rede(self):
        r = subprocess.run(
            ["docker", "run", "--rm", "--network", "none", image(), "python", "-c",
             "import urllib.request; urllib.request.urlopen('http://1.1.1.1', timeout=3)"],
            capture_output=True, text=True, timeout=120)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
