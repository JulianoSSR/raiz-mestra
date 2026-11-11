import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import ficha_lint  # noqa: E402

BOAS = RAIZ / "testes" / "fixtures" / "boas"
RUINS = RAIZ / "testes" / "fixtures" / "ruins"


def rodar(pasta, nome, *extra):
    saida = io.StringIO()
    with redirect_stdout(saida):
        codigo = ficha_lint.main([str(pasta / nome)] + list(extra))
    return codigo, saida.getvalue()


class TestFichaLint(unittest.TestCase):
    def test_arquetipo_sem_sinais_da_exit_0(self):
        self.assertEqual(rodar(BOAS, "ficha-arquetipo.md")[0], 0)

    def test_real_com_consentimento_sem_sinais_da_exit_0(self):
        self.assertEqual(rodar(BOAS, "ficha-real-consentida.md")[0], 0)

    def test_cpf_no_texto_da_exit_1(self):
        c, s = rodar(RUINS, "ficha-cpf.md")
        self.assertEqual(c, 1)
        self.assertIn("CPF", s)

    def test_email_no_texto_da_exit_1(self):
        self.assertEqual(rodar(RUINS, "ficha-email.md")[0], 1)

    def test_telefone_no_texto_da_exit_1(self):
        self.assertEqual(rodar(RUINS, "ficha-telefone.md")[0], 1)

    def test_consentimento_ausente_em_origem_real_da_exit_1(self):
        self.assertEqual(rodar(RUINS, "ficha-sem-consentimento.md")[0], 1)

    def test_consentimento_diferente_de_sim_em_origem_real_da_exit_1(self):
        self.assertEqual(rodar(RUINS, "ficha-consentimento-nao.md")[0], 1)

    def test_dona_maria_da_padaria_da_exit_1(self):
        self.assertEqual(rodar(RUINS, "ficha-tratamento-dona.md")[0], 1)

    def test_seu_joao_da_exit_1(self):
        self.assertEqual(rodar(RUINS, "ficha-tratamento-seu.md")[0], 1)

    def test_dr_sra_prof_com_nome_da_exit_1(self):
        c, s = rodar(RUINS, "ficha-tratamento-dr-prof.md")
        self.assertEqual(c, 1)
        self.assertGreaterEqual(s.count("tratamento"), 1)

    def test_cargo_mais_cidade_sem_revisao_da_exit_1(self):
        self.assertEqual(rodar(RUINS, "ficha-cargo-cidade.md")[0], 1)

    def test_cargo_mais_capital_sem_revisao_da_exit_1(self):
        self.assertEqual(rodar(RUINS, "ficha-cargo-cidade-capital.md")[0], 1)

    def test_cargo_mais_cidade_com_revisao_da_exit_0_com_aviso(self):
        c, s = rodar(BOAS, "ficha-cargo-cidade-revisada.md")
        self.assertEqual(c, 0)
        self.assertIn("AVISO", s)

    def test_cargo_mais_cidade_com_revisao_em_modo_eleitoral_da_exit_1(self):
        self.assertEqual(rodar(BOAS, "ficha-cargo-cidade-revisada.md", "--eleitoral")[0], 1)

    def test_opiniao_politica_de_origem_real_da_exit_1_so_agregado(self):
        c, s = rodar(RUINS, "ficha-politica-real.md")
        self.assertEqual(c, 1)
        self.assertIn("só agregado", s)

    def test_saude_de_origem_real_da_exit_1(self):
        self.assertEqual(rodar(RUINS, "ficha-saude-real.md")[0], 1)

    def test_religiao_de_pessoa_identificada_da_exit_1(self):
        c, s = rodar(RUINS, "ficha-religiao-identificada.md")
        self.assertEqual(c, 1)
        self.assertIn("só agregado", s)

    def test_eleitor_real_em_modo_eleitoral_da_exit_1_mesmo_revisado(self):
        self.assertEqual(rodar(RUINS, "ficha-eleitor-real.md", "--eleitoral")[0], 1)

    def test_arquetipo_limpo_em_modo_eleitoral_da_exit_0(self):
        self.assertEqual(rodar(BOAS, "ficha-arquetipo.md", "--eleitoral")[0], 0)

    def test_arquivo_inexistente_da_exit_2(self):
        self.assertEqual(rodar(BOAS, "nao-existe.md")[0], 2)

    def test_toda_ficha_ruim_reprova(self):
        for f in sorted(RUINS.glob("ficha-*.md")):
            if f.name == "ficha-eleitor-real.md":
                continue  # só reprova com --eleitoral; teste próprio acima
            self.assertEqual(rodar(RUINS, f.name)[0], 1, f.name)

    def test_toda_ficha_boa_aprova(self):
        for f in sorted(BOAS.glob("ficha-*.md")):
            self.assertEqual(rodar(BOAS, f.name)[0], 0, f.name)

    # R-3: cargo + cidade revisada não basta quando a ficha traz opinião, saúde ou religião.
    def test_cargo_cidade_revisada_com_opiniao_da_exit_1(self):
        c, s = rodar(RUINS, "ficha-cargo-cidade-revisada-opiniao.md")
        self.assertEqual(c, 1)
        self.assertIn("só agregado", s)

    def test_cargo_cidade_revisada_sem_opiniao_segue_com_aviso(self):
        c, s = rodar(BOAS, "ficha-cargo-cidade-revisada-sem-opiniao.md")
        self.assertEqual(c, 0)
        self.assertIn("AVISO", s)

    # R-4: preposições do/da/no/na/por e caixa livre contam como cidade; tratamento sem caixa.
    def test_prefeito_do_crato_da_exit_1(self):
        self.assertEqual(rodar(RUINS, "ficha-prefeito-do-crato.md")[0], 1)

    def test_prefeito_de_cidade_em_minusculo_da_exit_1(self):
        self.assertEqual(rodar(RUINS, "ficha-prefeito-minusculo.md")[0], 1)

    def test_vereadora_por_cidade_da_exit_1(self):
        self.assertEqual(rodar(RUINS, "ficha-vereadora-por-cidade.md")[0], 1)

    def test_dona_nome_em_minusculo_da_exit_1(self):
        self.assertEqual(rodar(RUINS, "ficha-dona-minuscula.md")[0], 1)

    def test_dona_nome_em_maiusculo_da_exit_1(self):
        self.assertEqual(rodar(RUINS, "ficha-dona-maiuscula.md")[0], 1)

    # R-4 (regressão): texto comum de arquétipo não pode reprovar nem pedir revisão.
    LEGITIMAS = (
        "Valoriza o seu atendimento rápido.",
        "Seu concorrente cobra menos e entrega depois.",
        "Professora aposentada, mora com a filha.",
        "Professor universitário, dá aula à noite.",
        "A dona não quer mensalidade.",
        "O sr. fiscal aparece uma vez por ano.",
        "Diretora de compras de uma rede de mercados.",
        "Presidente da associação de moradores do bairro.",
        "Síndico do prédio, cuida das contas do condomínio.",
        "Secretária da escola, faz as matrículas.",
        "Diretor da empresa, decide junto com o sócio.",
        "Dona de pequena padaria de bairro, abre antes das seis.",
        "Promotora de vendas em supermercado.",
        "Pastor de uma igreja de bairro, cuida das finanças.",
    )
    CABECALHO = "origem: arquetipo\nconsentimento: nao se aplica\n\n## Contexto de vida e trabalho\n"

    def _avulsa(self, frase, *extra, cabecalho=None):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "f.md").write_text((cabecalho or self.CABECALHO) + frase + "\n",
                                            encoding="utf-8")
            return rodar(Path(tmp), "f.md", *extra)

    def test_fichas_legitimas_aprovam_sem_revisao_e_sem_aviso(self):
        for frase in self.LEGITIMAS:
            with self.subTest(frase=frase):
                c, s = self._avulsa(frase)
                self.assertEqual(c, 0, s)
                self.assertNotIn("AVISO", s)

    def test_fichas_legitimas_aprovam_em_modo_eleitoral(self):
        for frase in self.LEGITIMAS:
            with self.subTest(frase=frase):
                c, s = self._avulsa(frase, "--eleitoral")
                self.assertEqual(c, 0, s)

    def test_fixtures_boas_da_regressao_aprovam_sem_aviso(self):
        for nome in ("ficha-seu-atendimento.md", "ficha-professora-aposentada.md",
                     "ficha-diretora-de-compras.md"):
            for extra in ((), ("--eleitoral",)):
                with self.subTest(nome=nome, extra=extra):
                    c, s = rodar(BOAS, nome, *extra)
                    self.assertEqual(c, 0, s)
                    self.assertNotIn("AVISO", s)

    def test_seis_casos_do_resina_seguem_reprovando(self):
        casos = (("O prefeito do Crato decide a compra.", ()),
                 ("prefeito de sobral decide a compra.", ()),
                 ("Vereadora por Sobral.", ("--eleitoral",)),
                 ("O prefeito do Crato é evangélico e vota no PT.", ("--eleitoral",)),
                 ("A dona maria da padaria abre cedo.", ()),
                 ("DONA MARIA da padaria abre cedo.", ()))
        for frase, extra in casos:
            with self.subTest(frase=frase):
                self.assertEqual(self._avulsa(frase, *extra)[0], 1)

    def test_dona_nome_minusculo_revisado_vira_aviso_mas_nao_em_modo_eleitoral(self):
        cab = self.CABECALHO.replace("\n\n", "\nidentificacao_indireta_revisada: sim\n\n", 1)
        c, s = self._avulsa("A dona maria da padaria abre cedo.", cabecalho=cab)
        self.assertEqual(c, 0, s)
        self.assertIn("AVISO", s)
        self.assertEqual(self._avulsa("A dona maria da padaria abre cedo.", "--eleitoral",
                                      cabecalho=cab)[0], 1)

    def test_tratamento_com_nome_comum_em_minusculo_reprova(self):
        # volta a pegar: lista de nomes comuns, depois de seu/dr./sr. etc.
        for frase in ("seu joão decide a compra.", "dr. carlos assina o contrato.",
                      "sra. ana paga à vista."):
            with self.subTest(frase=frase):
                c, s = self._avulsa(frase)
                self.assertEqual(c, 1, s)

    def test_tratamento_minusculo_sem_nome_da_lista_passa(self):
        # sem falso positivo em frase comum com "seu"/"dr."
        for frase in ("Valoriza o seu atendimento rápido.", "seu foco é o preço."):
            with self.subTest(frase=frase):
                c, s = self._avulsa(frase)
                self.assertEqual(c, 0, s)

    def test_tratamento_com_nome_comum_revisado_vira_aviso(self):
        cab = self.CABECALHO.replace("\n\n", "\nidentificacao_indireta_revisada: sim\n\n", 1)
        c, s = self._avulsa("seu joão decide a compra.", cabecalho=cab)
        self.assertEqual(c, 0, s)
        self.assertIn("AVISO", s)
        self.assertEqual(self._avulsa("seu joão decide a compra.", "--eleitoral", cabecalho=cab)[0], 1)

    def test_cargo_publico_colado_a_cidade_minuscula_reprova(self):
        for frase in ("a vereadora por sobral decide.", "o delegado de quixadá assina.",
                      "juíza em crato despacha."):
            with self.subTest(frase=frase):
                self.assertEqual(self._avulsa(frase)[0], 1)


if __name__ == "__main__":
    unittest.main()
