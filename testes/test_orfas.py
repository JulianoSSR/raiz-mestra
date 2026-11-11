"""Nada órfão: o que as peças citam existe, e toda peça é alcançada a partir do SKILL.md ou do README.md.

Peça é arquivo de scripts/, agents/, papeis/, moldes/, referencias/ e skill-trechos/.
"Alcançada" quer dizer: o caminho (pasta/arquivo) aparece no SKILL.md ou no README.md,
ou numa peça que já foi alcançada; para script, vale também o nome do arquivo no
SKILL.md ou no README.md, ou o import do módulo por um script já alcançado.
Duas peças que só se citam uma à outra são órfãs. Citação em comentário (`#` em
Python, `<!-- -->` em Markdown) não conta.

Limite: o teste confere o texto, não o uso. Peça citada só em docstring ou em frase
do tipo "não use mais X" fora de comentário passa aqui.
"""
import io
import re
import shutil
import sys
import tempfile
import tokenize
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import ficha_lint  # noqa: E402

PASTAS = ("scripts", "agents", "papeis", "moldes", "referencias")
TRECHOS = "skill-trechos"
DOCS = ("SKILL.md", "README.md")
CAMINHO = re.compile(
    r"(?<![\w./~-])((?:scripts|agents|papeis|moldes|referencias|testes|skill-trechos)/[\w./-]*\w)")
SCRIPT_SOLTO = re.compile(r"(?<![\w/.-])([a-z_]+\.py)\b")
IMPORTA = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_]\w*)", re.M)
# Pastas que nunca vão para o repositório, além das que o .gitignore listar.
PRIVADAS = (".seiva", ".claude")


def pecas(raiz=RAIZ, pastas=PASTAS):
    achadas = []
    for pasta in pastas:
        if not (raiz / pasta).is_dir():
            continue
        for arq in sorted((raiz / pasta).rglob("*")):
            if arq.is_file() and "__pycache__" not in arq.parts and arq.suffix != ".pyc":
                achadas.append(arq)
    return achadas


def texto(arq):
    return arq.read_text(encoding="utf-8")


def sem_comentario(arq):
    t = texto(arq)
    if arq.suffix == ".py":
        try:
            fichas = [f for f in tokenize.generate_tokens(io.StringIO(t).readline)
                      if f.type != tokenize.COMMENT]
            return tokenize.untokenize(fichas)
        except (tokenize.TokenError, SyntaxError):
            return t
    return re.sub(r"<!--.*?-->", "", t, flags=re.S)


def _cita(rel, t):
    return re.search(r"(?<![\w./~-])%s(?![\w/-]|\.\w)" % re.escape(rel), t) is not None


def orfas(raiz=RAIZ, pastas=PASTAS):
    """Peças que não são alcançadas a partir do SKILL.md nem do README.md."""
    todas = pecas(raiz, pastas)
    rel = {p: p.relative_to(raiz).as_posix() for p in todas}
    textos = {p: sem_comentario(p) for p in todas}
    docs = [sem_comentario(raiz / doc) for doc in DOCS]
    vivas, fila = set(), []
    for p in todas:
        solto = re.compile(r"(?<![\w/.-])%s\b" % re.escape(p.name))
        if any(_cita(rel[p], d) or (p.suffix == ".py" and solto.search(d)) for d in docs):
            vivas.add(p)
            fila.append(p)
    while fila:
        de = fila.pop()
        modulos = set(IMPORTA.findall(textos[de])) if de.suffix == ".py" else set()
        for p in todas:
            if p in vivas:
                continue
            importada = p.suffix == ".py" and p.parent == de.parent and p.stem in modulos
            if importada or _cita(rel[p], textos[de]):
                vivas.add(p)
                fila.append(p)
    return sorted(rel[p] for p in todas if p not in vivas)


def citacoes_sem_arquivo(raiz=RAIZ, pastas=PASTAS + (TRECHOS,)):
    """Caminho de peça citado em doc ou peça (comentário incluído) que não existe."""
    faltam = []
    for arq in [raiz / doc for doc in DOCS] + pecas(raiz, pastas):
        de = arq.relative_to(raiz).as_posix()
        conteudo = texto(arq)
        for caminho in sorted(set(CAMINHO.findall(conteudo))):
            if not (raiz / caminho).exists():
                faltam.append("%s cita %s, que não existe" % (de, caminho))
        if de in DOCS:
            for nome in sorted(set(SCRIPT_SOLTO.findall(conteudo))):
                if not (raiz / "scripts" / nome).exists() and not (raiz / "testes" / nome).exists():
                    faltam.append("%s cita %s, que não existe em scripts/ nem em testes/" % (de, nome))
    return faltam


def ponteiros_privados(raiz=RAIZ, pastas=PASTAS + (TRECHOS,)):
    """Doc ou peça que manda ler arquivo de pasta que não vai para o repositório."""
    nomes = set(PRIVADAS)
    ignora = raiz / ".gitignore"
    if ignora.is_file():
        for l in texto(ignora).splitlines():
            l = l.strip()
            if l.startswith(".") and l.endswith("/") and "*" not in l:
                nomes.add(l.strip("/"))
    padrao = re.compile(r"(?<![\w/~.-])((?:%s)/[\w./-]*\w)" % "|".join(re.escape(n) for n in sorted(nomes)))
    achados = []
    for arq in [raiz / doc for doc in DOCS] + pecas(raiz, pastas):
        for n, l in enumerate(texto(arq).splitlines(), 1):
            for caminho in padrao.findall(l):
                achados.append("%s:%d cita %s, que não vai para o repositório"
                               % (arq.relative_to(raiz).as_posix(), n, caminho))
    return achados


def copia():
    destino = Path(tempfile.mkdtemp()) / "raiz-mestra"
    shutil.copytree(RAIZ, destino, ignore=shutil.ignore_patterns(
        ".git", ".seiva", ".claude", "__pycache__", "*.pyc"))
    return destino


class TestOrfas(unittest.TestCase):
    def test_ha_pecas_em_todas_as_pastas(self):
        for pasta in PASTAS:
            self.assertTrue(any(p.parts[-2] == pasta or pasta in p.parts for p in pecas()),
                            "pasta sem peça nenhuma: %s" % pasta)

    def test_tudo_que_o_skill_o_readme_e_as_pecas_citam_existe(self):
        faltam = citacoes_sem_arquivo()
        self.assertEqual(faltam, [], "\n".join(faltam))

    def test_toda_peca_e_citada_em_algum_lugar(self):
        achadas = orfas()
        self.assertEqual(achadas, [], "peça que não se alcança a partir do SKILL.md nem do README.md: %s"
                         % ", ".join(achadas))

    def test_nenhuma_peca_aponta_para_pasta_privada(self):
        achados = ponteiros_privados()
        self.assertEqual(achados, [], "\n".join(achados))

    def test_todo_ensaio_e_citado(self):
        docs = "\n".join(texto(RAIZ / doc) for doc in DOCS)
        soltos = [e.relative_to(RAIZ).as_posix() for e in sorted((RAIZ / "testes" / "ensaios").glob("*.md"))
                  if e.relative_to(RAIZ).as_posix() not in docs]
        self.assertEqual(soltos, [], "ensaio sem citação no SKILL.md nem no README.md: %s" % ", ".join(soltos))


class TestOrfasPlantadas(unittest.TestCase):
    """Negativos: a regra tem de pegar o que se planta numa cópia do repositório."""

    def setUp(self):
        self.raiz = copia()
        self.addCleanup(shutil.rmtree, self.raiz.parent, True)

    def anexa(self, rel, trecho):
        with (self.raiz / rel).open("a", encoding="utf-8") as f:
            f.write(trecho)

    def test_cinco_orfas_plantadas_sao_pegas(self):
        r = self.raiz
        (r / "papeis" / "par_a.md").write_text("Ver `moldes/par_b.md`.\n", encoding="utf-8")
        (r / "moldes" / "par_b.md").write_text("Ver `papeis/par_a.md`.\n", encoding="utf-8")
        (r / "scripts" / "solto_a.py").write_text("import solto_b\n", encoding="utf-8")
        (r / "scripts" / "solto_b.py").write_text("import solto_a\n", encoding="utf-8")
        (r / "scripts" / "velho.py").write_text("x = 1\n", encoding="utf-8")
        self.anexa("scripts/dados.py", "\n# scripts/velho.py não é mais usado; não chamar.\n")
        self.anexa("moldes/dossie.md", "\n<!-- scripts/velho.py saiu do fluxo -->\n")
        achadas = orfas(r)
        for plantada in ("papeis/par_a.md", "moldes/par_b.md", "scripts/solto_a.py",
                         "scripts/solto_b.py", "scripts/velho.py"):
            self.assertIn(plantada, achadas)
        self.assertEqual(len(achadas), 5, achadas)

    def test_orfa_em_skill_trechos_e_pega(self):
        r = self.raiz
        (r / TRECHOS).mkdir(exist_ok=True)
        (r / TRECHOS / "T-plantado.md").write_text("Trecho que ninguém cita.\n", encoding="utf-8")
        self.assertIn("skill-trechos/T-plantado.md", orfas(r, PASTAS + (TRECHOS,)))

    def test_trecho_citado_no_skill_nao_e_orfa(self):
        r = self.raiz
        (r / TRECHOS).mkdir(exist_ok=True)
        (r / TRECHOS / "T-citado.md").write_text("Trecho citado.\n", encoding="utf-8")
        self.anexa("SKILL.md", "\nVer `skill-trechos/T-citado.md`.\n")
        self.assertNotIn("skill-trechos/T-citado.md", orfas(r, PASTAS + (TRECHOS,)))

    def test_peca_alcancada_por_cadeia_nao_e_orfa(self):
        r = self.raiz
        (r / "papeis" / "elo.md").write_text("Use `moldes/fim.md`.\n", encoding="utf-8")
        (r / "moldes" / "fim.md").write_text("Fim da cadeia.\n", encoding="utf-8")
        self.anexa("README.md", "\nVer `papeis/elo.md`.\n")
        achadas = orfas(r)
        self.assertNotIn("papeis/elo.md", achadas)
        self.assertNotIn("moldes/fim.md", achadas)

    def test_nome_que_so_comeca_igual_nao_conta_como_citacao(self):
        r = self.raiz
        (r / "moldes" / "ficha.md.bak").write_text("sobra\n", encoding="utf-8")
        self.assertIn("moldes/ficha.md.bak", orfas(r))

    def test_ponteiro_para_pasta_privada_e_pego(self):
        r = self.raiz
        (r / "papeis" / "aponta.md").write_text(
            "linha um\nSiga as regras de .seiva/plano/convencoes.md antes de começar.\n", encoding="utf-8")
        achados = ponteiros_privados(r)
        self.assertTrue(any(a.startswith("papeis/aponta.md:2 cita .seiva/plano/convencoes.md") for a in achados),
                        achados)

    def test_ponteiro_dentro_de_comentario_tambem_e_pego(self):
        r = self.raiz
        (r / "moldes" / "aponta.md").write_text("<!-- ver .claude/regras.md -->\n", encoding="utf-8")
        self.assertTrue(any(a.startswith("moldes/aponta.md:1 cita .claude/regras.md")
                            for a in ponteiros_privados(r)))

    def test_caminho_de_instalacao_e_nome_de_pasta_nao_sao_ponteiro(self):
        r = self.raiz
        (r / "papeis" / "ok.md").write_text(
            "Instale em ~/.claude/skills/raiz-mestra. A pasta .seiva fica fora do hash.\n", encoding="utf-8")
        self.assertFalse(any(a.startswith("papeis/ok.md") for a in ponteiros_privados(r)))

    def test_peca_que_cita_arquivo_que_nao_existe_reprova(self):
        r = self.raiz
        (r / "papeis" / "cita.md").write_text("Rode `scripts/nao_existe.py`.\n", encoding="utf-8")
        self.assertIn("papeis/cita.md cita scripts/nao_existe.py, que não existe", citacoes_sem_arquivo(r))


class TestMoldeFicha(unittest.TestCase):
    """O bloco do molde de ficha, copiado sem preencher, não passa no ficha_lint."""

    def bloco(self):
        dentro, linhas = False, []
        for l in texto(RAIZ / "moldes" / "ficha.md").splitlines():
            if l.strip() == "```":
                dentro = not dentro
                continue
            if dentro:
                linhas.append(l)
        self.assertTrue(linhas, "molde sem bloco de modelo")
        return "\n".join(linhas) + "\n"

    def test_molde_copiado_como_esta_reprova_pelo_campo_origem(self):
        erros, _ = ficha_lint.validar(self.bloco())
        self.assertTrue(any("origem" in e for e in erros), erros)

    def test_reprova_mesmo_sem_os_comentarios_do_fim_da_linha(self):
        # quem apaga só o "# ..." de cada linha ainda não preencheu nada
        limpo = re.sub(r"[ \t]+#[^\n]*", "", self.bloco())
        erros, _ = ficha_lint.validar(limpo)
        self.assertTrue(any("origem" in e for e in erros), "molde sem preencher passou no ficha_lint")

    def cabecalho_preenchido(self):
        cheio = re.sub(r"(?m)^origem:.*$", "origem: arquetipo", self.bloco())
        cheio = re.sub(r"(?m)^consentimento:.*$", "consentimento: nao se aplica", cheio)
        cheio = re.sub(r"(?m)^fonte:.*$", "fonte:", cheio)
        return re.sub(r"(?m)^identificacao_indireta_revisada:.*$", "identificacao_indireta_revisada: nao", cheio)

    def test_molde_preenchido_passa(self):
        # ficha de verdade: cabeçalho e corpo preenchidos, sem orientação do modelo
        cheio = self.cabecalho_preenchido()
        cheio = re.sub(r"(?m)^\(.*\)\s*$", "Texto de exemplo.", cheio)
        cheio = re.sub(r"(?m)^(## .*)$", r"\1\nTexto de exemplo.", cheio)
        erros, _ = ficha_lint.validar(cheio)
        self.assertEqual(erros, [])

    def test_so_o_cabecalho_preenchido_reprova(self):
        # A-14: origem preenchida e o resto do modelo intacto não é ficha pronta
        erros, _ = ficha_lint.validar(self.cabecalho_preenchido())
        self.assertTrue(any("parênteses" in e for e in erros), erros)

    def test_placeholder_no_cabecalho_reprova(self):
        cheio = self.cabecalho_preenchido().replace("fonte:", "fonte: <id do registro de coleta>")
        erros, _ = ficha_lint.validar(cheio)
        self.assertTrue(any("<...>" in e for e in erros), erros)
        self.assertTrue(any("seção sem texto" in e for e in erros), erros)


if __name__ == "__main__":
    unittest.main()
