import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import dados  # noqa: E402


class TestDados(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.dict(os.environ, {"RAIZ_MESTRA_DADOS": self.tmp.name})
        p.start()
        self.addCleanup(p.stop)

    def test_slug_ruim(self):
        for s in ("../x", "Maiuscula", "a" * 41, "", "a/b", "a b"):
            with self.assertRaises(dados.ErroDados, msg=s):
                dados.validar_slug(s)

    def test_slug_bom(self):
        self.assertEqual(dados.validar_slug("a" * 40), "a" * 40)
        self.assertEqual(dados.validar_slug("meu-caso-1"), "meu-caso-1")

    def test_cria_pasta_do_dossie(self):
        p = dados.pasta_dossie("caso", criar=True)
        self.assertTrue(p.is_dir())
        self.assertEqual(p.parent.parent, Path(os.path.realpath(self.tmp.name)))

    def test_recusa_dotdot(self):
        with self.assertRaises(dados.ErroDados):
            dados.dentro_da_pasta(Path(self.tmp.name) / "dossies" / ".." / ".." / "fora")

    def test_symlink_que_sai(self):
        pasta = dados.pasta_dossie("caso", criar=True)
        with tempfile.TemporaryDirectory() as fora:
            (pasta / "ln").symlink_to(fora)
            with self.assertRaises(dados.ErroDados):
                dados.arquivo_no_dossie("caso", "ln/segredo.txt")

    def test_pastas_nascem_com_modo_700(self):
        novo = Path(self.tmp.name) / "novo"
        with mock.patch.dict(os.environ, {"RAIZ_MESTRA_DADOS": str(novo)}):
            base = dados.pasta_dados()
            p = dados.pasta_dossie("caso", criar=True)
            for d in (base, base / "dossies", p, base / "cache_publico"):
                self.assertEqual(stat.S_IMODE(d.stat().st_mode), 0o700, d.name)

    def test_exibir_e_relativo_a_pasta_de_dados(self):
        p = dados.pasta_dossie("caso", criar=True)
        self.assertEqual(dados.exibir(p / "estado.json"), "dossies/caso/estado.json")
        with tempfile.TemporaryDirectory() as fora:
            mostrado = dados.exibir(Path(fora) / "entrega.md")
            self.assertNotIn(fora, mostrado)
            self.assertNotIn(self.tmp.name, mostrado)

    def test_symlink_do_proprio_dossie_para_fora(self):
        with tempfile.TemporaryDirectory() as fora:
            (Path(dados.pasta_dados()) / "dossies").mkdir()
            (Path(dados.pasta_dados()) / "dossies" / "preso").symlink_to(fora)
            with self.assertRaises(dados.ErroDados):
                dados.pasta_dossie("preso", criar=True)


if __name__ == "__main__":
    unittest.main()
