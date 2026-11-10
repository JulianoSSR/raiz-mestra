#!/usr/bin/env python3
"""lint_entrega.py <entrega.md> [--pesquisa <arquivo-ou-pasta>]...

Varre a entrega inteira e reprova:
  (a) percentual ou expressao de adocao ("a maioria", "vao comprar", "taxa de
      adocao", "3 em cada 10"...) na mesma linha de tabela de um item
      [simulacao]/[hipotese], ou em frase fora das tabelas que mencione um
      desses rotulos ou que nao aponte para linha [usuario]/[publico] (por id,
      ex.: F1, N2);
  (b) frase normativa juridica/fiscal/contabil fora de "Perguntas para o
      profissional";
  (c) trecho de 8 ou mais palavras igual a arquivo de --pesquisa, a menos que
      esteja entre aspas e seguido de fonte;
  (d) secoes "O que isto nao prova" e "Limites desta analise" ausentes ou vazias;
  (e) com `eleitoral: sim`: recomendacao de candidatura/voto, percentual de
      voto ou de intencao, texto de campanha sem "[conteudo gerado por IA]"
      (eleitoral ausente ou invalido e tratado como sim);
  (g) com `eleitoral: sim`: segmentacao ou perfilamento por opiniao politica
      individual ("eleitores de <partido>", "lista de simpatizantes", "quem
      votou em", "perfil ideologico de cada", "microdirecionamento",
      "segmentar por posicao politica");
  (f) com `tamanho: E3`: recomendacao em qualquer secao, menos "Perguntas",
      'nao prova' e "Limites", sem linha [usuario] em Fatos cuja Fonte cite
      "coleta:";
  (h) texto entre o cabecalho e a primeira secao (so `chave: valor` do
      cabecalho, titulo `# ...` e linhas vazias sao aceitos ali).

Heuristicas por lista de padroes. Declaradamente NAO pega:
  - adocao ou norma dita com palavras fora das listas (ex.: "o mercado vai
    abracar", "so quem tem CNPJ pode vender"), por extenso ("trinta por cento"),
    em ingles, ou com sinonimos raros;
  - percentual sem o sinal % ou "por cento";
  - em (a), frase em secao 'nao prova'/'Limites' que traga negacao ("nao
    prova", "nao ha"...) e sem rotulo e aceita: pode esconder afirmacao;
  - em (a), o ponteiro F1/N2 e conferido so pela existencia e pelo rotulo da
    linha, nao por a linha dizer aquilo;
  - em (c), parafrase, traducao ou 7 palavras iguais; copia de fonte nao passada
    em --pesquisa; aspas com "fonte" falsa;
  - em (e), recomendacao implicita, "voto" disfarçado, texto de campanha que nao
    use as palavras-gatilho (texto/peca/mensagem/post/slogan... de campanha);
    o marcador so precisa estar no mesmo paragrafo ou no seguinte;
  - em (g), segmentacao dita com palavras fora da lista (ex.: "separar o
      publico por orientacao", "base de apoiadores do deputado", "cadastro de
      simpatia"), por extenso em outra lingua ou em imagem; "eleitores de" so e
      pego quando seguido de partido/candidato/sigla conhecida; em 'nao
      prova'/'Limites' a linha com negacao ("nao", "sem", "proibido") e aceita
      e pode esconder afirmacao; nao distingue dado agregado de individual
      alem das palavras-gatilho;
  - em (f), recomendacao sem verbo das listas; "coleta:" e conferido como texto,
    nao como registro real.
Prefere falso positivo a falso negativo em (a).

Saida: 0 aprovado, 1 reprovado, 2 uso errado.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rotular  # noqa: E402
from rotular import sem_acento  # noqa: E402

SEC_NAO_PROVA = "O que isto não prova"
SEC_LIMITES = "Limites desta análise"
SEC_PERGUNTAS = "Perguntas para o profissional"
MARCA_IA = "[conteúdo gerado por IA]"

# ---- (a) -------------------------------------------------------------
RE_PERCENT = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|por cento|pontos? percentuais?|p\.p\.)", re.I)
_NUM = r"(?:\d+|um|uma|dois|duas|tres|quatro|cinco|seis|sete|oito|nove|dez)"
ADOCAO = [
    r"\ba maioria\b", r"\bmaioria d[aeo]s?\b", r"\bmetade d[aeo]s?\b",
    r"\bquase todos?\b", r"\btodos (?:vao|querem|compram|pagam|usam)\b",
    r"\bninguem (?:vai|vao|quer|compra|paga)\b",
    r"\b(?:grande|boa|maior) parte d[aeo]s?\b",
    r"\b(?:vao|vai|irao|ira) (?:comprar|pagar|aderir|usar|adotar|assinar|contratar|vender|funcionar|crescer)\b",
    r"\b(?:comprariam|pagariam|adeririam|adotariam|assinariam|contratariam|usariam)\b",
    r"\bvai dar (?:certo|errado)\b", r"\bvao dar certo\b", r"\bsucesso garantido\b",
    r"\bdemanda garantida\b", r"\bcom certeza (?:vai|vao|compr|pag)\w*",
    r"\btaxa de (?:adocao|conversao|aceitacao|aderencia|retencao|churn|sucesso|compra)\b",
    r"\bpenetracao de mercado\b", r"\bmarket share\b",
    rf"\b{_NUM} (?:em|a) cada {_NUM}\b", rf"\b{_NUM} (?:em|a) cada \w+\b",
    r"\bum em cada\b", r"\b(?:muitos|varios|poucos) (?:clientes|consumidores|moradores|pessoas) (?:vao|vai|iriam|comprariam|pagariam)\b",
]
RE_ADOCAO = [re.compile(p) for p in ADOCAO]
RE_REF = re.compile(r"\b([FN])(\d+)\b|#(\d+)")
RE_NEGA = re.compile(r"\bnao (?:prova|provam|permite|permitem|mostra|mostram|mede|medem|indica|indicam|autoriza|sustenta|ha|existe|se sabe)\b|\bsem (?:dado|evidencia|base)\b")

# ---- (b) -------------------------------------------------------------
_V = r"(?:registrar|abrir|emitir|declarar|recolher|pagar|contratar|formalizar|constituir|enquadrar|optar|tributar|reter|escriturar|prestar contas)"
NORMATIVO = [
    rf"\bvoce (?:deve|precisa|tem que|tem de) {_V}\b", rf"\b(?:deve|devem|precisa|precisam|tem que|tem de) (?:ser )?(?:registrad|declarad|recolhid|emitid|tributad|formalizad|abert)\w*",
    rf"\b(?:deve|devem|tem que|tem de) {_V}\b",
    r"\be obrigatori[oa]\b", r"\bsao obrigatori[oa]s?\b", r"\bobrigatoriedade de\b",
    r"\bobrigad[oa]s? a\b", r"\ba lei (?:exige|determina|obriga|manda|estabelece|preve|proibe|permite)\b",
    r"\b(?:lei|legislacao|norma|receita|fisco) (?:exige|determina|obriga|manda|proibe)\b",
    r"\bbasta (?:abrir|ter|registrar|emitir|fazer|ser) (?:um|uma|o|a)? ?(?:mei|cnpj|empresa|registro|nota|cooperativa|associacao)\b",
    r"\bbasta abrir\b", r"\bnao precisa (?:de|pagar|emitir|registrar|declarar|abrir|ter) (?:alvara|licenca|registro|cnpj|nota|imposto|tributo|contador)?",
    r"\b(?:esta|voce e|e) isent[oa]s?\b", r"\bpode deixar de (?:pagar|declarar|emitir|registrar)\b",
    r"\bnao (?:ha|existe) obrigacao\b", r"\bsujeit[oa]s? a tributacao\b",
    r"\be (?:legal|ilegal|permitido|proibido|licito|ilicito)\b",
    r"\bo correto e (?:registrar|declarar|abrir|emitir|pagar)\b",
    r"\bvoce pode (?:deduzir|abater|enquadrar|descontar|compensar)\b",
    r"\benquadra-se (?:no|como|na)\b", r"\be dedutivel\b", r"\bdevera (?:ser )?(?:registrad|declarad|recolh|emitid)\w*",
]
RE_NORMATIVO = [re.compile(p) for p in NORMATIVO]

# ---- (e) -------------------------------------------------------------
CANDIDATURA = [
    r"\brecomend\w* (?:a |o |uma |um )?(?:candidat\w*|voto|votar)\b", r"\brecomend\w* (?:que )?(?:vote|votem|se candidate)",
    r"\b(?:vote|votem|votar) (?:em|no|na|nos|nas)\b", r"\bvoto (?:em|no|na)\b",
    r"\b(?:deve|devem|deveria|deveriam) (?:se )?(?:candidat|votar|apoiar|eleger)\w*",
    r"\bmelhor candidat\w*", r"\bcandidat\w* (?:ideal|mais indicad\w*|que deve|ideal)\b",
    r"\bcandidate-se\b", r"\bapoie (?:o|a) candidat\w*", r"\blance(?:m)? (?:a |sua )?candidatura\b",
    r"\bvale a pena (?:se )?candidat\w*", r"\belej[ao]\b", r"\bseria (?:um|o) bom candidat\w*",
    r"\bapoi(?:e|em|ar) (?:o|a) (?:candidat|partid)\w*",
    r"\bvai ganhar\b", r"\bser[ao] eleit[oa]s?\b", r"\bvencer[ao]? a eleicao\b",
]
RE_CAND = [re.compile(p) for p in CANDIDATURA]
RE_PCT_VOTO_CTX = re.compile(r"\b(?:voto|votos|votar|eleitor\w*|intencao|candidat\w*|eleicao|eleicoes|urna|sufragio|pesquisa eleitoral|aprovacao)\b")
RE_VOTOS_QTD = re.compile(r"\b\d[\d.,]*\s+(?:mil )?votos\b|\bintencao de voto\b")
RE_CAMPANHA = re.compile(r"\b(?:texto|peca|mensagem|post|panfleto|material|slogan|jingle|santinho|discurso|video|anuncio|propaganda)s? (?:de|da|para a) campanha\b|\bslogan\b|\bsantinho\b|\bjingle\b")
RE_FONTE_APOS = re.compile(r"fonte\s*:|https?://|\bfonte\b|\b[FN]\d+\b|\(\s*(?:[A-Z][\w ]+,?\s*)?\d{4}\s*\)")

# ---- (f) -------------------------------------------------------------
RE_RECOMENDA = re.compile(
    r"\brecomend\w*|\bsugir\w*|\bsugerimos\b|\brecomenda-se\b|\bdeve(?:m|mos)?\b|\bdeveria\w*|\binvist\w*|\binvista\b"
    r"|\blance\b|\blancar\b|\baposte\b|\bapostar\b|\bvale a pena\b|\bcontrate\b|\badote\b|\bpriorize\b"
    r"|\bescolha\b|\bo ideal e\b|\bo melhor (?:caminho|e)\b|\bcomece por\b|\bfaca\b|\bavance\b|\bsiga com\b|\bconstrua\b|\bproduza\b")
# ---- (g) -------------------------------------------------------------
SEGMENTACAO = [
    r"\beleitor(?:es|a|as)? d[aeo]s? (?:partido|candidat\w*|siglas?|pt|pl|psdb|mdb|psol|pp|psd|pdt|psb|novo|uniao brasil|republicanos)\b",
    r"\blistas? de (?:simpatizantes|apoiadores|eleitores|filiados)\b", r"\bcadastro de (?:simpatizantes|apoiadores|eleitores)\b",
    r"\bquem votou (?:em|no|na|nos|nas)\b", r"\bperf(?:il|is) ideologic\w* de cada\b",
    r"\bmicro-?direcionamento\b", r"\bmicro-?segmentacao\b",
    r"\bsegment\w* (?:por|pela|pelo|segundo|conforme) (?:a |o )?(?:opiniao|posicao|orientacao|preferencia|inclinacao|afinidade) (?:politic|partidari|ideologic|eleitoral)\w*",
    r"\bsegment\w* (?:por|pela|pelo) (?:partido|ideologia)\b",
    r"\bperfil\w* (?:individual|de cada eleitor)\w*",
]
RE_SEG = [re.compile(p) for p in SEGMENTACAO]
RE_NEGA_SEG = re.compile(r"\bnao\b|\bsem\b|\bproibid\w*|\bvedad\w*|\bnunca\b")
RE_COLETA = re.compile(r"coleta\s*:", re.I)

EXEMPLO = lambda s: s if len(s) <= 90 else s[:87] + "..."


def frases(texto):
    return [f.strip() for f in re.split(r"(?<=[.!?;])\s+(?=[A-ZÀ-Ý0-9\[(\"“])", texto) if f.strip()]


def blocos(sec):
    """Blocos de prosa da secao: (linha, texto) por paragrafo/item.

    Linha de tabela vira bloco proprio (celulas unidas por espaco), exceto as
    linhas de Fatos/Numeros que a tabela da secao ja cobre em linhas_tabela."""
    out, buf, ini = [], [], None
    cobertas = set()
    if sec["titulo"] in ("Fatos", "Números"):
        _, rows, _ = rotular.tabela(sec)
        cobertas = {n for n, cels in rows if len(cels) >= 4}

    def fecha():
        nonlocal buf, ini
        if buf:
            out.append((ini, " ".join(buf)))
        buf, ini = [], None

    for n, ln in sec["linhas"]:
        s = ln.strip()
        if s.startswith("|"):
            fecha()
            cels = rotular.celulas(s)
            if n in cobertas or rotular.eh_separador(cels):
                continue
            out.append((n, " ".join(c for c in cels if c)))
            continue
        if not s or re.fullmatch(r"[-*_]{3,}", s):
            fecha()
            continue
        if re.match(r"^([-*>]|\d+[.)])\s", s):
            fecha()
        if ini is None:
            ini = n
        buf.append(s)
    fecha()
    return out


def contexto_eleitoral(ent):
    v = sem_acento(ent["header"].get("eleitoral", "")).strip().lower()
    return v != "nao"


def ids_rotulos(ent):
    """Mapa de ponteiros (F1, N2, #1...) para rotulo; e rotulos das linhas."""
    mapa = {}
    for titulo, pref in (("Fatos", "F"), ("Números", "N")):
        sec = rotular.secao(ent, titulo)
        if not sec:
            continue
        cab, rows, _ = rotular.tabela(sec)
        if cab is None:
            continue
        for _, cels in rows:
            if len(cels) < 4:
                continue
            ident = cels[0].strip()
            rot = cels[-2].strip()
            num = re.sub(r"^[FN]", "", ident)
            mapa.setdefault(pref + num, set()).add(rot)
            mapa.setdefault(ident, set()).add(rot)
            mapa.setdefault("#" + num, set()).add(rot)
    return mapa


def linhas_tabela(ent):
    """(titulo, linha, celulas, rotulo, fonte) das linhas validas das duas tabelas."""
    out = []
    for titulo in ("Fatos", "Números"):
        sec = rotular.secao(ent, titulo)
        if not sec:
            continue
        cab, rows, _ = rotular.tabela(sec)
        if cab is None:
            continue
        for n, cels in rows:
            if len(cels) >= 4:
                out.append((titulo, n, cels, cels[-2].strip(), cels[-1].strip()))
    return out


def gatilhos_adocao(texto):
    t = sem_acento(texto).lower()
    achados = []
    m = RE_PERCENT.search(texto)
    if m:
        achados.append(m.group(0))
    for r in RE_ADOCAO:
        m = r.search(t)
        if m:
            achados.append(m.group(0))
    return achados


def lint_a(ent, nome, msgs):
    mapa = ids_rotulos(ent)
    for titulo, n, cels, rot, _ in linhas_tabela(ent):
        if rot in ("[simulação]", "[hipótese]"):
            g = gatilhos_adocao(" | ".join(cels[1:]))
            if g:
                msgs.append(f"{nome}:{n}: (a) '{g[0]}' em linha {rot} da tabela {titulo}: percentual/adoção não pode vir de simulação ou hipótese")
    for s in ent["secoes"]:
        tolera = s["titulo"] in (SEC_NAO_PROVA, SEC_LIMITES)
        for n, bloco in blocos(s):
            for fr in frases(bloco):
                g = gatilhos_adocao(fr)
                if not g:
                    continue
                refs = set()
                for m in RE_REF.finditer(fr):
                    k = (m.group(1) + m.group(2)) if m.group(1) else "#" + m.group(3)
                    if k in mapa:
                        refs |= mapa[k]
                tem_simhip = bool(re.search(r"\[(?:simulação|hipótese)\]", fr)) or bool(refs & {"[simulação]", "[hipótese]"})
                ok_ref = bool(refs & {"[usuário]", "[público]"})
                if tolera and RE_NEGA.search(sem_acento(fr).lower()) and not tem_simhip:
                    continue
                if tem_simhip:
                    msgs.append(f"{nome}:{n}: (a) '{g[0]}' ligado a item [simulação]/[hipótese]: \"{EXEMPLO(fr)}\"")
                elif not ok_ref:
                    msgs.append(f"{nome}:{n}: (a) '{g[0]}' sem apontar para linha [usuário] ou [público] (use F1/N2): \"{EXEMPLO(fr)}\"")


def lint_b(ent, nome, msgs):
    for s in ent["secoes"]:
        if s["titulo"] == SEC_PERGUNTAS:
            continue
        for n, ln in s["linhas"]:
            t = sem_acento(ln).lower()
            for r in RE_NORMATIVO:
                m = r.search(t)
                if m:
                    msgs.append(f"{nome}:{n}: (b) frase normativa jurídica/fiscal fora de '{SEC_PERGUNTAS}' ('{m.group(0).strip()}'): vire pergunta ao profissional")
                    break


def carregar_pesquisa(caminhos):
    textos = {}
    for c in caminhos:
        p = Path(c)
        arqs = [p] if p.is_file() else sorted(q for q in p.rglob("*") if q.is_file() and q.suffix.lower() in (".md", ".txt", ".json", ".html", ".csv"))
        for a in arqs:
            try:
                textos[a.name] = a.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
    return textos


def palavras(texto):
    return [(m.group(0).lower(), m.start(), m.end()) for m in re.finditer(r"\w+", texto)]


def lint_c(texto, nome, pesquisa, msgs):
    K = 8
    grams = {}
    for arq, t in pesquisa.items():
        w = [x[0] for x in palavras(t)]
        for i in range(len(w) - K + 1):
            grams.setdefault(tuple(w[i:i + K]), arq)
    if not grams:
        return
    ws = palavras(texto)
    i, runs = 0, []
    while i <= len(ws) - K:
        g = tuple(x[0] for x in ws[i:i + K])
        if g in grams:
            j = i
            arq = grams[g]
            while j + 1 <= len(ws) - K and tuple(x[0] for x in ws[j + 1:j + 1 + K]) in grams:
                j += 1
            runs.append((ws[i][1], ws[j + K - 1][2], arq))
            i = j + K
        else:
            i += 1
    for ini, fim, arq in runs:
        ls = texto.rfind("\n", 0, ini) + 1
        le = texto.find("\n", fim)
        le = len(texto) if le < 0 else le
        linha = texto[ls:le]
        a, b = ini - ls, fim - ls
        aspas = '"“”'
        esq = max((linha.rfind(q, 0, a) for q in aspas))
        dir_ = min((p for p in (linha.find(q, b) for q in aspas) if p >= 0), default=-1)
        citado = False
        if esq >= 0 and dir_ >= 0 and not any(q in linha[esq + 1:a] for q in aspas) \
                and not any(q in linha[b:dir_] for q in aspas):
            abre = sum(linha[:esq].count(q) for q in aspas) % 2 == 0
            if abre and RE_FONTE_APOS.search(linha[dir_ + 1:dir_ + 140]):
                citado = True
        if not citado:
            n = texto.count("\n", 0, ini) + 1
            msgs.append(f"{nome}:{n}: (c) trecho copiado de '{arq}' sem aspas e fonte: \"{EXEMPLO(texto[ini:fim])}\"")


def lint_d(ent, nome, msgs):
    for t in (SEC_NAO_PROVA, SEC_LIMITES):
        s = rotular.secao(ent, t)
        if s is None:
            msgs.append(f"{nome}:1: (d) seção '{t}' ausente")
            continue
        corpo = " ".join(ln for _, ln in s["linhas"])
        if len(re.findall(r"\w{2,}", re.sub(r"\b(?:n/?a|todo|tbd)\b", "", corpo, flags=re.I))) < 3:
            msgs.append(f"{nome}:{s['linha']}: (d) seção '{t}' vazia")


def paragrafos(texto):
    out, buf, ini = [], [], None
    for n, ln in enumerate(texto.splitlines(), 1):
        if ln.strip():
            if ini is None:
                ini = n
            buf.append(ln)
        elif buf:
            out.append((ini, "\n".join(buf)))
            buf, ini = [], None
    if buf:
        out.append((ini, "\n".join(buf)))
    return out


def lint_e(ent, texto, nome, msgs):
    for n, ln in enumerate(texto.splitlines(), 1):
        t = sem_acento(ln).lower()
        if ln.lstrip().startswith("|") and re.match(r"^\|?\s*-", ln.strip()):
            continue
        for r in RE_CAND:
            m = r.search(t)
            if m:
                msgs.append(f"{nome}:{n}: (e) recomendação de candidatura ou voto ('{m.group(0)}'): proibido no modo eleitoral")
                break
        if (RE_PERCENT.search(ln) and RE_PCT_VOTO_CTX.search(t)) or RE_VOTOS_QTD.search(t):
            msgs.append(f"{nome}:{n}: (e) percentual/contagem de voto ou de intenção de voto: proibido no modo eleitoral")
    ps = paragrafos(texto)
    for k, (n, p) in enumerate(ps):
        if RE_CAMPANHA.search(sem_acento(p).lower()):
            vizinhos = p + "\n" + (ps[k + 1][1] if k + 1 < len(ps) else "")
            if MARCA_IA.lower() not in vizinhos.lower():
                msgs.append(f"{nome}:{n}: (e) texto de campanha sem a marca '{MARCA_IA}' no parágrafo ou no seguinte")


def lint_g(ent, nome, msgs):
    for s in ent["secoes"]:
        tolera = s["titulo"] in (SEC_NAO_PROVA, SEC_LIMITES)
        for n, ln in s["linhas"]:
            t = sem_acento(ln).lower()
            if tolera and RE_NEGA_SEG.search(t):
                continue
            for r in RE_SEG:
                m = r.search(t)
                if m:
                    msgs.append(f"{nome}:{n}: (g) segmentação por opinião política individual ('{m.group(0)}'): proibido no modo eleitoral, só agregado de fonte pública")
                    break


def lint_f(ent, nome, msgs):
    if ent["header"].get("tamanho", "").strip().upper() != "E3":
        return
    tem_coleta = any(titulo == "Fatos" and rot == "[usuário]" and RE_COLETA.search(fonte)
                     for titulo, _, _, rot, fonte in linhas_tabela(ent))
    if tem_coleta:
        return
    for s in ent["secoes"]:
        if s["titulo"] in (SEC_PERGUNTAS, SEC_NAO_PROVA, SEC_LIMITES):
            continue
        for n, ln in s["linhas"]:
            m = RE_RECOMENDA.search(sem_acento(ln).lower())
            if m:
                msgs.append(f"{nome}:{n}: (f) tamanho E3 com recomendação em '{s['titulo']}' ('{m.group(0)}') sem linha [usuário] em Fatos com Fonte 'coleta:': só perguntas e teste barato")


def lint_h(ent, nome, msgs):
    for n, ln in rotular.linhas_fora_de_secao(ent):
        msgs.append(f"{nome}:{n}: (h) texto antes da primeira seção (fora das seções que o lint confere): \"{EXEMPLO(ln.strip())}\"")


def lint(texto, nome, pesquisa=None):
    ent = rotular.parse_entrega(texto)
    msgs = []
    lint_h(ent, nome, msgs)
    lint_a(ent, nome, msgs)
    lint_b(ent, nome, msgs)
    if pesquisa:
        lint_c(texto, nome, pesquisa, msgs)
    lint_d(ent, nome, msgs)
    if contexto_eleitoral(ent):
        lint_e(ent, texto, nome, msgs)
        lint_g(ent, nome, msgs)
    lint_f(ent, nome, msgs)
    return msgs


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    arq, pesq, i = None, [], 0
    while i < len(argv):
        if argv[i] == "--pesquisa" and i + 1 < len(argv):
            pesq.append(argv[i + 1])
            i += 2
        elif arq is None and not argv[i].startswith("--"):
            arq = argv[i]
            i += 1
        else:
            print("uso: lint_entrega.py <entrega.md> [--pesquisa <arquivo-ou-pasta>]...")
            return 2
    if arq is None:
        print("uso: lint_entrega.py <entrega.md> [--pesquisa <arquivo-ou-pasta>]...")
        return 2
    p = Path(arq)
    if not p.is_file():
        print(f"{p}: arquivo não encontrado")
        return 2
    for q in pesq:
        if not Path(q).exists():
            print(f"{q}: pesquisa não encontrada")
            return 2
    try:
        texto = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"{p}: não consegui ler ({e.__class__.__name__})")
        return 2
    msgs = lint(texto, p.name, carregar_pesquisa(pesq) if pesq else None)
    for m in msgs:
        print(m)
    if msgs:
        print(f"REPROVADO: {len(msgs)} problema(s). (Heurística por padrões: aprovar não prova ausência de defeito.)")
        return 1
    print("OK: nenhum padrão proibido achado (heurística, não garantia).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
