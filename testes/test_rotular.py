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


    # ---- G6: A-1, V-2, A-3, A-5, A-8 ------------------------------------
    def _base(self):
        return (FIX / "boas" / "entrega-exemplo.md").read_text(encoding="utf-8")

    def _roda_texto(self, texto):
        p = Path(self.tmp.name) / "e.md"
        p.write_text(texto, encoding="utf-8")
        return roda([str(p)])

    def _troca(self, a, b):
        base = self._base()
        self.assertEqual(base.count(a), 1, a)
        return base.replace(a, b)

    def test_linha_solta_depois_da_tabela_de_fatos_e_conferida(self):
        # A-1: linha de tabela depois de linha em branco tambem tem rotulo e fonte conferidos
        rc, out = roda([str(FIX / "ruins" / "fatos-linha-solta.md")])
        self.assertEqual(rc, 1, out)
        self.assertIn("Rótulo inválido 'sem fonte'", out)
        self.assertIn("Rótulo inválido '[inventado]'", out)

    def test_segunda_tabela_em_fatos_e_conferida(self):
        # A-1: segunda tabela sob '###' com rotulo inventado
        rc, out = roda([str(FIX / "ruins" / "fatos-segunda-tabela.md")])
        self.assertEqual(rc, 1, out)
        self.assertIn("Rótulo inválido '[achismo]'", out)
        self.assertIn("fora da tabela em '## Fatos'", out)  # a linha '###'

    def test_item_de_lista_em_fatos_reprova(self):
        # A-1: linha nao vazia fora de tabela dentro de Fatos
        rc, out = roda([str(FIX / "ruins" / "fatos-item-de-lista.md")])
        self.assertEqual(rc, 1, out)
        self.assertIn("fora da tabela em '## Fatos'", out)
        self.assertIn("fatos-item-de-lista.md:16:", out)

    def test_linha_solta_em_numeros_reprova(self):
        # A-1: o mesmo vale para Numeros
        rc, out = self._roda_texto(self._troca("\n## Conceitos", "Os números acima são firmes.\n\n## Conceitos"))
        self.assertEqual(rc, 1, out)
        self.assertIn("fora da tabela em '## Números'", out)

    def test_segundo_titulo_com_numero_reprova(self):
        # V-2: linha '# ...' a mais antes da primeira secao nao pula a conferencia
        rc, out = roda([str(FIX / "ruins" / "titulo-com-adocao.md")])
        self.assertEqual(rc, 1, out)
        self.assertIn("número '80%' no cabeçalho", out)
        self.assertIn("mais de uma linha de título", out)

    def test_titulo_e_empreitada_com_numero_reprovam(self):
        # A-3: titulo e valor de 'empreitada:' passam pela conferencia de numero
        for nome in ("titulo-unico-com-adocao", "cabecalho-com-adocao"):
            with self.subTest(nome):
                rc, out = roda([str(FIX / "ruins" / f"{nome}.md")])
                self.assertEqual(rc, 1, out)
                self.assertIn("número '70%' no cabeçalho", out)

    def test_data_do_cabecalho_tem_de_ser_data_valida(self):
        # A-3: 'data:' so aceita AAAA-MM-DD valida
        rc, out = roda([str(FIX / "ruins" / "data-do-cabecalho-invalida.md")])
        self.assertEqual(rc, 1, out)
        self.assertIn("deve ser uma data AAAA-MM-DD", out)
        self.assertIn("90.000", out)
        for ruim in ("2026-02-30", "10/03/2026", "2026-03-10 e mais texto"):
            with self.subTest(ruim):
                rc, out = self._roda_texto(self._troca("data: 2026-03-10\n", f"data: {ruim}\n"))
                self.assertEqual(rc, 1, out)
                self.assertIn("deve ser uma data AAAA-MM-DD", out)

    def test_chave_repetida_no_cabecalho_tambem_e_conferida(self):
        # A-3: a primeira 'empreitada:' nao pode esconder numero atras da segunda
        rc, out = self._roda_texto("empreitada: lucro de R$ 777 garantido\n" + self._base())
        self.assertEqual(rc, 1, out)
        self.assertIn("777", out)

    def test_multiplicador_depois_do_numero_conta(self):
        # A-5: 'R$ 2 milhoes' nao casa com o 2 (semanas) da tabela
        rc, out = roda([str(FIX / "ruins" / "numero-com-multiplicador.md")])
        self.assertEqual(rc, 1, out)
        self.assertIn("número 'R$ 2 milhões'", out)
        self.assertIn("número '15 mil'", out)
        self.assertIn("número '40k'", out)
        self.assertEqual(len([l for l in out.splitlines() if ".md:" in l]), 3, out)

    def test_multiplicador_casa_com_o_valor_por_extenso_da_tabela(self):
        # A-5: 52 mil na prosa e 52.000 na tabela sao o mesmo valor
        rc, out = self._roda_texto(self._troca("Conceito a abandonar", "A cidade tem 52 mil habitantes (N8). Conceito a abandonar"))
        self.assertEqual(rc, 0, out)
        self.assertEqual([v for _, v in rotular.numeros("R$ 2 milhões, 15 mil, 40k, 3 bi, 2 milímetros")],
                         [2e6, 15000.0, 40000.0, 3e9, 2.0])

    def test_linha_sem_coluna_reprova(self):
        # A-8: linha da tabela sem a coluna Fonte
        rc, out = self._roda_texto(self._troca(
            "| F1 | O dono vende 180 pães por dia no balcão | [usuário] | informado em 2026-03-02 |",
            "| F1 | O dono vende 180 pães por dia no balcão | [usuário] |"))
        self.assertEqual(rc, 1, out)
        self.assertIn("linha com 3 colunas, esperadas 4", out)

    def test_identificador_repetido_reprova(self):
        # A-8
        rc, out = self._roda_texto(self._troca("| F3 | A sobra", "| F1 | A sobra"))
        self.assertEqual(rc, 1, out)
        self.assertIn("# 'F1' repetido na tabela Fatos", out)

    def test_tabela_sem_linha_reprova(self):
        # A-8
        t = self._base()
        ini, fim = t.index("| F1 |"), t.index("\n## Números")
        rc, out = self._roda_texto(t[:ini] + t[fim:])
        self.assertEqual(rc, 1, out)
        self.assertIn("tabela 'Fatos' sem nenhuma linha", out)

    def test_tamanho_fora_de_e0_a_e3_reprova(self):
        # A-8
        for ruim in ("E4", "grande", "E2 ou E3"):
            with self.subTest(ruim):
                rc, out = self._roda_texto(self._troca("tamanho: E2\n", f"tamanho: {ruim}\n"))
                self.assertEqual(rc, 1, out)
                self.assertIn("fora de E0 a E3", out)

    def test_secao_repetida_reprova(self):
        # A-8
        rc, out = self._roda_texto(self._base() + "\n## Limites desta análise\n\nOutra versão dos limites desta análise.\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("seção repetida: '## Limites desta análise'", out)


if __name__ == "__main__":
    unittest.main()
