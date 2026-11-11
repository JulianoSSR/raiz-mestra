"""Pseudonimização e limpeza heurística de texto com dado pessoal.

Uso: pseudonimizar.py <entrada.txt> <saida.txt> --nomes <lista.txt> [--dossie SLUG]
     pseudonimizar.py <entrada.txt> <saida.txt> --so-limpeza

Duas etapas, nesta ordem:
  1. Cada nome da lista do usuário vira um código estável (P01, P02...). O mapa
     nome->código fica SÓ na pasta de dados do dossiê, nunca na saída.
  2. Limpeza heurística: CPF, e-mail (também "fulano (at) dominio.com", "[at]", "arroba" e
     "(arroba)" entre usuário e domínio), telefone, CEP, endereço com número e endereço de
     quadra (SQS 308, QNM 17 Conjunto H Casa 22, Bloco C, Bl. C apt 201, apto 201,
     Quadra 5 Lote 12, Qd. 5 Lt. 12).

DECLARADAMENTE NÃO PEGA (a limpeza é por padrão, não é garantia):
  - endereço por extenso sem número ("a rua atrás da igreja matriz");
  - nome que o usuário não pôs na lista, apelido e variação de grafia
    (ex.: "Zezé" quando a lista tem "José");
  - telefone de 10 dígitos sem nenhuma pontuação ou prefixo;
  - número bruto de 11 dígitos: é tratado como CPF, mesmo que seja telefone;
  - e-mail disfarçado de outro jeito ("fulano em dominio ponto com", "(dot)", "fulano at
    dominio.com", "fulano @ dominio.com"), "arroba" antes de domínio que começa por "www." e
    "arroba" depois de usuário com letra acentuada ("joão arroba gmail.com");
  - "casa 12" sozinho ou depois de condomínio sem número ("Condomínio Bela Vista, casa 12"),
    "Quadra 5 Casa 12", "Quadra B Lote 12", sigla de quadra em minúscula ou com hífen
    ("sqs 308", "SQS-308"), e "apartamento nº 201" fora de um endereço de bloco ou quadra;
  - fixo sem DDD cujos dois blocos parecem ano (2020-1999): fica no texto, para que
    intervalo de anos ("2019-2023") não vire telefone;
  - placa de veículo, RG, título de eleitor, conta bancária, data de nascimento;
  - descrição física e identificação por combinação de detalhes;
  - CNPJ: não é removido de propósito (é dado de empresa, não de pessoa).
REMOVE A MAIS, de propósito: "Vila", "Campo", "Ponte" e os outros logradouros seguidos de
número em até sete palavras saem como endereço ("Campo de futebol com 11 jogadores"), e
"QI 120", "QE 40", "Bloco A", "bloco 12", "bloco c" e "Lt 12" saem mesmo quando não são
endereço ("vende bloco b inteiro"). "Bloco" seguido de a, e ou o minúsculos fica ("bloco a
bloco"). "Apartamento 2" sai quando a palavra seguinte não é quartos, suítes, dormitórios,
vagas, banheiros ou cômodos ("Apartamento 2 salas amplas" sai).
O texto que você colou na conversa já foi enviado ao provedor do modelo.
"""
import argparse
import json
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dados  # noqa: E402

AVISO = ("Limpeza por padrão: não é garantia. O texto que você colou na conversa "
         "já foi enviado ao provedor do modelo.")

EMAIL = re.compile(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+")
# E-mail disfarçado: "fulano (at) dominio.com", "fulano [at] dominio.com", "fulano arroba dominio.com".
# Fica fora de EMAIL de propósito: EMAIL continua casando só com um "@".
# "arroba" por extenso só vale entre usuário e domínio com letras depois do último ponto:
# "Cotação da arroba 310.50" (número solto) e "símbolo arroba www.site.com" (site) ficam.
EMAIL_DISFARCADO = re.compile(
    r"[\w.+\-]+[ \t]*(?:\(at\)|\[at\])[ \t]*[\w\-]+(?:\.[\w\-]+)+"
    r"|(?<![\w.+\-])[A-Za-z0-9._+\-]+"
    r"(?:[ \t]+arroba[ \t]+|[ \t]*(?:\(arroba\)|\[arroba\])[ \t]*)"
    r"(?!www\.)[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}(?![\w])",
    re.IGNORECASE)
# CPF com separador opcional (ponto, espaço, barra, hífen). CNPJ não casa: 2 + 3 + 3 + 4 + 2.
CPF = re.compile(r"(?<![\d/])\d{3}[ .\-]?\d{3}[ .\-]?\d{3}[ \t]*[-/.]?[ \t]*\d{2}(?!\d)")
# CEP com ou sem hífen, espaço ou ponto. Oito dígitos seguidos também casam.
CEP = re.compile(r"(?<!\d)\d{2}\.?\d{3}[ \-]?\d{3}(?!\d)")
TELEFONE = re.compile(
    r"(?<!\d)(?:"
    # DDD com parênteses ou separador, depois 9 solto ou não, e os dois blocos de 4
    r"(?:\+?55[ .\-]?)?(?:\(\d{2}\)[ ]?|\d{2}[ .\-])9?[ .\-]?\d{4}[ .\-]?\d{4}"
    r"|9\d{4}[ .\-]?\d{4}"                                  # 99999 0000 (celular sem DDD)
    # 9999-0000 ou 9999 0000 (fixo sem DDD); dois anos seguidos ("2019-2023") são intervalo
    r"|(?!(?:19|20)\d\d[ \-](?:19|20)\d\d(?!\d))\d{4}[ \-]\d{4}"
    r"|(?:\+|wa\.me/)55\d{10,11}"                           # +5585999990000 e wa.me/5585...
    r"|0800[ .\-]?\d{3}[ .\-]?\d{4}"                        # 0800 123 4567
    r")(?!\d)")
_LOGRADOURO = (r"(?:Rua|R\.|Avenida|Av\.?|Travessa|Trav\.|Tv\.|Alameda|Al\.|Pra[çc]a|"
               r"Estrada|Rodovia|Rod\.|Largo|Beco|Ladeira|Vila|Viela|Ponte|Campo|"
               r"Ch[áa]cara|Condom[íi]nio)")
# Palavras do nome podem começar por dígito ("Rua 7 de Setembro, 45").
_ATE_O_NUMERO = (r"(?<![\w])" + _LOGRADOURO + r"\s+(?:[\w'.\-]+\s+){0,6}?[\w'.\-]+"
                 r"\s*,?\s*(?:n(?:[º°o]|[úu]mero)\.?\s*)?")
_NUMERO = r"(?:\d{1,5}[A-Za-z]?(?![\w])%s|km\s*\d+(?:[.,]\d+)?|s/n(?![\w]))"
# Primeiro tenta o número que não é seguido de "de/do/da": em "Rua 13 de Maio, 200" o 13
# é nome da rua, não número da casa. Se assim não casar ("Rua das Flores, 123 de frente"),
# vale o número mesmo seguido de preposição.
# Endereço de quadra (Brasília e loteamentos), que não tem logradouro + número. As siglas
# só valem em maiúsculas: "qi" e "ql" minúsculos aparecem em texto comum.
# "Apartamento 2 quartos" é anúncio, não endereço.
_NAO_COMODO = r"(?![\w])(?!\s+(?:quartos?|su[íi]tes?|dormit[óo]rios?|vagas?|banheiros?|c[ôo]modos?)(?![\w]))"
# "Bloco" com letra: maiúscula isolada ("Bloco C") ou minúscula que não seja a, e, o
# ("bloco c."); assim "bloco a bloco", "bloco e cada" e "bloco a ser" ficam. Com número, sempre.
_PECA_QUADRA = (r"(?:(?-i:SQS|SQN|CLN|CLS|QNM|QNN|QNL|QE|QS|QI|QD|QL|QR)[ \t]*\d{1,4}(?![\w])"
                r"(?:\s+(?:Conjunto|Casa|Lote)\s+(?:\d{1,4}|(?-i:[A-Z]))(?![\w]))*"
                r"|Quadra\s+\d{1,4}\s*,?\s*Lote\s+\d{1,4}(?![\w])"
                r"|(?:Qd|Lt)\.?\s*\d{1,4}(?![\w])"
                r"|Bloco\s+(?:\d{1,4}|(?-i:[A-Zb-df-np-z]))(?![\w])"
                r"|(?-i:B[Ll])\.?\s*(?-i:[A-Z])(?![\w])"
                r"|ap(?:to|artamento)\.?\s*\d{1,5}" + _NAO_COMODO + r")")
# só valem coladas a uma peça anterior: "Bloco 12 ap. 34", "Bl. C apt 201", "Bloco C apartamento nº 201"
_PECA_SEGUINTE = (r"(?:" + _PECA_QUADRA
                  + r"|(?:ap(?:to?|artamento)?\.?\s*(?:n[º°]\.?\s*)?|n[º°]\.?\s*)\d{1,5}" + _NAO_COMODO + r")")
# peças vizinhas ("SQS 308 Bloco C apto 201") saem numa marca só
_QUADRA = r"(?<![\w])" + _PECA_QUADRA + r"(?:[\s,]+" + _PECA_SEGUINTE + r")*"
ENDERECO = re.compile(
    _ATE_O_NUMERO + _NUMERO % r"(?!\s+d[eao]s?\s)" + "|" + _ATE_O_NUMERO + _NUMERO % ""
    + "|" + _QUADRA,
    re.IGNORECASE)

# ordem importa: e-mail antes de tudo; CPF antes de telefone; CEP antes de telefone
ETAPAS = (("email", EMAIL), ("cpf", CPF), ("cep", CEP),
          ("telefone", TELEFONE), ("endereco", ENDERECO))


def _base(texto):
    """Minúsculo e sem acento, com o MESMO comprimento do texto (NFC de entrada)."""
    saida = []
    for c in texto:
        d = unicodedata.normalize("NFD", c)
        saida.append(d[0].lower() if d else c)
    return "".join(saida)


def _carregar_mapa(caminho):
    if caminho.exists():
        return json.loads(caminho.read_text(encoding="utf-8"))
    return {}


def _mapa_valido(mapa):
    return isinstance(mapa, dict) and all(
        isinstance(k, str) and isinstance(v, str) for k, v in mapa.items())


def _gravar_mapa(caminho, mapa):
    """Grava por arquivo temporário criado com 0o600 e troca atômica (os.replace)."""
    fd, tmp = tempfile.mkstemp(dir=str(caminho.parent), prefix=".mapa-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(mapa, ensure_ascii=False, indent=2))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, caminho)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _sem_invisiveis(t):
    """Tira categoria Cf (largura zero, marcas de direção). Não mexe no resto."""
    return "".join(c for c in t if unicodedata.category(c) != "Cf")


def _norma_nome(n):
    return " ".join(_sem_invisiveis(unicodedata.normalize("NFC", n)).split())


def trocar_nomes(texto, nomes, mapa, avisos=None):
    """Troca nomes por códigos. Mapa nome->código é alterado (códigos estáveis).

    Nome da lista sem nenhuma ocorrência não é erro: vira aviso (em `avisos`, se passado),
    porque a mesma lista serve a vários textos.
    """
    texto = _sem_invisiveis(unicodedata.normalize("NFC", texto))
    nomes = [_norma_nome(n) for n in nomes]
    chaves = {_base(_norma_nome(n)): n for n in mapa}
    for n in nomes:
        k = _base(n)
        if k and k not in chaves:
            mapa[n] = "P%02d" % (len(mapa) + 1)
            chaves[k] = n
    por_chave = {_base(_norma_nome(n)): c for n, c in mapa.items()}
    # nomes mais longos primeiro: o nome completo vence o primeiro nome isolado
    desta_lista = {_base(n) for n in nomes}
    ordem = sorted((k for k in desta_lista if k), key=len, reverse=True)
    achados = 0
    sem_ocorrencia = {}
    for k in ordem:
        partes = [re.escape(p) for p in k.split()]
        padrao = re.compile(r"(?<!\w)" + r"\s+".join(partes) + r"(?!\w)")
        base = _base(texto)
        trechos = list(padrao.finditer(base))
        for m in reversed(trechos):
            texto = texto[:m.start()] + por_chave[k] + texto[m.end():]
        achados += len(trechos)
        sem_ocorrencia[k] = not trechos
    if avisos is not None:
        vistos = set()
        for pos, n in enumerate(nomes, 1):
            k = _base(n)
            if k and k not in vistos and sem_ocorrencia.get(k):
                avisos.append("AVISO: nome da lista número %d não apareceu no texto; "
                              "não houve troca para ele." % pos)
            vistos.add(k)
    return texto, achados


def limpar(texto):
    """Limpeza heurística. Devolve (texto, contagem por tipo)."""
    contagem = {}
    # rótulo próprio ("e-mail"), mas a contagem soma na chave "email"
    texto, disfarcados = EMAIL_DISFARCADO.subn("[e-mail removido]", texto)
    for nome, padrao in ETAPAS:
        texto, n = padrao.subn("[%s removido]" % nome, texto)
        contagem[nome] = n
    contagem["email"] += disfarcados
    return texto, contagem


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Pseudonimiza nomes e limpa dado pessoal.")
    ap.add_argument("entrada")
    ap.add_argument("saida")
    ap.add_argument("--nomes", help="lista de nomes, um por linha")
    ap.add_argument("--so-limpeza", action="store_true", help="só a limpeza heurística")
    ap.add_argument("--dossie", default="geral", help="slug do dossiê onde o mapa fica")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    if not a.so_limpeza and not a.nomes:
        print("uso: passe --nomes <lista.txt> ou --so-limpeza.")
        return 2
    try:
        texto = Path(a.entrada).read_text(encoding="utf-8")
        nomes = []
        if a.nomes and not a.so_limpeza:
            nomes = [l.strip() for l in Path(a.nomes).read_text(encoding="utf-8").splitlines()
                     if l.strip()]
    except OSError as e:
        print("não consegui ler: %s" % e)
        return 2

    n_nomes = 0
    avisos = []
    if nomes:
        try:
            pasta = dados.pasta_dossie(a.dossie, criar=True)
        except dados.ErroDados as e:
            print(str(e))
            return 2
        caminho = dados.dentro_da_pasta(pasta / "mapa-pseudonimos.json")
        try:
            mapa = _carregar_mapa(caminho)
        except (OSError, ValueError):
            mapa = None
        if not _mapa_valido(mapa):
            print("mapa de pseudônimos do dossiê %s não é um dicionário JSON válido; "
                  "não alterei nada. Confira o arquivo antes de rodar de novo." % a.dossie)
            return 1
        texto, n_nomes = trocar_nomes(texto, nomes, mapa, avisos)
        _gravar_mapa(caminho, mapa)
    texto, cont = limpar(texto)
    Path(a.saida).write_text(texto, encoding="utf-8")

    for aviso in avisos:
        print(aviso)
    partes = ["%s: %d" % (k, v) for k, v in cont.items()]
    if not a.so_limpeza:
        partes.insert(0, "nomes trocados: %d" % n_nomes)
    print("Removido: " + "; ".join(partes))
    print(AVISO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
