"""Modo eleitoral: um teste por item proibido (referencias/eleitoral.md, secao 1).

Cada teste prova exit 1 pelo motivo certo (a mensagem precisa trazer o trecho
esperado) e ha um teste positivo. Heuristica por padroes: ver o topo de
scripts/lint_entrega.py e de scripts/ficha_lint.py para o que NAO e pego.
"""
import contextlib
import io
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import ficha_lint  # noqa: E402
import lint_entrega  # noqa: E402
import rotular  # noqa: E402

FIX = RAIZ / "testes" / "fixtures"


def roda(modulo, args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = modulo.main(args)
    return rc, buf.getvalue()


def lint(nome, pasta="ruins"):
    return roda(lint_entrega, [str(FIX / pasta / nome)])


def ficha(nome, pasta="ruins"):
    return roda(ficha_lint, [str(FIX / pasta / nome), "--eleitoral"])


class TestEleitoral(unittest.TestCase):
    def test_1_recomendar_candidatura_reprova(self):
        rc, out = lint("eleitoral-recomenda-candidato.md")
        self.assertEqual(rc, 1, out)
        self.assertIn("(e) recomendação de candidatura", out)

    def test_2_percentual_de_voto_reprova(self):
        rc, out = lint("eleitoral-percentual-de-voto.md")
        self.assertEqual(rc, 1, out)
        self.assertIn("(e) percentual/contagem de voto", out)

    def test_3a_ficha_de_eleitor_real_reprova(self):
        rc, out = ficha("ficha-eleitor-real.md")
        self.assertEqual(rc, 1, out)
        self.assertIn("--eleitoral: ficha de eleitor com origem real", out)

    def test_3b_ficha_de_eleitor_com_nome_reprova(self):
        rc, out = ficha("eleitoral-ficha-eleitor-nome.md")
        self.assertEqual(rc, 1, out)
        self.assertIn("tratamento com nome próprio", out)

    def test_3c_ficha_com_cargo_e_cidade_reprova(self):
        rc, out = ficha("ficha-cargo-cidade.md")
        self.assertEqual(rc, 1, out)
        self.assertIn("--eleitoral: cargo + cidade", out)

    def test_4_segmentacao_por_opiniao_politica_reprova(self):
        rc, out = lint("eleitoral-segmentacao-politica.md")
        self.assertEqual(rc, 1, out)
        self.assertIn("(g) segmentação por opinião política", out)

    def test_5_texto_de_campanha_sem_rotulo_de_ia_reprova(self):
        rc, out = lint("eleitoral-sem-rotulo-ia.md")
        self.assertEqual(rc, 1, out)
        self.assertIn("(e) texto de campanha sem a marca", out)

    def test_ruins_eleitorais_tem_forma_correta(self):
        # o defeito de cada fixture e so o proibido, nao a forma
        for nome in ("eleitoral-recomenda-candidato", "eleitoral-percentual-de-voto",
                     "eleitoral-segmentacao-politica", "eleitoral-sem-rotulo-ia"):
            with self.subTest(nome):
                texto = (FIX / "ruins" / f"{nome}.md").read_text(encoding="utf-8")
                self.assertEqual(rotular.valida(texto, nome), [])

    def test_positivo_entrega_eleitoral_correta_passa(self):
        rc, out = lint("eleitoral-ok.md", "boas")
        self.assertEqual(rc, 0, out)
        rc, out = roda(rotular, [str(FIX / "boas" / "eleitoral-ok.md")])
        self.assertEqual(rc, 0, out)

    def test_positivo_ficha_arquetipo_passa_no_modo_eleitoral(self):
        rc, out = ficha("ficha-arquetipo.md", "boas")
        self.assertEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main()
