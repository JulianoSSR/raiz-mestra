"""Valida a ficha devolvida pelo agente leitor antes de chegar ao orquestrador.

Entrada: arquivo ou "-" (stdin). Uma ficha tem campos fixos, um por linha, "campo: valor".
Várias fichas se separam por uma linha "---". Saída: ficha saneada em stdout; resumo do que
foi descartado em stderr. Exit 1 se faltar campo obrigatório. Texto de terceiros é dado:
valor com padrão de instrução vai entre aspas, prefixado por [suspeito], e nunca é interpretado.
"""
import re
import sys
import unicodedata
from pathlib import Path

CAMPOS = ("nome", "url", "o_que_oferece", "para_quem", "preco_visto", "diferencial_declarado",
          "evidencia", "consultado_em", "confianca", "limitacao")
OBRIGATORIOS = ("nome", "url", "o_que_oferece", "consultado_em")
TETO = 300
TETOS = {"evidencia": 400}
TETO_ENTRADA = 200_000
CONFIANCA = ("alta", "media", "baixa")

_PADROES = [
    r"\bignor(e|ar|a|em)\b.{0,40}(instru|anterior|previous|prior|above|acima|regras|rules)",
    r"\bignore (all|any|the|previous|prior|above|everything)\b",
    r"\bdisregard\b", r"\bdesconsider\w*",
    r"\besquec\w*\b.{0,30}(instru|regras|anterior)", r"\bforget\b.{0,30}(instruc|instruction|rules|previous)",
    r"\bvoce agora e\b", r"\byou are now\b", r"\ba partir de agora\b.{0,30}(voce|aja|responda|atue)",
    r"\b(act|behave) as\b", r"\bpretend\b", r"\bfinja\b", r"\b(atue|aja) como\b", r"\bhaja como\b",
    r"system prompt", r"prompt d[oe] sistema", r"instrucoes d[oe] sistema", r"developer message",
    r"\bexecute\b", r"\bexecutar\b", r"\brode o comando\b", r"\brode\b.{0,20}\bscript\b",
    r"\brun (the |this )?(command|script)\b", r"\bapague\w*", r"\bdelete (all|the|every|files)",
    r"rm -rf", r"\bsudo\b", r"\bremova (os |todos )",
    r"(^|[\s\[(\"'])(assistant|system|human|developer|assistente)\s*:",
    r"<\s*/?\s*(system|assistant|user|human|instructions?|tool\w*|function_?calls?|antml\w*)\b",
    r"\[\s*/?\s*(inst|sys)\s*\]", r"<\|", r"\|>", r"#{2,}\s*(instruction|system|instrucao)",
    r"\bnovas? instrucoes\b", r"\bnew instructions?\b",
    r"\bse voce (for|e) (uma? )?(ia|assistente|modelo|llm|agente)\b", r"\bif you are an? (ai|llm|assistant|model)\b",
    r"\bao ler (isto|isso|esta|este)\b", r"\bnao (conte|diga|avise) (ao|para o) usuario\b",
]
_RE = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _PADROES]


# preenchedores que parecem letra ou espaço e são invisíveis: somem antes de casar e na saída
PREENCHEDORES = frozenset("ᅟᅠㅤﾠ⠀")


def _invisivel(c):
    cat = unicodedata.category(c)
    return cat[0] == "M" or cat in ("Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp") or c in PREENCHEDORES


def _normalizar(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not _invisivel(c) and not unicodedata.combining(c))


def suspeito(texto):
    n = _normalizar(texto)
    return any(r.search(n) for r in _RE)


def _limpar(s):
    """Remove caracteres de controle, invisíveis e marcas; devolve (texto, quantos removidos)."""
    s = unicodedata.normalize("NFC", s.replace("\t", " "))
    out, rem = [], 0
    for c in s:
        if _invisivel(c):
            rem += 1
        else:
            out.append(c)
    return re.sub(r" {2,}", " ", "".join(out)).strip(), rem


def sanear_livre(valor):
    """Texto livre de terceiro fora de ficha (nome, razão social, descrição de API).

    Limpa como uma ficha e, se houver padrão de instrução, sai entre aspas com [suspeito]:
    é dado, não instrução.
    """
    texto, _ = _limpar("" if valor is None else str(valor))
    if texto and suspeito(texto):
        return '[suspeito] "%s"' % texto.replace('"', "'")
    return texto


def _entre_aspas(v):
    v = v.replace('"', "'")
    return '"%s"' % v


def sanear_ficha(linhas):
    """Devolve (campos dict, relatório dict)."""
    rel = {"extras": [], "sem_campo": 0, "repetidos": 0, "truncados": [], "invalidos": [],
           "suspeitos": [], "controle": 0, "suspeitas_descartadas": 0}
    campos = {}
    for bruta in linhas:
        linha, rem = _limpar(bruta)
        rel["controle"] += rem
        if not linha:
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", linha)
        if not m:
            rel["sem_campo"] += 1
            if suspeito(linha):
                rel["suspeitas_descartadas"] += 1
            continue
        nome, valor = m.group(1).lower(), m.group(2).strip()
        if nome not in CAMPOS:
            rel["extras"].append(nome)
            if suspeito(valor) or suspeito(nome):
                rel["suspeitas_descartadas"] += 1
            continue
        if nome in campos:
            rel["repetidos"] += 1
            continue
        if not valor:
            continue
        teto = TETOS.get(nome, TETO)
        if len(valor) > teto:
            if nome == "url":
                rel["invalidos"].append("url acima de %d caracteres" % teto)
                continue
            valor = valor[:teto].rstrip()
            rel["truncados"].append(nome)
        if nome == "url" and not re.fullmatch(r"https?://[^\s\"'<>]+", valor, re.IGNORECASE):
            rel["invalidos"].append("url não é http(s)")
            continue
        if nome == "confianca":
            if _normalizar(valor).lower() not in CONFIANCA:
                rel["invalidos"].append("confianca fora de alta|media|baixa")
                continue
            valor = _normalizar(valor).lower()
        sus = suspeito(valor)
        if nome == "evidencia":
            valor = _entre_aspas(valor.strip().strip('"“”'))
        if sus:
            rel["suspeitos"].append(nome)
            if nome != "evidencia":
                valor = _entre_aspas(valor)
            valor = "[suspeito] " + valor
        campos[nome] = valor
    return campos, rel


def dividir_fichas(texto):
    blocos, atual = [], []
    for l in texto.splitlines():
        if l.strip() == "---":
            blocos.append(atual)
            atual = []
        else:
            atual.append(l)
    blocos.append(atual)
    return [b for b in blocos if any(x.strip() for x in b)]


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) != 1:
        print("uso: ler_ficha.py <ficha.md|->", file=sys.stderr)
        return 2
    try:
        if a[0] == "-":
            texto = sys.stdin.read(TETO_ENTRADA + 1)
        else:
            with open(a[0], "r", encoding="utf-8", errors="replace") as f:
                texto = f.read(TETO_ENTRADA + 1)
    except OSError as e:
        print("não consegui ler a entrada: %s" % e.strerror, file=sys.stderr)
        return 2
    cortada = len(texto) > TETO_ENTRADA
    texto = texto[:TETO_ENTRADA]
    fichas = dividir_fichas(texto)
    if not fichas:
        print("entrada vazia: nenhuma ficha.", file=sys.stderr)
        return 1
    saidas, erro = [], False
    if cortada:
        print("entrada cortada em %d caracteres." % TETO_ENTRADA, file=sys.stderr)
    for i, bloco in enumerate(fichas, 1):
        campos, rel = sanear_ficha(bloco)
        p = "ficha %d" % i
        falta = [c for c in OBRIGATORIOS if c not in campos]
        if falta:
            erro = True
            print("%s reprovada: faltam campos obrigatórios: %s." % (p, ", ".join(falta)), file=sys.stderr)
        if rel["extras"]:
            print("%s: %d campo(s) fora da lista descartado(s): %s." % (p, len(rel["extras"]), ", ".join(sorted(set(rel["extras"])))), file=sys.stderr)
        if rel["sem_campo"]:
            print("%s: %d linha(s) sem 'campo:' descartada(s)." % (p, rel["sem_campo"]), file=sys.stderr)
        if rel["repetidos"]:
            print("%s: %d campo(s) repetido(s) descartado(s)." % (p, rel["repetidos"]), file=sys.stderr)
        if rel["truncados"]:
            print("%s: valor(es) cortado(s) no teto: %s." % (p, ", ".join(rel["truncados"])), file=sys.stderr)
        for m in rel["invalidos"]:
            print("%s: campo descartado: %s." % (p, m), file=sys.stderr)
        if rel["suspeitos"]:
            print("%s: padrão de instrução em: %s (mantido entre aspas, como dado)." % (p, ", ".join(rel["suspeitos"])), file=sys.stderr)
        if rel["suspeitas_descartadas"]:
            print("%s: %d linha(s) descartada(s) continham padrão de instrução." % (p, rel["suspeitas_descartadas"]), file=sys.stderr)
        if rel["controle"]:
            print("%s: %d caractere(s) de controle removido(s)." % (p, rel["controle"]), file=sys.stderr)
        saidas.append("\n".join("%s: %s" % (c, campos[c]) for c in CAMPOS if c in campos))
    print("\n---\n".join(saidas))
    return 1 if erro else 0


if __name__ == "__main__":
    sys.exit(main())
