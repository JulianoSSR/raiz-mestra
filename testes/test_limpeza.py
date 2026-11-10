import json
import os
import stat
import sys
import tempfile
import unittest
import unicodedata
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import pseudonimizar  # noqa: E402

FONTE = (
    "Maria Souza contou que o CPF dela é 123.456.789-00 e o outro, 12345678900.\n"
    "Escreva para maria@dominio.invalid ou ligue (85) 99999-0000 ou +55 85 99999-0000.\n"
    "Também atende no 99999-0000. CEP 60000-000. Mora na Rua das Flores, 123 e\n"
    "trabalha na Av. Central 45. Sítio na Rodovia CE-040 km 12.\n"
    "O João disse que Maria concorda. A empresa tem CNPJ 12.345.678/0001-90.\n"
)


class TestLimpeza(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.dict(os.environ, {"RAIZ_MESTRA_DADOS": self.tmp.name})
        p.start()
        self.addCleanup(p.stop)
        self.dir = Path(self.tmp.name) / "trabalho"
        self.dir.mkdir()

    def rodar(self, fonte, nomes=None, *extra):
        ent, sai = self.dir / "e.txt", self.dir / "s.txt"
        ent.write_text(fonte, encoding="utf-8")
        args = [str(ent), str(sai)]
        if nomes is None:
            args.append("--so-limpeza")
        else:
            lista = self.dir / "nomes.txt"
            lista.write_text("\n".join(nomes), encoding="utf-8")
            args += ["--nomes", str(lista), "--dossie", "caso"]
        saida = StringIO()
        with redirect_stdout(saida):
            codigo = pseudonimizar.main(args + list(extra))
        return codigo, sai.read_text(encoding="utf-8") if sai.exists() else "", saida.getvalue()

    def test_so_limpeza_tira_cpf_email_telefone_cep_e_endereco(self):
        c, out, msg = self.rodar(FONTE)
        self.assertEqual(c, 0)
        for proibido in ("123.456.789-00", "12345678900", "maria@dominio.invalid",
                         "99999-0000", "60000-000", "Rua das Flores", "Av. Central",
                         "CE-040 km 12"):
            self.assertNotIn(proibido, out, proibido)
        for marca in ("[cpf removido]", "[email removido]", "[telefone removido]",
                      "[cep removido]", "[endereco removido]"):
            self.assertIn(marca, out)

    def test_cnpj_nao_e_removido(self):
        _, out, _ = self.rodar(FONTE)
        self.assertIn("12.345.678/0001-90", out)

    def test_imprime_contagem_e_aviso_fixo(self):
        _, _, msg = self.rodar(FONTE)
        self.assertIn("cpf: 2", msg)
        self.assertIn("email: 1", msg)
        self.assertIn("Limpeza por padrão: não é garantia. O texto que você colou na "
                      "conversa já foi enviado ao provedor do modelo.", msg)

    def test_nomes_da_lista_viram_codigos_sem_diferenciar_caixa_e_acento(self):
        c, out, _ = self.rodar("MARIA souza e joao, depois João e Maria.", ["Maria Souza", "João"])
        self.assertEqual(c, 0)
        self.assertEqual(out, "P01 e P02, depois P02 e Maria.")

    def test_primeiro_nome_isolado_so_quando_a_lista_trouxer(self):
        _, out, _ = self.rodar("Maria Souza falou. Maria saiu.", ["Maria Souza", "Maria"])
        self.assertEqual(out, "P01 falou. P02 saiu.")

    def test_palavra_inteira(self):
        _, out, _ = self.rodar("Mariana e Maria.", ["Maria"])
        self.assertEqual(out, "Mariana e P01.")

    def test_mapa_fica_no_dossie_e_nao_aparece_na_saida(self):
        _, out, msg = self.rodar("Falou com Maria Souza.", ["Maria Souza"])
        self.assertNotIn("Maria", out)
        self.assertNotIn("Maria", msg)
        mapa = Path(self.tmp.name) / "dossies" / "caso" / "mapa-pseudonimos.json"
        self.assertEqual(json.loads(mapa.read_text(encoding="utf-8")), {"Maria Souza": "P01"})

    def test_codigo_estavel_entre_rodadas(self):
        self.rodar("Ana e Bia.", ["Ana", "Bia"])
        _, out, _ = self.rodar("Bia chegou. Carla também.", ["Bia", "Carla"])
        self.assertEqual(out, "P02 chegou. P03 também.")

    def test_sem_nomes_e_sem_so_limpeza_da_exit_2(self):
        ent = self.dir / "e.txt"
        ent.write_text("x", encoding="utf-8")
        with redirect_stdout(StringIO()):
            self.assertEqual(pseudonimizar.main([str(ent), str(self.dir / "s.txt")]), 2)

    def test_so_limpeza_nao_grava_mapa(self):
        self.rodar("Maria.")
        self.assertFalse((Path(self.tmp.name) / "dossies").exists())

    def test_limitacao_conhecida_endereco_por_extenso_sem_numero_passa(self):
        # LIMITAÇÃO DECLARADA: sem logradouro + número a heurística não acha endereço.
        # Este teste documenta a falha; se um dia passar a remover, atualize o README.
        frase = "mora na rua atrás da igreja matriz"
        _, out, _ = self.rodar(frase)
        self.assertIn("rua atrás da igreja matriz", out)

    def test_limitacao_conhecida_nome_fora_da_lista_passa(self):
        # LIMITAÇÃO DECLARADA: nome que o usuário não listou fica no texto.
        _, out, _ = self.rodar("Falou com Carla Dias.", ["Maria"])
        self.assertIn("Carla Dias", out)

    # R-5: formatos correntes que a limpeza antes deixava passar.
    def test_cpf_em_todos_os_formatos(self):
        for cpf in ("123456789-09", "123 456 789 09", "123.456.789 - 09",
                    "123.456.789/09", "123456789 09"):
            with self.subTest(cpf=cpf):
                c, out, _ = self.rodar("Cadastro com CPF %s fim." % cpf)
                self.assertEqual(c, 0)
                self.assertNotIn(cpf, out)
                self.assertIn("[cpf removido]", out)

    def test_telefone_em_todos_os_formatos(self):
        for tel in ("85.99999.0000", "99999 0000", "85 9 9999 0000",
                    "(85) 9 9999-0000", "+55 85 99999-0000", "85 99999-0000"):
            with self.subTest(tel=tel):
                _, out, _ = self.rodar("Ligue %s hoje." % tel)
                self.assertNotIn(tel, out)
                self.assertIn("[telefone removido]", out)

    def test_cep_sem_hifen_e_com_ponto(self):
        for cep in ("60000000", "60.000-000"):
            with self.subTest(cep=cep):
                _, out, _ = self.rodar("Moro no CEP %s, perto." % cep)
                self.assertNotIn(cep, out)
                self.assertIn("[cep removido]", out)

    def test_endereco_com_numero_no_nome_da_rua(self):
        for end in ("Rua 7 de Setembro, 45", "Rua 13 de Maio, 200"):
            with self.subTest(end=end):
                _, out, _ = self.rodar("Entregar na %s amanhã." % end)
                self.assertNotIn(end, out)
                self.assertIn("[endereco removido]", out)

    # R-6: lista em NFD e caractere de largura zero não podem escapar da troca.
    def test_lista_em_nfd_troca_o_nome(self):
        nfd = unicodedata.normalize("NFD", "José da Silva")
        c, out, _ = self.rodar("José da Silva falou.", [nfd])
        self.assertEqual(c, 0)
        self.assertEqual(out, "P01 falou.")

    def test_caractere_de_largura_zero_no_texto_nao_impede_a_troca(self):
        _, out, _ = self.rodar("Ma​ria falou.", ["Maria"])
        self.assertEqual(out, "P01 falou.")

    def test_nome_da_lista_sem_ocorrencia_vira_aviso_e_nao_sai_com_1(self):
        c, out, msg = self.rodar("Falou com Ana.", ["Ana", "Bruno"])
        self.assertEqual(c, 0)
        self.assertEqual(out, "Falou com P01.")
        self.assertIn("AVISO", msg)
        self.assertIn("nome da lista número 2", msg)
        self.assertNotIn("Bruno", msg)

    # R-12: o mapa nasce com 0o600, sem arquivo temporário sobrando, e mapa inválido dá exit 1.
    @unittest.skipUnless(os.name == "posix", "modo de arquivo só vale em POSIX")
    def test_mapa_nasce_so_para_o_dono_e_sem_sobra(self):
        self.rodar("Falou com Maria Souza.", ["Maria Souza"])
        pasta = Path(self.tmp.name) / "dossies" / "caso"
        mapa = pasta / "mapa-pseudonimos.json"
        self.assertEqual(stat.S_IMODE(mapa.stat().st_mode), 0o600)
        self.assertEqual(sorted(os.listdir(pasta)), ["mapa-pseudonimos.json"])

    def test_mapa_que_nao_e_dicionario_da_exit_1_e_nao_e_alterado(self):
        pasta = Path(self.tmp.name) / "dossies" / "caso"
        pasta.mkdir(parents=True)
        mapa = pasta / "mapa-pseudonimos.json"
        mapa.write_text("[1]", encoding="utf-8")
        c, _, msg = self.rodar("Maria.", ["Maria"])
        self.assertEqual(c, 1)
        self.assertIn("mapa", msg)
        self.assertEqual(mapa.read_text(encoding="utf-8"), "[1]")

    def test_mapa_corrompido_da_exit_1(self):
        pasta = Path(self.tmp.name) / "dossies" / "caso"
        pasta.mkdir(parents=True)
        (pasta / "mapa-pseudonimos.json").write_text("{nao fecha", encoding="utf-8")
        c, _, msg = self.rodar("Maria.", ["Maria"])
        self.assertEqual(c, 1)
        self.assertIn("mapa", msg)


if __name__ == "__main__":
    unittest.main()
