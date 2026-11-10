"""Reprova linha de referencias/*.md que cita artigo, lei, resolução ou prazo sem fonte oficial."""
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent.parent
BOAS = RAIZ / "testes" / "fixtures" / "boas"
RUINS = RAIZ / "testes" / "fixtures" / "ruins"

DOMINIOS = (
    "planalto.gov.br", "tse.jus.br", "camara.leg.br", "senado.leg.br", "gov.br", "in.gov.br",
)
CITACAO = re.compile(
    r"\bart(?:igos?|s?\.)\s*\d"
    r"|\bLeis?\s+(?:n[ºo°.]*\s*)?\d"
    r"|\bDecreto-Lei\s+(?:n[ºo°.]*\s*)?\d"
    r"|\bResolu[çc][ãa]o\s+(?:do\s+)?(?:TSE\s+)?(?:n[ºo°.]*\s*)?\d"
    r"|\bRes\.\s*(?:TSE\s+)?\d"
    r"|\b\d+\s*(?:horas?|dias?|h|meses|anos)\b",
    re.IGNORECASE,
)
URL = re.compile(r"https?://[^\s)>\]]+")
LIDO = re.compile(r"lido em \d{4}-\d{2}-\d{2}")
MARCA = "conferir antes de citar"


def dominio_oficial(url):
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in DOMINIOS)


def verificar(texto, nome="texto"):
    """Devolve lista de mensagens 'arquivo:linha: motivo'."""
    erros = []
    for n, linha in enumerate(texto.splitlines(), 1):
        if not CITACAO.search(linha):
            continue
        if MARCA in linha.lower():
            continue
        oficial = any(dominio_oficial(u) for u in URL.findall(linha))
        if oficial and LIDO.search(linha):
            continue
        erros.append(
            "%s:%d: cita artigo, lei, resolução ou prazo sem URL oficial com 'lido em AAAA-MM-DD' "
            "nem a marca '%s'" % (nome, n, MARCA)
        )
    return erros


class TestReferencias(unittest.TestCase):
    def test_referencias_reais(self):
        erros = []
        for p in sorted((RAIZ / "referencias").glob("*.md")):
            erros += verificar(p.read_text(encoding="utf-8"), "referencias/" + p.name)
        self.assertEqual(erros, [], "\n" + "\n".join(erros))

    def test_fixtures_boas_aprovam(self):
        arquivos = sorted(BOAS.glob("ref_*.md"))
        self.assertTrue(arquivos)
        for p in arquivos:
            self.assertEqual(verificar(p.read_text(encoding="utf-8"), p.name), [], p.name)

    def test_fixtures_ruins_reprovam(self):
        arquivos = sorted(RUINS.glob("ref_ruim_*.md"))
        self.assertGreaterEqual(len(arquivos), 5)
        for p in arquivos:
            self.assertTrue(verificar(p.read_text(encoding="utf-8"), p.name), p.name)

    def test_mensagem_traz_arquivo_e_linha(self):
        erros = verificar("ok\nLei 1.234 diz algo\n", "x.md")
        self.assertTrue(erros[0].startswith("x.md:2:"))

    def test_subdominio_e_dominio_falso(self):
        self.assertTrue(dominio_oficial("https://www.planalto.gov.br/x"))
        self.assertFalse(dominio_oficial("https://planalto.gov.br.falso.com/x"))


if __name__ == "__main__":
    unittest.main()
