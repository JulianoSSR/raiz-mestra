"""Testes de scripts/lint_entrega.py (heuristicas por padrao, ver docstring do script)."""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import lint_entrega  # noqa: E402
import rotular  # noqa: E402

FIX = RAIZ / "testes" / "fixtures"
PESQUISA = FIX / "pesquisa"

# fixture ruim -> trecho que a mensagem precisa trazer
RUINS = {
    "maioria-compraria": "(a) 'a maioria'",
    "percentual-em-simulacao": "(a) '30%' em linha [simulação]",
    "taxa-de-adocao-em-hipotese": "(a) 'taxa de adocao' em linha [hipótese]",
    "percentual-sem-fonte": "(a) '30%' sem apontar",
    "tres-em-cada-dez": "(a) 'tres em cada 10' ligado a item [simulação]/[hipótese]",
    "parecer-juridico": "(b) frase normativa",
    "basta-abrir-mei": "(b) frase normativa",
    "trecho-copiado": "(c) trecho copiado de 'fonte-pesquisa.md'",
    "sem-nao-prova": "(d) seção 'O que isto não prova' ausente",
    "limites-vazio": "(d) seção 'Limites desta análise' vazia",
    "eleitoral-recomenda-candidato": "(e) recomendação de candidatura",
    "eleitoral-percentual-de-voto": "(e) percentual/contagem de voto",
    "eleitoral-sem-rotulo-ia": "(e) texto de campanha sem a marca",
    "eleitoral-segmentacao-politica": "(g) segmentação por opinião política",
    "e3-recomenda-sem-coleta": "(f) tamanho E3",
}


def roda(args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = lint_entrega.main(args)
    return rc, buf.getvalue()


class TestLintEntrega(unittest.TestCase):
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

    def _escreve(self, texto):
        p = Path(self.tmp.name) / "e.md"
        p.write_text(texto, encoding="utf-8")
        return str(p)

    def _base(self):
        return (FIX / "boas" / "entrega-exemplo.md").read_text(encoding="utf-8")

    def test_boas_passam(self):
        for nome in ("entrega-exemplo", "eleitoral-ok", "e3-com-coleta", "e3-so-perguntas"):
            with self.subTest(nome):
                rc, out = roda([str(FIX / "boas" / f"{nome}.md"), "--pesquisa", str(PESQUISA)])
                self.assertEqual(rc, 0, out)

    def test_ruins_reprovam_pelo_motivo(self):
        self.assertGreaterEqual(len(RUINS), 8)
        for nome, trecho in RUINS.items():
            with self.subTest(nome):
                rc, out = roda([str(FIX / "ruins" / f"{nome}.md"), "--pesquisa", str(PESQUISA)])
                self.assertEqual(rc, 1, out)
                self.assertIn(trecho, out)
                self.assertIn(f"{nome}.md:", out)

    def test_ruins_de_lint_passam_na_forma(self):
        # defeito unico: o que o lint acusa nao e problema de forma (exceto secoes ausentes)
        for nome in RUINS:
            if nome in ("sem-nao-prova",):
                continue
            with self.subTest(nome):
                msgs = rotular.valida((FIX / "ruins" / f"{nome}.md").read_text(encoding="utf-8"), nome)
                self.assertEqual(msgs, [])

    def test_pesquisa_so_vale_com_flag(self):
        rc, _ = roda([str(FIX / "ruins" / "trecho-copiado.md")])
        self.assertEqual(rc, 0)

    def test_trecho_entre_aspas_com_fonte_passa(self):
        t = self._base().replace(
            "Conceito a abandonar",
            'Segundo o texto, "o comércio varejista de pequeno porte costuma operar com margens apertadas e giro diário" (fonte: nota de pesquisa 2026). Conceito a abandonar')
        rc, out = roda([self._escreve(t), "--pesquisa", str(PESQUISA / "fonte-pesquisa.md")])
        self.assertEqual(rc, 0, out)

    def test_trecho_entre_aspas_sem_fonte_reprova(self):
        t = self._base().replace(
            "Conceito a abandonar",
            'Segundo o texto, "o comércio varejista de pequeno porte costuma operar com margens apertadas e giro diário". Conceito a abandonar')
        rc, out = roda([self._escreve(t), "--pesquisa", str(PESQUISA)])
        self.assertEqual(rc, 1)
        self.assertIn("(c)", out)

    def test_sete_palavras_iguais_nao_reprova(self):
        t = self._base().replace(
            "Conceito a abandonar",
            "Comércio varejista de pequeno porte costuma operar. Conceito a abandonar")
        rc, out = roda([self._escreve(t), "--pesquisa", str(PESQUISA)])
        self.assertEqual(rc, 0, out)

    def test_percentual_apontando_para_usuario_passa_e_para_hipotese_reprova(self):
        t = self._base().replace("Conceito a abandonar", "Cerca de 15% sobra (F3). Conceito a abandonar")
        self.assertEqual(roda([self._escreve(t)])[0], 0)
        t = self._base().replace("Conceito a abandonar", "Cerca de 15% sobra (F3) e 40 aderem (N4). Conceito a abandonar")
        rc, out = roda([self._escreve(t)])
        self.assertEqual(rc, 1)
        self.assertIn("(a)", out)

    def test_pergunta_ao_profissional_pode_ter_a_lei_exige(self):
        rc, out = roda([str(FIX / "boas" / "entrega-exemplo.md")])
        self.assertEqual(rc, 0, out)  # a boa tem "A lei exige ..." na secao de perguntas

    def test_nao_prova_com_negacao_nao_acusa_adocao(self):
        t = self._base().replace("Não prova que clientes pagariam", "Não prova que a maioria compraria nem que clientes pagariam")
        self.assertEqual(roda([self._escreve(t)])[0], 0)

    def test_eleitoral_ausente_vale_como_sim(self):
        t = self._base().replace("eleitoral: não\n", "").replace("Conceito a abandonar", "Vote em Ana Teste. Conceito a abandonar")
        rc, out = roda([self._escreve(t)])
        self.assertEqual(rc, 1)
        self.assertIn("(e)", out)

    def test_e3_com_coleta_aceita_recomendacao(self):
        rc, out = roda([str(FIX / "boas" / "e3-com-coleta.md")])
        self.assertEqual(rc, 0, out)

    def test_segmentacao_so_vale_com_eleitoral_sim(self):
        base = (FIX / "ruins" / "eleitoral-segmentacao-politica.md").read_text(encoding="utf-8")
        rc, _ = roda([self._escreve(base.replace("eleitoral: sim", "eleitoral: não"))])
        self.assertEqual(rc, 0)

    def test_segmentacao_negada_em_limites_passa(self):
        t = (FIX / "boas" / "eleitoral-ok.md").read_text(encoding="utf-8")
        t += " Não há lista de simpatizantes nem microdirecionamento nesta análise.\n"
        rc, out = roda([self._escreve(t)])
        self.assertEqual(rc, 0, out)

    def test_texto_antes_da_primeira_secao_reprova(self):
        # A-1: o lint nao varria o texto entre o cabecalho e o primeiro ##
        rc, out = roda([str(FIX / "ruins" / "texto-antes-da-secao.md")])
        self.assertEqual(rc, 1, out)
        self.assertIn("(h) texto antes da primeira seção", out)

    def test_tabela_fora_de_numeros_reprova(self):
        # A-3: linhas de tabela em Conceitos (comeco com '|') nao eram varridas
        rc, out = roda([str(FIX / "ruins" / "tabela-fora-de-numeros.md")])
        self.assertEqual(rc, 1, out)
        self.assertIn("(a) '40%' sem apontar", out)
        self.assertIn("(a) 'a maioria'", out)

    def test_tabela_comum_em_conceitos_passa(self):
        rc, out = roda([str(FIX / "boas" / "tabela-conceitos-ok.md")])
        self.assertEqual(rc, 0, out)

    def test_recomendacao_e3_em_qualquer_secao_reprova(self):
        # A-4: E3 sem coleta, recomendacao fora de Conceitos
        rc, out = roda([str(FIX / "ruins" / "e3-recomenda-em-teste.md")])
        self.assertEqual(rc, 1, out)
        self.assertIn("(f) tamanho E3", out)
        self.assertIn("'Próximo teste real'", out)

    def test_uso_errado(self):
        self.assertEqual(roda([])[0], 2)
        self.assertEqual(roda(["nao-existe.md"])[0], 2)
        self.assertEqual(roda([str(FIX / "boas" / "entrega-exemplo.md"), "--pesquisa", "nao-existe"])[0], 2)
        self.assertEqual(roda([str(FIX / "boas" / "entrega-exemplo.md"), "--pesquisa"])[0], 2)


    # ---- G6: V-2, A-3, A-4, A-8 -----------------------------------------
    def _troca(self, a, b, base=None):
        base = self._base() if base is None else base
        self.assertEqual(base.count(a), 1, a)
        return base.replace(a, b)

    def test_segundo_titulo_passa_pelos_lints_de_prosa(self):
        # V-2: '# Recomendamos ... 80% dos clientes vao comprar' numa entrega E3
        rc, out = roda([str(FIX / "ruins" / "titulo-com-adocao.md")])
        self.assertEqual(rc, 1, out)
        self.assertIn("titulo-com-adocao.md:7: (a) '80%' sem apontar", out)
        self.assertIn("(f) tamanho E3 com recomendação em 'cabeçalho'", out)

    def test_titulo_e_empreitada_passam_pelos_lints_de_prosa(self):
        # A-3
        for nome, linha in (("titulo-unico-com-adocao", 6), ("cabecalho-com-adocao", 1)):
            with self.subTest(nome):
                rc, out = roda([str(FIX / "ruins" / f"{nome}.md")])
                self.assertEqual(rc, 1, out)
                self.assertIn(f"{nome}.md:{linha}: (a) '70%' sem apontar", out)

    def test_frase_normativa_no_cabecalho_reprova(self):
        # A-3: (b) tambem vale para titulo e valores do cabecalho
        casos = (
            ("empreitada: Assinatura semanal de pães na Padaria Exemplo (fictícia)", "empreitada: Padaria; você deve abrir um MEI e a lei exige alvará"),
            ("# Entrega: assinatura semanal de pães", "# Entrega: basta abrir MEI"),
            ("data: 2026-03-10", "data: 2026-03-10, e a lei exige alvará"),
        )
        for a, b in casos:
            with self.subTest(b):
                rc, out = roda([self._escreve(self._troca(a + "\n", b + "\n"))])
                self.assertEqual(rc, 1, out)
                self.assertIn("(b) frase normativa", out)

    def test_frase_normativa_quebrada_em_linhas_reprova(self):
        # A-4: 'voce deve / abrir um MEI e a lei / exige alvara'
        rc, out = roda([str(FIX / "ruins" / "frase-normativa-quebrada.md")])
        self.assertEqual(rc, 1, out)
        self.assertIn("(b) frase normativa", out)
        self.assertEqual(rotular.valida((FIX / "ruins" / "frase-normativa-quebrada.md").read_text(encoding="utf-8"), "x"), [])

    def test_segmentacao_quebrada_em_linhas_reprova(self):
        # A-4: 'lista de / simpatizantes ... segmentar por / opiniao politica'
        rc, out = roda([str(FIX / "ruins" / "eleitoral-segmentacao-quebrada.md")])
        self.assertEqual(rc, 1, out)
        self.assertIn("(g) segmentação por opinião política individual ('lista de simpatizantes')", out)

    def test_candidatura_quebrada_em_linhas_reprova(self):
        # A-4: 'recomenda a / candidatura dela, que tem intencao de / voto alta'
        rc, out = roda([str(FIX / "ruins" / "eleitoral-candidatura-quebrada.md")])
        self.assertEqual(rc, 1, out)
        self.assertIn("(e) recomendação de candidatura ou voto", out)
        self.assertIn("(e) percentual/contagem de voto", out)

    def test_normativa_em_linha_de_tabela_de_fatos_continua_reprovando(self):
        # A-4: juntar frases nao pode tirar as linhas de Fatos/Numeros de (b), (e) e (g)
        t = self._troca("| F1 | O dono vende 180 pães por dia no balcão |", "| F1 | O dono vende 180 pães por dia e a lei exige alvará |")
        rc, out = roda([self._escreve(t)])
        self.assertEqual(rc, 1, out)
        self.assertIn("(b) frase normativa", out)
        el = (FIX / "boas" / "eleitoral-ok.md").read_text(encoding="utf-8")
        t = self._troca("| F1 | O dono vende 180 pães por dia no balcão |", "| F1 | O dono tem a lista de simpatizantes do partido |", el)
        rc, out = roda([self._escreve(t)])
        self.assertEqual(rc, 1, out)
        self.assertIn("(g)", out)
        t = self._troca("| F1 | O dono vende 180 pães por dia no balcão |", "| F1 | Vote em Ana Teste |", el)
        rc, out = roda([self._escreve(t)])
        self.assertEqual(rc, 1, out)
        self.assertIn("(e) recomendação", out)

    def test_titulo_de_secao_continua_em_e(self):
        # A-4: (e) lia o arquivo inteiro; o titulo '## ...' nao pode sair da varredura
        el = (FIX / "boas" / "eleitoral-ok.md").read_text(encoding="utf-8")
        rc, out = roda([self._escreve(el + "\n## Vote em Ana Teste\n\nTexto qualquer aqui.\n")])
        self.assertEqual(rc, 1, out)
        self.assertIn("(e) recomendação", out)

    def test_negacao_so_desculpa_adocao_em_nao_prova_e_limites(self):
        # A-8: a tolerancia de (a) por negacao nao vale nas outras secoes
        for sec in ("Conceitos", "Pré-mortem", "Próximo teste real", "Perguntas para o profissional"):
            with self.subTest(sec):
                t = self._troca(f"## {sec}\n\n", f"## {sec}\n\nNão há dúvida de que a maioria compraria.\n\n")
                rc, out = roda([self._escreve(t)])
                self.assertEqual(rc, 1, out)
                self.assertIn("(a) 'a maioria'", out)

    def test_normativa_reprova_em_toda_secao_menos_perguntas(self):
        # A-8: (b) nao vale so em Conceitos
        for sec in ("Pré-mortem", "Próximo teste real", "O que isto não prova", "Limites desta análise"):
            with self.subTest(sec):
                t = self._troca(f"## {sec}\n\n", f"## {sec}\n\nA lei exige alvará para entrega.\n\n")
                rc, out = roda([self._escreve(t)])
                self.assertEqual(rc, 1, out)
                self.assertIn("(b) frase normativa", out)
        t = self._troca("## Perguntas para o profissional\n\n", "## Perguntas para o profissional\n\nA lei exige alvará para entrega?\n\n")
        self.assertEqual(roda([self._escreve(t)])[0], 0)

    def test_oito_palavras_iguais_reprova(self):
        # A-8: o limiar de (c) e 8 palavras, nao 12
        t = self._troca("Conceito a abandonar", "Comércio varejista de pequeno porte costuma operar com. Conceito a abandonar")
        rc, out = roda([self._escreve(t), "--pesquisa", str(PESQUISA)])
        self.assertEqual(rc, 1, out)
        self.assertIn("(c) trecho copiado", out)


if __name__ == "__main__":
    unittest.main()
