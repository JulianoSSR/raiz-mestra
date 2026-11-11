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
  - dado pessoal escrito de jeito incomum (CPF por extenso, e-mail com " arroba ",
    e-mail com "(at)", CEP ou endereço fora do formato de pseudonimizar.py);
  - endereço de Brasília (SQS, quadra, lote) e logradouro sem número;
  - tratamento com nome fora de NOMES_COMUNS, em minúsculo ("a tia Cida da cantina"
    não casa: tia, tio, padre, irmã e frei não são tratamento aqui);
  - texto de injeção do leitor: este lint não lê fonte externa (quem trata isso é ler_ficha.py).
Cargo + cidade: "Secretário de Saúde" casa como "cargo + cidade" porque "de Saúde"
tem o formato "de <Capitalizada>". Nesse caso a saída é revisar a ficha e marcar
identificacao_indireta_revisada: sim (em --eleitoral, tirar um dos dois).
Cidade em minúsculo só conta colada a cargo público ("prefeito de sobral"); solta
("o prefeito mora em sobral") ou depois de cargo privado ("diretor em sobral") não é pega,
nem capital em minúsculo fora desse caso. Nome em minúsculo conta depois de tratamento
("dona maria", "seu joão", "dr. carlos") só se estiver em NOMES_COMUNS ou depois de "dona"
com palavra fora de NAO_NOME. Nomes comuns que não estão na lista passam: a lista é curta.
Falso alarme que sobra: "dona" + verbo ou adjetivo fora da lista curta ("a dona paga")
e cargo público + palavra comum fora da lista ("juiz de várzea"); a saída é a revisão.
"""
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pseudonimizar import CEP, CPF, EMAIL, ENDERECO, TELEFONE  # noqa: E402

CAPITAIS = ("Rio Branco", "Maceió", "Macapá", "Manaus", "Salvador", "Fortaleza",
            "Brasília", "Vitória", "Goiânia", "São Luís", "Cuiabá", "Campo Grande",
            "Belo Horizonte", "Belém", "João Pessoa", "Curitiba", "Recife", "Teresina",
            "Rio de Janeiro", "Natal", "Porto Alegre", "Porto Velho", "Boa Vista",
            "Florianópolis", "São Paulo", "Aracaju", "Palmas")
_PUBLICO = (r"prefeit[oa]s?|vereador(?:a|es|as)?|pastor(?:a|es|as)?|padres?|delegad[oa]s?|"
            r"ju[ií]z(?:a|es|as)?|promotor(?:a|es|as)?")
_CARGO = _PUBLICO + r"|secret[áa]ri[oa]s?|diretor(?:a|es|as)?|president[ea]s?|s[ií]ndic[oa]s?"
CARGO = re.compile(r"\b(?:" + _CARGO + r")\b", re.IGNORECASE)

_MAIUSCULA = r"[A-ZÀ-Ý][^\W\d_]{2,}"
# Cidade em qualquer lugar da ficha: capital pelo nome, ou "de/em <Capitalizada>".
MUNICIPIO = re.compile(
    r"\b(?:" + "|".join(re.escape(c) for c in CAPITAIS) + r")\b"
    r"|\b(?i:de|em)\s+" + _MAIUSCULA)
# Cidade colada ao cargo: "prefeito do Crato", "Vereadora por Sobral".
CARGO_CIDADE = re.compile(
    r"\b(?i:" + _CARGO + r")\s+(?i:de|do|da|em|no|na|por)\s+" + _MAIUSCULA)
# Cidade em minúsculo: só colada a cargo público ("prefeito de sobral").
PUBLICO_CIDADE = re.compile(
    r"\b(?:" + _PUBLICO + r")\s+(?:de|do|da|em|no|na|por)\s+([^\W\d_]{3,})", re.IGNORECASE)
# Palavra comum depois de cargo público que não é cidade (comparada sem acento).
NAO_CIDADE = frozenset(
    "uma cidade municipio interior capital regiao bairro distrito comunidade igreja "
    "paroquia congregacao vendas eventos justica direito paz policia futebol oposicao "
    "primeira primeiro segunda segundo pequena pequeno grande media medio vara comarca "
    "camara prefeitura partido carreira plantao familia menores turismo".split())

# Tratamento sem distinção de caixa, seguido de nome com inicial maiúscula.
TRATAMENTO_NOME = re.compile(
    r"\b(?i:dona|seu|dr\.?|dra\.?|sr\.?|sra\.?|srta\.?|prof\.?|profa\.?|doutor|doutora|"
    r"professor|professora)\s+[A-ZÀ-Ý][^\W\d_]+")
# Nome em minúsculo: só depois de "dona" ("dona maria").
DONA_NOME = re.compile(r"\bdona\s+([^\W\d_]{3,})", re.IGNORECASE)
# Palavra comum depois de "dona" que não é nome (comparada sem acento).
NAO_NOME = frozenset(
    "nao nem que quer quem tambem sempre nunca ainda mesma para por com sem das dos "
    "uma dessa desta daquela desse deste daquele unica atual antiga nova decide paga "
    "prefere acha tem faz abre fecha desde mas mora trabalha cuida atende vende compra "
    "sozinha junto entre sobre".split())

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

# Tratamento em minúsculo seguido de nome comum brasileiro ("seu joão", "dr. carlos").
TRAT_MIN = re.compile(
    r"\b(?i:seu|dr\.?|dra\.?|sr\.?|sra\.?|srta\.?|prof\.?|profa\.?|professor|professora|doutor|doutora)\s+([^\W\d_]{3,})")
# Lista de primeiros nomes comuns (sem acento, minúsculas). Não é lista completa: o que não
# estiver aqui não é pego no tratamento em minúsculo; "dona" continua com a regra de NAO_NOME.
NOMES_COMUNS = frozenset(
    "joao jose maria ana antonio francisco carlos paulo pedro lucas luiz luis marcos gabriel "
    "rafael daniel marcelo bruno eduardo felipe rodrigo andre fernando fabio ricardo sergio "
    "roberto alexandre thiago leonardo gustavo diego julio juliano vitor victor jorge mario "
    "raimundo edson geraldo claudio cesar wagner wellington samuel fernanda juliana patricia "
    "adriana aline sandra cristina camila carla daniela simone luciana claudia mariana vanessa "
    "renata tatiana beatriz larissa leticia amanda bruna bianca priscila rosangela lucia "
    "luzia teresa fatima joana helena elaine eliane marta sonia silvia regina nilza lourdes "
    "aparecida cida zelia pereira oliveira souza silva santos ferreira alves "
    "gomes ribeiro carvalho lopes teixeira".split())
# rosa, lima, costa e rocha saíram: são substantivos comuns ("o seu rosa de sempre") e davam falso positivo.

# Modelo de ficha que não foi preenchido: <...>, linha inteira entre parênteses, seção vazia.
PLACEHOLDER = re.compile(r"<[A-Za-zÀ-ÿ|.\s/_\-]{1,80}>")  # só letras e o que o molde usa
ORIENTACAO = re.compile(r"^\s*\([^():\d]*\)\s*$")  # sem dois-pontos nem números: "(nota: ... 2025)" passa


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


def _linhas_fora_da_lista(padrao, linhas, lista):
    """Linhas em que o grupo 1 do padrão casa com palavra fora da lista de palavras comuns."""
    return [i + 1 for i, l in enumerate(linhas)
            if any(_sem_acento(m.group(1)) not in lista for m in padrao.finditer(l))]


def _linhas_na_lista(padrao, linhas, lista):
    """Linhas em que o grupo 1 do padrão casa com palavra que está na lista."""
    return [i + 1 for i, l in enumerate(linhas)
            if any(_sem_acento(m.group(1)) in lista for m in padrao.finditer(l))]


def _secoes_vazias(linhas):
    """Números das linhas de '## ...' seguidas só de linhas vazias até a próxima seção."""
    vazias = []
    for i, l in enumerate(linhas):
        if l.startswith("## "):
            corpo = []
            for prox in linhas[i + 1:]:
                if prox.startswith("## "):
                    break
                corpo.append(prox)
            if not any(c.strip() for c in corpo):
                vazias.append(i + 1)
    return vazias


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

    for n in _linhas_com(PLACEHOLDER, linhas):
        erro("trecho do modelo ainda no texto (<...>); troque pelo valor ou apague a linha.", n)
    for n in [i + 1 for i, l in enumerate(linhas) if ORIENTACAO.match(l)]:
        erro("linha entre parênteses é orientação do modelo; apague ao preencher.", n)
    for n in _secoes_vazias(linhas):
        erro("seção sem texto; preencha ou apague o título.", n)

    for nome, pad, rotulo in (("cpf", CPF, "CPF"), ("email", EMAIL, "e-mail"),
                              ("telefone", TELEFONE, "telefone"), ("cep", CEP, "CEP"),
                              ("endereco", ENDERECO, "endereço")):
        for n in _linhas_com(pad, linhas):
            erro("%s no texto da ficha; remova." % rotulo, n)

    if real and _campo(linhas, "consentimento") != "sim":
        erro("origem real exige `consentimento: sim`; campo ausente ou diferente de sim.")

    tratamento = _linhas_com(TRATAMENTO_NOME, linhas)
    for n in tratamento:
        erro("tratamento com nome próprio (ex.: dona Maria); use só o papel.", n)
    revisada = _campo(linhas, "identificacao_indireta_revisada") == "sim"
    nomes_min = _linhas_na_lista(TRAT_MIN, linhas, NOMES_COMUNS)
    dona = sorted((set(_linhas_fora_da_lista(DONA_NOME, linhas, NAO_NOME)) | set(nomes_min))
                  - set(tratamento))
    for n in dona:
        if revisada and not eleitoral:
            avisos.append("AVISO: linha %d: tratamento seguido de palavra que pode ser nome; "
                          "segue porque identificacao_indireta_revisada: sim." % n)
        else:
            erro("tratamento seguido de palavra que pode ser nome próprio (ex.: dona maria, "
                 "seu joão); use só o papel, ou revise e marque `identificacao_indireta_revisada: "
                 "sim` (não vale em --eleitoral).", n)
    nome_campo = _campo(linhas, "nome")
    identificada = (bool(tratamento) or bool(nome_campo)
                    or bool(dona and not (revisada and not eleitoral)))
    if nome_campo:
        erro("campo `nome:` preenchido; a ficha não leva nome próprio.")

    tem_cargo = bool(CARGO.search(texto))
    tem_cidade = bool(MUNICIPIO.search(texto) or CARGO_CIDADE.search(texto)
                      or _linhas_fora_da_lista(PUBLICO_CIDADE, linhas, NAO_CIDADE))
    if tem_cargo and tem_cidade:
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
