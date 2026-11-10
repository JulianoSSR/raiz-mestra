"""Pseudonimização e limpeza heurística de texto com dado pessoal.

Uso: pseudonimizar.py <entrada.txt> <saida.txt> --nomes <lista.txt> [--dossie SLUG]
     pseudonimizar.py <entrada.txt> <saida.txt> --so-limpeza

Duas etapas, nesta ordem:
  1. Cada nome da lista do usuário vira um código estável (P01, P02...). O mapa
     nome->código fica SÓ na pasta de dados do dossiê, nunca na saída.
  2. Limpeza heurística: CPF, e-mail, telefone, CEP e endereço com número.

DECLARADAMENTE NÃO PEGA (a limpeza é por padrão, não é garantia):
  - endereço por extenso sem número ("a rua atrás da igreja matriz");
  - nome que o usuário não pôs na lista, apelido e variação de grafia
    (ex.: "Zezé" quando a lista tem "José");
  - telefone de 10 dígitos sem nenhuma pontuação ou prefixo;
  - número bruto de 11 dígitos: é tratado como CPF, mesmo que seja telefone;
  - placa de veículo, RG, título de eleitor, conta bancária, data de nascimento;
  - descrição física e identificação por combinação de detalhes;
  - CNPJ: não é removido de propósito (é dado de empresa, não de pessoa).
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
# CPF com separador opcional (ponto, espaço, barra, hífen). CNPJ não casa: 2 + 3 + 3 + 4 + 2.
CPF = re.compile(r"(?<![\d/])\d{3}[ .]?\d{3}[ .]?\d{3}[ \t]*[-/.]?[ \t]*\d{2}(?!\d)")
# CEP com ou sem hífen e com ou sem ponto. Oito dígitos seguidos também casam.
CEP = re.compile(r"(?<!\d)\d{2}\.?\d{3}-?\d{3}(?!\d)")
TELEFONE = re.compile(
    r"(?<!\d)(?:"
    # DDD com parênteses ou separador, depois 9 solto ou não, e os dois blocos de 4
    r"(?:\+?55[ .\-]?)?(?:\(\d{2}\)[ ]?|\d{2}[ .\-])9?[ .\-]?\d{4}[ .\-]?\d{4}"
    r"|9\d{4}[ .\-]?\d{4}"                                  # 99999 0000 (celular sem DDD)
    r"|\d{4}-\d{4}"                                         # 9999-0000 (fixo sem DDD)
    r")(?!\d)")
_LOGRADOURO = (r"(?:Rua|R\.|Avenida|Av\.?|Travessa|Trav\.|Tv\.|Alameda|Al\.|Pra[çc]a|"
               r"Estrada|Rodovia|Rod\.|Largo|Beco)")
# Palavras do nome podem começar por dígito ("Rua 7 de Setembro, 45").
ENDERECO = re.compile(
    r"(?<![\w])" + _LOGRADOURO + r"\s+(?:[\w'.\-]+\s+){0,6}?[\w'.\-]+"
    r"\s*,?\s*(?:n[º°o]\.?\s*)?(?:\d{1,5}[A-Za-z]?(?![\w])|km\s*\d+(?:[.,]\d+)?|s/n(?![\w]))",
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
    for nome, padrao in ETAPAS:
        texto, n = padrao.subn("[%s removido]" % nome, texto)
        contagem[nome] = n
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
