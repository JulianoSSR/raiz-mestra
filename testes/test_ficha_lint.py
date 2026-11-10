import io
import sys
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


if __name__ == "__main__":
    unittest.main()
