"""Nada órfão: o que o SKILL.md cita existe, e toda peça é citada em algum lugar.

Peça é arquivo de scripts/, agents/, papeis/, moldes/ e referencias/.
"Citada" quer dizer: o caminho (pasta/arquivo) aparece no SKILL.md, no README.md
ou em outra peça; para script, vale também o nome do arquivo no SKILL.md ou no
README.md, ou o import do módulo por outro script.

Limite: o teste confere o texto, não o uso. Uma peça citada só em comentário
passa aqui.
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTAS = ("scripts", "agents", "papeis", "moldes", "referencias")
DOCS = ("SKILL.md", "README.md")
CAMINHO = re.compile(r"\b((?:scripts|agents|papeis|moldes|referencias|testes)/[\w./-]*\w)")
SCRIPT_SOLTO = re.compile(r"(?<![\w/.-])([a-z_]+\.py)\b")


def pecas():
    achadas = []
    for pasta in PASTAS:
        for arq in sorted((RAIZ / pasta).rglob("*")):
            if arq.is_file() and "__pycache__" not in arq.parts and arq.suffix != ".pyc":
                achadas.append(arq)
    return achadas


def texto(arq):
    return arq.read_text(encoding="utf-8")


class TestOrfas(unittest.TestCase):
    def test_ha_pecas_em_todas_as_pastas(self):
        for pasta in PASTAS:
            self.assertTrue(any(p.parts[-2] == pasta or pasta in p.parts for p in pecas()),
                            "pasta sem peça nenhuma: %s" % pasta)

    def test_tudo_que_o_skill_e_o_readme_citam_existe(self):
        faltam = []
        for doc in DOCS:
            conteudo = texto(RAIZ / doc)
            for caminho in sorted(set(CAMINHO.findall(conteudo))):
                if not (RAIZ / caminho).exists():
                    faltam.append("%s cita %s, que não existe" % (doc, caminho))
            for nome in sorted(set(SCRIPT_SOLTO.findall(conteudo))):
                if not (RAIZ / "scripts" / nome).exists() and not (RAIZ / "testes" / nome).exists():
                    faltam.append("%s cita %s, que não existe em scripts/ nem em testes/" % (doc, nome))
        self.assertEqual(faltam, [], "\n".join(faltam))

    def test_toda_peca_e_citada_em_algum_lugar(self):
        docs = {doc: texto(RAIZ / doc) for doc in DOCS}
        todas = pecas()
        textos = {p: texto(p) for p in todas}
        orfas = []
        for peca in todas:
            rel = peca.relative_to(RAIZ).as_posix()
            citada = any(rel in t for t in docs.values())
            if not citada:
                citada = any(rel in t for outra, t in textos.items() if outra != peca)
            if not citada and peca.suffix == ".py":
                nome = re.escape(peca.name)
                modulo = re.escape(peca.stem)
                solto = re.compile(r"(?<![\w/.-])%s\b" % nome)
                importa = re.compile(r"^\s*(?:import|from)\s+%s\b" % modulo, re.M)
                citada = any(solto.search(t) for t in docs.values()) or any(
                    importa.search(t) for outra, t in textos.items()
                    if outra != peca and outra.suffix == ".py")
            if not citada:
                orfas.append(rel)
        self.assertEqual(orfas, [], "peça sem citação em SKILL.md, README.md ou outra peça: %s"
                         % ", ".join(orfas))

    def test_todo_ensaio_e_citado(self):
        docs = "\n".join(texto(RAIZ / doc) for doc in DOCS)
        soltos = [e.relative_to(RAIZ).as_posix() for e in sorted((RAIZ / "testes" / "ensaios").glob("*.md"))
                  if e.relative_to(RAIZ).as_posix() not in docs]
        self.assertEqual(soltos, [], "ensaio sem citação no SKILL.md nem no README.md: %s" % ", ".join(soltos))


if __name__ == "__main__":
    unittest.main()
