"""Testes de scripts/rotular.py (confere forma, nao verdade)."""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import rotular  # noqa: E402

FIX = RAIZ / "testes" / "fixtures"

# fixture ruim -> trecho que a mensagem precisa trazer
RUINS = {
    "numero-na-prosa-fora-da-tabela": "R$ 99,90",
    "fonte-vazia": "Fonte vazia",
    "publico-sem-url": "sem URL",
    "hipotese-sem-como-medir": "como medir",
    "usuario-sem-data": "[usuário] sem data",
    "simulacao-sem-painel": "id de painel",
    "rotulo-invalido": "Rótulo inválido",
    "secao-ausente": "Pré-mortem",
    "cabecalho-sem-chave": "eleitoral:",
    "titulo-de-secao-errado": "Limites desta análise",
    "data-impossivel-na-fonte": "sem data",
}


def roda(args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = rotular.main(args)
    return rc, buf.getvalue()


class TestRotular(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._old = os.environ.get("RAIZ_MESTRA_DADOS")
        os.environ["RAIZ_MESTRA_DADOS"] = self.tmp.name
        self.addCleanup(self._restaura)

    def _restaura(self):
        if self._old is None:
            os.environ.pop("RAIZ_MESTRA_DADOS", None)
        else:
            os.environ["RAIZ_MESTRA_DADOS"] = self._old

    def test_boas_passam(self):
        for nome in ("entrega-exemplo", "eleitoral-ok", "e3-com-coleta", "e3-so-perguntas"):
            with self.subTest(nome):
                rc, out = roda([str(FIX / "boas" / f"{nome}.md")])
                self.assertEqual(rc, 0, out)

    def test_ruins_reprovam_pelo_motivo(self):
        self.assertGreaterEqual(len(RUINS), 8)
        for nome, trecho in RUINS.items():
            with self.subTest(nome):
                rc, out = roda([str(FIX / "ruins" / f"{nome}.md")])
                self.assertEqual(rc, 1, out)
                self.assertIn(trecho, out)
                self.assertIn(f"{nome}.md:", out)  # arquivo:linha

    def test_defeito_unico_na_fixture(self):
        # numero na prosa: so a linha do numero, nenhum outro defeito de forma
        _, out = roda([str(FIX / "ruins" / "numero-na-prosa-fora-da-tabela.md")])
        self.assertEqual(len([l for l in out.splitlines() if ".md:" in l]), 1, out)

    def test_uso_errado(self):
        self.assertEqual(roda([])[0], 2)
        self.assertEqual(roda(["nao-existe.md"])[0], 2)
        rc, out = roda(["--help"])
        self.assertEqual(rc, 0)
        self.assertIn("NÃO confere verdade", out)

    def test_numero_com_ponto_e_virgula_casa_com_tabela(self):
        base = (FIX / "boas" / "entrega-exemplo.md").read_text(encoding="utf-8")
        p = Path(self.tmp.name) / "e.md"
        p.write_text(base.replace("de R$ 12,50 se sustenta", "de R$ 2250,00 se sustenta"), encoding="utf-8")
        self.assertEqual(roda([str(p)])[0], 0)  # 2250 == R$ 2.250

    def test_data_ano_e_lista_nao_contam(self):
        base = (FIX / "boas" / "entrega-exemplo.md").read_text(encoding="utf-8")
        p = Path(self.tmp.name) / "e.md"
        p.write_text(base.replace("## Próximo teste real\n\n", "## Próximo teste real\n\n1. Em 2026, no dia 12/03/2026, começar.\n2) Depois seguir.\n\n"), encoding="utf-8")
        rc, out = roda([str(p)])
        self.assertEqual(rc, 0, out)

    def test_numero_novo_em_tabela_de_outra_secao_com_coluna_hash(self):
        base = (FIX / "boas" / "entrega-exemplo.md").read_text(encoding="utf-8")
        p = Path(self.tmp.name) / "e.md"
        p.write_text(base.replace("## Pré-mortem\n\n", "## Pré-mortem\n\n| # | Causa |\n|---|---|\n| 7 | custo de R$ 777 |\n\n"), encoding="utf-8")
        rc, out = roda([str(p)])
        self.assertEqual(rc, 1)
        self.assertIn("777", out)
        self.assertNotIn("'7'", out)

    def test_texto_antes_da_primeira_secao_reprova(self):
        # A-1: Resumo com numero e adocao, antes do primeiro ##, nao pode passar
        rc, out = roda([str(FIX / "ruins" / "texto-antes-da-secao.md")])
        self.assertEqual(rc, 1, out)
        self.assertIn("texto antes da primeira seção", out)
        self.assertIn("texto-antes-da-secao.md:", out)

    def test_secao_fora_do_formato_reprova(self):
        # A-4: secao extra (## Recomendacao) nao pode passar
        rc, out = roda([str(FIX / "ruins" / "secao-extra.md")])
        self.assertEqual(rc, 1, out)
        self.assertIn("'## Recomendação' fora das 8 seções", out)

    def test_funcoes_de_fonte(self):
        self.assertIsNone(rotular.fonte_ok("[público]", "https://a.org/x em 2026-01-02"))
        self.assertIsNotNone(rotular.fonte_ok("[público]", "https://a.org/x"))
        self.assertIsNone(rotular.fonte_ok("[hipótese]", "como medir: contar pedidos"))
        self.assertIsNotNone(rotular.fonte_ok("[hipótese]", "como medir:"))
        self.assertIsNotNone(rotular.fonte_ok("[usuário]", "—"))


if __name__ == "__main__":
    unittest.main()
