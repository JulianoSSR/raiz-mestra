"""Tamanho E3 (dinheiro alto): recomendacao exige coleta real registrada em Fatos."""
import contextlib
import io
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import lint_entrega  # noqa: E402
import rotular  # noqa: E402

FIX = RAIZ / "testes" / "fixtures"


def roda(modulo, caminho):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = modulo.main([str(caminho)])
    return rc, buf.getvalue()


class TestDinheiroAlto(unittest.TestCase):
    def test_e3_com_recomendacao_e_sem_coleta_reprova(self):
        f = FIX / "ruins" / "e3-recomenda-sem-coleta.md"
        self.assertEqual(roda(rotular, f)[0], 0)  # a forma esta certa
        rc, out = roda(lint_entrega, f)
        self.assertEqual(rc, 1, out)
        self.assertIn("(f) tamanho E3", out)
        self.assertIn("e3-recomenda-sem-coleta.md:", out)

    def test_e3_com_coleta_real_e_recomendacao_passa(self):
        f = FIX / "boas" / "e3-com-coleta.md"
        self.assertEqual(roda(rotular, f)[0], 0)
        rc, out = roda(lint_entrega, f)
        self.assertEqual(rc, 0, out)

    def test_e3_so_com_perguntas_e_teste_barato_passa(self):
        f = FIX / "boas" / "e3-so-perguntas.md"
        self.assertEqual(roda(rotular, f)[0], 0)
        rc, out = roda(lint_entrega, f)
        self.assertEqual(rc, 0, out)

    def test_coleta_so_conta_em_linha_usuario_de_fatos(self):
        # "coleta:" numa linha [hipotese] nao vale como coleta real
        t = (FIX / "boas" / "e3-com-coleta.md").read_text(encoding="utf-8")
        t = t.replace("| [usuário] | coleta: reg-007 de 2026-03-05 |",
                      "| [hipótese] | como medir: coleta: reg-007 de 2026-03-05 |")
        self.assertIn("[hipótese] | como medir: coleta", t)
        msgs = lint_entrega.lint(t, "e3.md")
        self.assertTrue(any("(f)" in m for m in msgs), msgs)

    def test_mesmo_texto_em_e2_nao_aciona_a_regra(self):
        t = (FIX / "ruins" / "e3-recomenda-sem-coleta.md").read_text(encoding="utf-8")
        msgs = lint_entrega.lint(t.replace("tamanho: E3", "tamanho: E2"), "e2.md")
        self.assertFalse(any("(f)" in m for m in msgs), msgs)


if __name__ == "__main__":
    unittest.main()
