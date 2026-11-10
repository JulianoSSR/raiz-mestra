import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import ambiente  # noqa: E402

PADRAO = re.compile(r"os\.environ|\benviron\b|getenv|printenv|import\s+os\s+as\b")


class TestAmbiente(unittest.TestCase):
    def test_fora_da_lista_levanta(self):
        with self.assertRaises(ambiente.VariavelNaoPermitida):
            ambiente.ler("PATH")
        with self.assertRaises(ambiente.VariavelNaoPermitida):
            ambiente.tem("SEGREDO")

    def test_ler_e_tem(self):
        with mock.patch.dict(os.environ, {"RAIZ_MESTRA_CHAVE_API": "x"}):
            self.assertEqual(ambiente.ler("RAIZ_MESTRA_CHAVE_API"), "x")
            self.assertIs(ambiente.tem("RAIZ_MESTRA_CHAVE_API"), True)
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIs(ambiente.tem("RAIZ_MESTRA_CHAVE_API"), False)
            self.assertIsNone(ambiente.ler("RAIZ_MESTRA_CHAVE_API"))

    def test_so_ambiente_le_ambiente(self):
        achados = []
        for pasta in ("scripts", "hooks"):
            for arq in (RAIZ / pasta).rglob("*"):
                if arq.suffix not in (".py", ".sh") or arq.name == "ambiente.py":
                    continue
                for n, l in enumerate(arq.read_text(encoding="utf-8").splitlines(), 1):
                    if PADRAO.search(l):
                        achados.append("%s:%d" % (arq, n))
        self.assertEqual(achados, [])

    def test_padrao_pega_variantes_de_leitura(self):
        for linha in ("x = os.environ.get('A')", "from os import environ", "import os as o",
                      "o.getenv('A')", "print(environ['A'])"):
            self.assertIsNotNone(PADRAO.search(linha), linha)

    def test_ambiente_nao_imprime(self):
        txt = (RAIZ / "scripts" / "ambiente.py").read_text(encoding="utf-8")
        self.assertNotIn("print(", txt)


if __name__ == "__main__":
    unittest.main()
