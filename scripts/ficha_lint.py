"""Valida ficha de persona (moldes/ficha.md).

Uso: ficha_lint.py <ficha.md> [--eleitoral]
Saída: 0 aprovada (pode trazer AVISO), 1 reprovada, 2 uso errado.

DECLARADAMENTE NÃO PEGA (o lint ajuda, não garante anonimato):
  - apelido sem tratamento ("o Zé do mercado");
  - profissão rara + cidade pequena fora da lista de capitais e fora do padrão
    "de/em <Palavra Capitalizada>";
  - descrição física;
  - nome próprio que o usuário não listou e que não vem após tratamento;
  - identificação por combinação de detalhes (idade + bairro + hobby + empresa);
  - dado pessoal escrito de jeito incomum (CPF por extenso, e-mail com " arroba ").
Cargo + cidade é detectado de forma larga de propósito: "Secretário de Saúde"
casa como "cargo + cidade" porque "de Saúde" tem o formato "de <Capitalizada>".
Nesse caso a saída é revisar a ficha e marcar identificacao_indireta_revisada: sim.
"""
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pseudonimizar import CPF, EMAIL, TELEFONE  # noqa: E402

CAPITAIS = ("Rio Branco", "Maceió", "Macapá", "Manaus", "Salvador", "Fortaleza",
            "Brasília", "Vitória", "Goiânia", "São Luís", "Cuiabá", "Campo Grande",
            "Belo Horizonte", "Belém", "João Pessoa", "Curitiba", "Recife", "Teresina",
            "Rio de Janeiro", "Natal", "Porto Alegre", "Porto Velho", "Boa Vista",
            "Florianópolis", "São Paulo", "Aracaju", "Palmas")
MUNICIPIO = re.compile(
    r"\b(?:" + "|".join(re.escape(c) for c in CAPITAIS) + r")\b"
    r"|\b(?:de|do|da|em|no|na|por)\s+[^\W\d_]{3,}", re.IGNORECASE)

CARGO = re.compile(
    r"\b(?:prefeit[oa]s?|vereador(?:a|es|as)?|secret[áa]ri[oa]s?|diretor(?:a|es|as)?|"
    r"president[ea]s?|pastor(?:a|es|as)?|padres?|delegad[oa]s?|ju[ií]z(?:a|es|as)?|"
    r"promotor(?:a|es|as)?|s[ií]ndic[oa]s?)\b", re.IGNORECASE)

# Tratamento sem distinção de caixa. Nome: com inicial maiúscula, ou com 3+ letras em
# qualquer caixa ("dona maria"). "dona de" não casa: "de" tem 2 letras e é minúscula.
TRATAMENTO_NOME = re.compile(
    r"\b(?i:dona|seu|dr\.?|dra\.?|sr\.?|sra\.?|srta\.?|prof\.?|profa\.?|doutor|doutora|"
    r"professor|professora)\s+(?:[A-ZÀ-Ý][^\W\d_]+|[^\W\d_]{3,})")

PARTIDOS = re.compile(r"\b(?:PT|PL|PSDB|MDB|PSOL|PSD|PDT|PSB|PCdoB|PV|PP|Republicanos|"
                      r"Podemos|União Brasil)\b")
TERMOS = {
    "política": r"esquerd|direita|bolsonar|petista|lulista|conservador|progressista|"
                r"\bvota(?:r|va|m)?\s+(?:em|no|na)\b|\beleitor(?:a)?\s+d[eao]\b|"
                r"\bvoto\s+(?:em|no|na)\b|\bpartido\b",
    "saúde": r"diabet|hipertens|c[aâ]ncer|depress|ansiedade|\bhiv\b|\baids\b|epilep|"
             r"\basma\b|obesidade|defici[eê]ncia|card[ií]ac|\bavc\b|bipolar|esquizofreni|"
             r"transtorno|doen[çc]a|burnout|\bautis",
    "religião": r"cat[óo]lic|evang[ée]lic|protestante|umbandist|candombl|esp[ií]rita|"
                r"mu[çc]ulman|\bjude|judaic|budist|\bateu|\bateia|adventist|batist|"
                r"pentecostal|jeov[áa]|m[óo]rmon|religi",
}
ELEITOR = re.compile(r"\b(?:eleitor(?:a|es|as)?|votante)\b", re.IGNORECASE)


def _sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", t)
                   if unicodedata.category(c) != "Mn").lower()


def _campo(linhas, nome):
    r = re.compile(r"^\s*[-*]?\s*" + nome + r"\s*:\s*(.*?)\s*$", re.IGNORECASE)
    for l in linhas:
        m = r.match(l)
        if m:
            return m.group(1).strip().strip("`*_\"'").lower()
    return None


def _linhas_com(padrao, linhas):
    return [i + 1 for i, l in enumerate(linhas) if padrao.search(l)]


def validar(texto, eleitoral=False):
    """Devolve (erros, avisos), listas de mensagens."""
    linhas = texto.splitlines()
    erros, avisos = [], []

    def erro(msg, n=None):
        erros.append(("linha %d: " % n if n else "") + msg)

    origem = _campo(linhas, "origem")
    if origem not in ("real", "arquetipo", "arquétipo"):
        erro("campo `origem:` ausente ou diferente de real ou arquetipo.")
    real = origem == "real"

    for nome, pad, rotulo in (("cpf", CPF, "CPF"), ("email", EMAIL, "e-mail"),
                              ("telefone", TELEFONE, "telefone")):
        for n in _linhas_com(pad, linhas):
            erro("%s no texto da ficha; remova." % rotulo, n)

    if real and _campo(linhas, "consentimento") != "sim":
        erro("origem real exige `consentimento: sim`; campo ausente ou diferente de sim.")

    tratamento = _linhas_com(TRATAMENTO_NOME, linhas)
    for n in tratamento:
        erro("tratamento com nome próprio (ex.: dona Maria); use só o papel.", n)
    nome_campo = _campo(linhas, "nome")
    identificada = bool(tratamento) or bool(nome_campo)
    if nome_campo:
        erro("campo `nome:` preenchido; a ficha não leva nome próprio.")

    tem_cargo = bool(CARGO.search(texto))
    tem_cidade = bool(MUNICIPIO.search(texto))
    if tem_cargo and tem_cidade:
        revisada = _campo(linhas, "identificacao_indireta_revisada") == "sim"
        if eleitoral:
            erro("--eleitoral: cargo + cidade na mesma ficha; marcar revisão não basta, "
                 "tire um dos dois.")
        elif revisada:
            avisos.append("AVISO: cargo + cidade na mesma ficha; segue porque "
                          "identificacao_indireta_revisada: sim.")
        else:
            erro("cargo + cidade na mesma ficha pode identificar a pessoa; revise e "
                 "marque `identificacao_indireta_revisada: sim`, ou tire um dos dois.")

    if eleitoral:
        if real and (ELEITOR.search(texto) or "eleitor" in (_campo(linhas, "papel") or "")):
            erro("--eleitoral: ficha de eleitor com origem real não entra; só agregado.")
        if identificada and tem_cidade:
            erro("--eleitoral: nome ou tratamento + cidade na mesma ficha.")

    if real or identificada or (tem_cargo and tem_cidade):
        achou = set()
        for i, l in enumerate(linhas, 1):
            lb = _sem_acento(l)
            if PARTIDOS.search(l):
                achou.add((i, "política"))
            for cat, pad in TERMOS.items():
                if re.search(pad, lb):
                    achou.add((i, cat))
        for i, cat in sorted(achou):
            erro("opinião ou condição de %s atribuída a pessoa identificada ou real: "
                 "só agregado." % cat, i)
    return erros, avisos


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    eleitoral = "--eleitoral" in args
    args = [a for a in args if a != "--eleitoral"]
    if len(args) != 1:
        print("uso: ficha_lint.py <ficha.md> [--eleitoral]")
        return 2
    caminho = Path(args[0])
    try:
        texto = caminho.read_text(encoding="utf-8")
    except OSError as e:
        print("não consegui ler a ficha: %s" % e)
        return 2
    erros, avisos = validar(texto, eleitoral)
    for a in avisos:
        print("%s: %s" % (caminho, a))
    for e in erros:
        print("%s: %s" % (caminho, e))
    if erros:
        return 1
    print("%s: ficha aprovada." % caminho)
    return 0


if __name__ == "__main__":
    sys.exit(main())
