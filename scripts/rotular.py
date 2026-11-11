#!/usr/bin/env python3
"""rotular.py <entrega.md>

Confere a FORMA da entrega, nao a verdade. Passar aqui NAO significa que um
fato seja verdadeiro, que uma URL exista ou que um numero esteja certo: isso e
o portao 2 (juiz). O que e conferido:

  - cabecalho (linhas `chave: valor` antes do primeiro `##`) com empreitada,
    tamanho (E0 a E3), eleitoral (sim|nao) e data (AAAA-MM-DD valida), e no
    maximo uma linha de titulo `# ...`;
  - as 8 secoes de nivel 2 com titulo exato, cada uma uma vez;
  - secoes Fatos e Numeros so com tabela: toda linha iniciada por `|` e
    conferida (inclusive depois de linha em branco ou em segunda tabela) e
    qualquer outra linha nao vazia reprova; colunas certas e, em toda linha,
    Rotulo valido e Fonte no formato do rotulo:
      [usuario]   -> data AAAA-MM-DD
      [publico]   -> URL http(s) e data AAAA-MM-DD
      [simulacao] -> `painel:<id>`
      [hipotese]  -> `como medir: ...`
  - todo numero da prosa, do titulo e dos valores do cabecalho (valor
    monetario, percentual, quantidade) tem valor igual ao de alguma linha da
    coluna Numero da tabela Numeros; multiplicador depois do numero conta
    ("2 milhoes" vale 2.000.000, "15 mil" vale 15.000, "40k" vale 40.000).

Declaradamente NAO pega:
  - se a fonte e verdadeira, se a URL abre ou se a data e a real;
  - numero escrito por extenso ("tres clientes", "dois mil");
  - unidade: 30% na prosa casa com 30 clientes na tabela (so o valor e comparado);
  - ano isolado (19xx/20xx sem R$ nem %) e numero colado em letras (E3, COVID-19)
    sao ignorados de proposito, e por isso tambem nao sao conferidos;
  - numero escrito em imagem, codigo ou fora do Markdown;
  - multiplicador fora da lista (mil, milhao/milhoes, bilhao/bilhoes, mi, bi,
    k, M) ou composto ("2 mil e 500" vale 2.000 e 500 em separado).

Saida: 0 aprovado, 1 reprovado, 2 uso errado.
"""
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

SECOES = [
    "Fatos", "Números", "Conceitos", "Pré-mortem", "Próximo teste real",
    "Perguntas para o profissional", "O que isto não prova",
    "Limites desta análise",
]
CHAVES = ["empreitada", "tamanho", "eleitoral", "data"]
COLS_FATOS = ["#", "Fato", "Rótulo", "Fonte"]
COLS_NUMEROS = ["#", "Número", "O que mede", "Rótulo", "Fonte"]
ROTULOS = ["[usuário]", "[público]", "[simulação]", "[hipótese]"]

RE_DATA = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
RE_URL = re.compile(r"https?://[^\s|)>\]]+", re.I)
RE_PAINEL = re.compile(r"painel\s*[:#]\s*[\w.\-]+", re.I)
RE_COMO_MEDIR = re.compile(r"como medir\s*:\s*\S.{3,}", re.I)
VAZIOS = {"", "-", "—", "–", "n/a", "na", "tbd", "todo", "?", "..."}


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def data_valida(s):
    for m in RE_DATA.finditer(s):
        try:
            date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return True
        except ValueError:
            continue
    return False


def fonte_ok(rotulo, fonte):
    """Devolve None se a fonte tem a forma do rotulo, ou a mensagem do defeito."""
    f = fonte.strip()
    if f.lower() in VAZIOS:
        return "Fonte vazia"
    if rotulo == "[usuário]":
        return None if data_valida(f) else "Fonte [usuário] sem data AAAA-MM-DD"
    if rotulo == "[público]":
        if not RE_URL.search(f):
            return "Fonte [público] sem URL http(s)"
        return None if data_valida(f) else "Fonte [público] sem data de consulta AAAA-MM-DD"
    if rotulo == "[simulação]":
        return None if RE_PAINEL.search(f) else "Fonte [simulação] sem id de painel (painel:<id>)"
    if rotulo == "[hipótese]":
        return None if RE_COMO_MEDIR.search(f) else 'Fonte [hipótese] sem "como medir: ..."'
    return "Rótulo inválido"


def parse_entrega(texto):
    """Quebra o Markdown em cabecalho, secoes e tabelas.

    Devolve dict: header, secoes (lista de dict titulo/linha/linhas) e erros."""
    linhas = texto.splitlines()
    header, secoes, erros, pre = {}, [], [], []
    atual = None
    for n, ln in enumerate(linhas, 1):
        m = re.match(r"^##\s+(.+?)\s*$", ln)
        if m and not ln.startswith("###"):
            atual = {"titulo": m.group(1), "linha": n, "linhas": []}
            secoes.append(atual)
            continue
        if atual is None:
            pre.append((n, ln))
            m2 = re.match(r"^([A-Za-zÀ-ÿ_]+)\s*:\s*(.*?)\s*$", ln)
            if m2 and not ln.startswith("#"):
                header[sem_acento(m2.group(1)).lower()] = m2.group(2)
        else:
            atual["linhas"].append((n, ln))
    return {"header": header, "secoes": secoes, "erros": erros, "pre": pre}


def prosa_cabecalho(ent):
    """(linha, texto) do titulo '# ...' e do valor de cada chave do cabecalho.

    E o que linhas_fora_de_secao deixa passar; quem chama confere esse texto
    com as mesmas regras da prosa das secoes."""
    out = []
    for n, ln in ent["pre"]:
        s = ln.strip()
        m = re.match(r"^#(?!#)\s+(.*)$", s)
        if m:
            out.append((n, m.group(1)))
            continue
        m = re.match(r"^([A-Za-zÀ-ÿ_]+)\s*:\s*(.*)$", s)
        if m and sem_acento(m.group(1)).lower() in CHAVES:
            out.append((n, m.group(2)))
    return out


def linhas_fora_de_secao(ent):
    """Linhas antes da primeira secao que nao sao vazias, titulo '# ...' nem chave do cabecalho.

    Titulo e chaves nao ficam sem conferencia: saem em prosa_cabecalho."""
    out = []
    for n, ln in ent["pre"]:
        s = ln.strip()
        if not s or re.match(r"^#(?!#)\s", s):
            continue
        m = re.match(r"^([A-Za-zÀ-ÿ_]+)\s*:", s)
        if m and sem_acento(m.group(1)).lower() in CHAVES:
            continue
        out.append((n, ln))
    return out


def secao(ent, titulo):
    for s in ent["secoes"]:
        if s["titulo"] == titulo:
            return s
    return None


def celulas(ln):
    ln = ln.strip().replace("\\|", "\x00")
    if ln.startswith("|"):
        ln = ln[1:]
    if ln.endswith("|"):
        ln = ln[:-1]
    return [c.replace("\x00", "|").strip() for c in ln.split("|")]


def eh_separador(cels):
    return all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) for c in cels) and cels


def tabela(sec):
    """Todas as linhas de tabela da secao: (cabecalho, [(linha, celulas)], linhas_da_tabela).

    A primeira linha iniciada por '|' e o cabecalho. Toda outra linha iniciada
    por '|' entra como linha de dados, mesmo depois de linha em branco, de
    texto ou de subtitulo; so o separador e a repeticao exata do cabecalho
    (segunda tabela) ficam de fora."""
    cab, rows, usadas = None, [], set()
    for n, ln in sec["linhas"]:
        if not ln.lstrip().startswith("|"):
            continue
        cels = celulas(ln)
        usadas.add(n)
        if cab is None:
            cab = cels
        elif eh_separador(cels) or [c.lower() for c in cels] == [c.lower() for c in cab]:
            continue
        else:
            rows.append((n, cels))
    return cab, rows, usadas


# ---------------------------------------------------------------- numeros
RE_REF = re.compile(r"\b[FN]\d+\b|#\d+")
RE_DATAS = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}/\d{4}")
RE_COLADO = re.compile(r"\b[A-Za-z][A-Za-z\-]*\d[\w.]*")
RE_LISTA = re.compile(r"^\s*(?:[-*>]\s+)?\d+[.)]\s")
RE_NUM = re.compile(
    r"(R\$\s*)?(\d+(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?|\d+\.\d+)"
    r"(?:\s*((?i:milh[ãa]o|milh[õo]es|bilh[ãa]o|bilh[õo]es|mil|mi|bi)|[kK]|M)(?![\wÀ-ÿ]))?(\s*%)?")
MULT = {"mil": 1e3, "k": 1e3, "mi": 1e6, "m": 1e6, "milhao": 1e6, "milhoes": 1e6,
        "bi": 1e9, "bilhao": 1e9, "bilhoes": 1e9}


def numeros(texto):
    """Lista de (texto_do_numero, valor) que contam como numero de prosa."""
    t = RE_LISTA.sub("", texto)
    t = RE_URL.sub(" ", t)
    t = RE_DATAS.sub(" ", t)
    t = RE_REF.sub(" ", t)
    t = RE_COLADO.sub(" ", t)
    out = []
    for m in RE_NUM.finditer(t):
        bruto = m.group(2)
        valor = float(bruto.replace(".", "").replace(",", ".")) \
            if re.search(r",|\.\d{3}\b", bruto) else float(bruto)
        if m.group(3):
            valor *= MULT[sem_acento(m.group(3)).lower()]
        elif re.fullmatch(r"(19|20)\d\d", bruto) and not m.group(1) and not m.group(4):
            continue
        out.append((m.group(0).strip(), valor))
    return out


def valida(texto, nome):
    ent = parse_entrega(texto)
    msgs = []

    def erro(n, m):
        msgs.append(f"{nome}:{n}: {m}")

    for k in CHAVES:
        if not ent["header"].get(k):
            erro(1, f"cabeçalho sem a chave '{k}:'")
    h = ent["header"]
    if h.get("tamanho") and not re.fullmatch(r"E[0-3]", h["tamanho"]):
        erro(1, f"tamanho '{h['tamanho']}' fora de E0 a E3")
    if h.get("eleitoral") and sem_acento(h["eleitoral"]).lower() not in ("sim", "nao"):
        erro(1, f"eleitoral '{h['eleitoral']}' deve ser sim ou não")
    if h.get("data") and not (re.fullmatch(r"\d{4}-\d{2}-\d{2}", h["data"]) and data_valida(h["data"])):
        erro(1, f"data '{h['data'][:40]}' do cabeçalho deve ser uma data AAAA-MM-DD válida, e só ela")
    titulos_h1 = [n for n, ln in ent["pre"] if re.match(r"^#(?!#)\s", ln.strip())]
    for n in titulos_h1[1:]:
        erro(n, "mais de uma linha de título '# ...' antes da primeira seção (só uma é aceita)")

    for n, ln in linhas_fora_de_secao(ent):
        erro(n, f"texto antes da primeira seção (só 'chave: valor' do cabeçalho e título '# ...'): \"{ln.strip()[:80]}\"")

    titulos = [s["titulo"] for s in ent["secoes"]]
    for t in SECOES:
        c = titulos.count(t)
        if c == 0:
            erro(1, f"seção ausente ou com título diferente: '## {t}'")
        elif c > 1:
            erro(1, f"seção repetida: '## {t}'")
    for s in ent["secoes"]:
        if s["titulo"] not in SECOES:
            erro(s["linha"], f"seção '## {s['titulo']}' fora das 8 seções do formato")

    ids = set()
    valores_numeros = set()
    for titulo, cols in (("Fatos", COLS_FATOS), ("Números", COLS_NUMEROS)):
        sec = secao(ent, titulo)
        if sec is None:
            continue
        cab, rows, usadas = tabela(sec)
        for n, ln in sec["linhas"]:
            if ln.strip() and n not in usadas:
                erro(n, f"linha fora da tabela em '## {titulo}' (a seção só aceita a tabela): \"{ln.strip()[:80]}\"")
        if cab is None:
            erro(sec["linha"], f"seção '{titulo}' sem tabela")
            continue
        if [c.lower() for c in cab] != [c.lower() for c in cols]:
            erro(sec["linha"], f"cabeçalho da tabela '{titulo}' deve ser | " + " | ".join(cols) + " |")
            continue
        if not rows:
            erro(sec["linha"], f"tabela '{titulo}' sem nenhuma linha")
        for n, cels in rows:
            if len(cels) != len(cols):
                erro(n, f"linha com {len(cels)} colunas, esperadas {len(cols)}")
                continue
            ident = cels[0]
            if not ident:
                erro(n, "coluna # vazia")
            elif (titulo, ident) in ids:
                erro(n, f"# '{ident}' repetido na tabela {titulo}")
            ids.add((titulo, ident))
            rot, fonte = cels[-2], cels[-1]
            if titulo == "Números":
                for _, v in numeros(cels[1]):
                    valores_numeros.add(v)
            if rot not in ROTULOS:
                erro(n, f"Rótulo inválido '{rot}' (use {', '.join(ROTULOS)})")
                continue
            m = fonte_ok(rot, fonte)
            if m:
                erro(n, f"{m} (linha {ident} da tabela {titulo})")
            if titulo == "Números":
                if not numeros(cels[1]) and not re.search(r"\d", cels[1]):
                    erro(n, f"coluna Número sem valor numérico (linha {ident})")

    # numeros no titulo e nos valores do cabecalho
    for n, txt in prosa_cabecalho(ent):
        for bruto, v in numeros(txt):
            if v not in valores_numeros:
                erro(n, f"número '{bruto}' no cabeçalho ou no título sem linha na tabela Números")

    # numeros na prosa
    for s in ent["secoes"]:
        _, _, usadas = tabela(s) if s["titulo"] in ("Fatos", "Números") else (None, None, set())
        cab_outra = None
        for n, ln in s["linhas"]:
            if n in usadas or not ln.strip():
                continue
            if ln.lstrip().startswith("|"):
                cels = celulas(ln)
                if eh_separador(cels):
                    continue
                if cab_outra is None:
                    cab_outra = cels
                if cab_outra and cab_outra[0] == "#":
                    ln = " | ".join(cels[1:])
            for bruto, v in numeros(ln):
                if v not in valores_numeros:
                    erro(n, f"número '{bruto}' na prosa de '{s['titulo']}' sem linha na tabela Números")
    return msgs


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        print("uso: rotular.py <entrega.md>")
        print("Confere a FORMA da entrega (cabeçalho, seções, rótulo e fonte por linha,")
        print("número da prosa na tabela Números). NÃO confere verdade: fonte inventada")
        print("com a forma certa passa. A verdade é o portão 2.")
        return 0 if argv and argv[0] in ("-h", "--help") else 2
    p = Path(argv[0])
    if not p.is_file():
        print(f"{p}: arquivo não encontrado")
        return 2
    try:
        texto = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"{p}: não consegui ler ({e.__class__.__name__})")
        return 2
    msgs = valida(texto, p.name)
    for m in msgs:
        print(m)
    if msgs:
        print(f"REPROVADO: {len(msgs)} problema(s) de forma. (Isto confere forma, não verdade.)")
        return 1
    print("OK: forma conferida (não a verdade).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
