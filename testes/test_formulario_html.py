import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "formulario_html.py"
MOLDE = RAIZ / "moldes" / "formulario.md"
FIX = RAIZ / "testes" / "fixtures"
CABECA = "# Formulário para o público\n\n## Bloco\n"


def gerar(texto):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "f.md").write_text(texto, encoding="utf-8")
        r = subprocess.run(
            [sys.executable, "-I", str(SCRIPT), str(d / "f.md"), str(d / "o.html")],
            capture_output=True, text=True,
            env={"RAIZ_MESTRA_DADOS": str(d), "PATH": ""},
        )
        saida = (d / "o.html").read_text(encoding="utf-8") if (d / "o.html").exists() else None
        return r.returncode, r.stdout, saida


HOSTIL = """# Formulário para o público

# <script>alert(1)</script> título

## <script>alert(1)</script> bloco
1. [unica] <script>alert(1)</script> pergunta | <script>alert(1)</script> | outra
2. [multipla] várias? | a | b
3. [texto] <img src=x onerror=alert(1)> livre
"""


class TestFormularioHtml(unittest.TestCase):
    def test_molde_real_gera_pagina_sem_rede(self):
        rc, out, pagina = gerar(MOLDE.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0, out)
        for proibido in ("http://", "https://", "<script src", "<link"):
            self.assertNotIn(proibido, pagina)
        self.assertIn('type="radio"', pagina)
        self.assertIn('type="checkbox"', pagina)
        self.assertIn("<textarea", pagina)

    def test_texto_hostil_sai_escapado(self):
        rc, out, pagina = gerar(HOSTIL)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("<script>alert(1)</script>", pagina)
        self.assertNotIn("<img src=x", pagina)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", pagina)
        # só o script inline fixo da própria página
        self.assertEqual(pagina.count("<script>"), 1)

    def test_sem_campo_de_nome_email_telefone(self):
        _, _, pagina = gerar(MOLDE.read_text(encoding="utf-8"))
        for tag in re.findall(r"<(?:input|textarea)[^>]*>", pagina):
            self.assertNotRegex(tag, r'type="(email|tel|text)"')
            self.assertNotRegex(tag.lower(), r'name="[^"]*(nome|email|e-mail|telefone|contato|cpf)')

    def test_fixture_que_pede_dado_pessoal_reprova_e_nao_gera(self):
        rc, out, pagina = gerar((FIX / "ruins" / "formulario-pede-dado-pessoal.md").read_text(encoding="utf-8"))
        self.assertEqual(rc, 1, out)
        self.assertIsNone(pagina, "a página não pode ser gerada")
        # diz o que reprovou e onde: as duas perguntas, cada uma com a sua linha
        self.assertRegex(out, r"f\.md:6: .*nome.*CPF.*telefone")
        self.assertRegex(out, r"f\.md:8: .*e-mail")
        self.assertNotIn("f.md:7:", out)

    def test_cada_dado_pessoal_reprova_sozinho(self):
        casos = {
            "nome": "1. [texto] Qual é o seu nome completo?",
            "nome ": "1. [texto] Como você se chama?",
            "nome  ": "1. [texto] Nome e sobrenome",
            "CPF": "1. [texto] Informe o CPF do titular",
            "telefone": "1. [texto] Qual o seu celular?",
            "telefone ": "1. [texto] Passe o WhatsApp para contato",
            "e-mail": "1. [texto] Qual é o seu email?",
            "endereço": "1. [texto] Qual o endereço da sua casa?",
            # o pedido também não entra escondido numa opção
            "telefone  ": "1. [unica] Como prefere? | Deixo meu telefone | Não deixo",
        }
        for dado, linha in casos.items():
            with self.subTest(linha=linha):
                rc, out, pagina = gerar(CABECA + linha + "\n")
                self.assertEqual(rc, 1, out)
                self.assertIsNone(pagina)
                self.assertIn(dado.strip(), out)

    def test_pergunta_que_cita_nome_de_coisa_passa(self):
        rc, out, pagina = gerar((FIX / "boas" / "formulario-sem-dado-pessoal.md").read_text(encoding="utf-8"))
        self.assertEqual(rc, 0, out)
        self.assertIn("nome da ferramenta", pagina)

    def test_pagina_ja_existente_nao_e_tocada_quando_reprova(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "f.md").write_text(CABECA + "1. [texto] Qual é o seu CPF?\n", encoding="utf-8")
            (d / "o.html").write_text("anterior", encoding="utf-8")
            r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(d / "f.md"), str(d / "o.html")],
                               capture_output=True, text=True, env={"RAIZ_MESTRA_DADOS": str(d), "PATH": ""})
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertEqual((d / "o.html").read_text(encoding="utf-8"), "anterior")

    def test_sem_perguntas_reprova(self):
        rc, _, pagina = gerar("# Nada\n\ntexto solto\n")
        self.assertEqual(rc, 1)
        self.assertIsNone(pagina)

    def test_uso_errado(self):
        r = subprocess.run([sys.executable, "-I", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
