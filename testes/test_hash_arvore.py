import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import hash_arvore  # noqa: E402


def montar(raiz):
    raiz = Path(raiz)
    (raiz / "sub").mkdir()
    (raiz / "a.txt").write_bytes(b"aaa")
    (raiz / "sub" / "b.txt").write_bytes(b"bbb")


class TestHash(unittest.TestCase):
    def test_igual_para_arvore_igual(self):
        with tempfile.TemporaryDirectory() as x, tempfile.TemporaryDirectory() as y:
            montar(x)
            montar(y)
            self.assertEqual(hash_arvore.hash_arvore(x), hash_arvore.hash_arvore(y))

    def test_muda_com_um_byte(self):
        with tempfile.TemporaryDirectory() as x:
            montar(x)
            antes = hash_arvore.hash_arvore(x)
            (Path(x) / "a.txt").write_bytes(b"aab")
            self.assertNotEqual(antes, hash_arvore.hash_arvore(x))

    def test_muda_com_renomeio(self):
        with tempfile.TemporaryDirectory() as x:
            montar(x)
            antes = hash_arvore.hash_arvore(x)
            (Path(x) / "a.txt").rename(Path(x) / "c.txt")
            self.assertNotEqual(antes, hash_arvore.hash_arvore(x))

    def test_ignora_git_index_objects_pycache_seiva(self):
        # ruído legítimo de git status/commit e de Python não pode dar falso alarme
        with tempfile.TemporaryDirectory() as x:
            montar(x)
            (Path(x) / ".git").mkdir()  # repositório real já tem .git antes da medição
            antes = hash_arvore.hash_arvore(x)
            (Path(x) / ".git" / "objects" / "ab").mkdir(parents=True)
            (Path(x) / ".git" / "objects" / "ab" / "f").write_bytes(b"ruido")
            (Path(x) / ".git" / "index").write_bytes(b"ruido")
            (Path(x) / "__pycache__").mkdir()
            (Path(x) / "__pycache__" / "m.pyc").write_bytes(b"ruido")
            (Path(x) / ".seiva").mkdir()
            (Path(x) / ".seiva" / "f").write_bytes(b"ruido")
            self.assertEqual(antes, hash_arvore.hash_arvore(x))

    def test_muda_com_gravacao_em_git_hooks_e_config(self):
        with tempfile.TemporaryDirectory() as x:
            montar(x)
            (Path(x) / ".git" / "hooks").mkdir(parents=True)
            (Path(x) / ".git" / "config").write_bytes(b"[core]")
            antes = hash_arvore.hash_arvore(x)
            (Path(x) / ".git" / "hooks" / "pre-commit").write_bytes(b"#!/bin/sh\n")
            self.assertNotEqual(antes, hash_arvore.hash_arvore(x))
            antes = hash_arvore.hash_arvore(x)
            (Path(x) / ".git" / "config").write_bytes(b"[core]\n\tx = 1")
            self.assertNotEqual(antes, hash_arvore.hash_arvore(x))

    def test_muda_com_pasta_vazia(self):
        with tempfile.TemporaryDirectory() as x:
            montar(x)
            antes = hash_arvore.hash_arvore(x)
            (Path(x) / "vazia").mkdir()
            self.assertNotEqual(antes, hash_arvore.hash_arvore(x))

    @unittest.skipIf(os.name == "nt", "link simbólico e modo POSIX")
    def test_muda_com_link_simbolico_de_arquivo_e_de_pasta(self):
        with tempfile.TemporaryDirectory() as x:
            montar(x)
            antes = hash_arvore.hash_arvore(x)
            os.symlink("a.txt", Path(x) / "ln_arq")
            self.assertNotEqual(antes, hash_arvore.hash_arvore(x))
            antes = hash_arvore.hash_arvore(x)
            os.symlink("sub", Path(x) / "ln_pasta", target_is_directory=True)
            self.assertNotEqual(antes, hash_arvore.hash_arvore(x))

    @unittest.skipIf(os.name == "nt", "modo POSIX")
    def test_muda_com_mudanca_de_modo(self):
        with tempfile.TemporaryDirectory() as x:
            montar(x)
            antes = hash_arvore.hash_arvore(x)
            os.chmod(Path(x) / "a.txt", 0o755)
            self.assertNotEqual(antes, hash_arvore.hash_arvore(x))


if __name__ == "__main__":
    unittest.main()
