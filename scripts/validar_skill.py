"""Valida uma pasta de skill (Agent Skills). A contagem de tokens é ESTIMATIVA: caracteres / 3,5."""
import math
import re
import sys
from pathlib import Path

CAMPOS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NOME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
AJUDA = ("uso: validar_skill.py <pasta-da-skill>\n"
         "Confere SKILL.md, frontmatter, nome, tamanhos. Tokens do corpo são estimativa "
         "(caracteres / 3,5, arredondado para cima), limite 3.000.")


def _frontmatter(linhas):
    if not linhas or linhas[0].strip() != "---":
        return None, 0
    for i in range(1, len(linhas)):
        if linhas[i].strip() == "---":
            return linhas[1:i], i + 1
    return None, 0


BLOCO = re.compile(r"^[|>][+-]?\d?[+-]?$")


def _chaves(fm):
    """Chaves de nível 0 e seus valores (sem YAML completo).

    O valor inclui as linhas recuadas que vêm depois da chave: bloco `|` ou `>` e
    texto continuado na linha seguinte. O tamanho conta o texto sem o recuo.
    """
    out = {}
    chave = None
    for n, l in enumerate(fm, 2):
        if l.startswith((" ", "\t")) or not l.strip():
            if chave and l.strip():
                out[chave][0].append(l.strip())
            continue
        chave = None
        if l.startswith(("#", "-")) or ":" not in l:
            continue
        k, v = l.split(":", 1)
        chave = k.strip()
        v = v.strip()
        out[chave] = ([] if BLOCO.match(v) else [v], n)
    return {k: (" ".join(p for p in partes if p).strip("\"'"), n) for k, (partes, n) in out.items()}


def validar(pasta):
    erros = []
    pasta = Path(pasta)
    arq = pasta / "SKILL.md"
    if not arq.is_file():
        return ["%s: SKILL.md não existe." % pasta]
    texto = arq.read_text(encoding="utf-8")
    linhas = texto.splitlines()
    if len(linhas) >= 500:
        erros.append("%s: %d linhas; o limite é menos de 500." % (arq, len(linhas)))
    fm, fim = _frontmatter(linhas)
    if fm is None:
        erros.append("%s:1: frontmatter ausente ou sem fechamento." % arq)
        return erros
    ch = _chaves(fm)
    for k, (_, n) in ch.items():
        if k not in CAMPOS:
            erros.append("%s:%d: campo fora da especificação: %s" % (arq, n, k))
    nome = ch.get("name", ("", 0))[0]
    if not nome:
        erros.append("%s: falta o campo name." % arq)
    else:
        if len(nome) > 64 or not NOME_RE.match(nome):
            erros.append("%s:%d: name deve ter minúsculas, números e hífen, até 64." % (arq, ch["name"][1]))
        if nome != pasta.resolve().name:
            erros.append("%s:%d: name '%s' difere do nome da pasta '%s'." % (arq, ch["name"][1], nome, pasta.resolve().name))
    desc = ch.get("description", ("", 0))[0]
    if not desc:
        erros.append("%s: falta o campo description." % arq)
    elif len(desc) > 1024:
        erros.append("%s:%d: description com %d caracteres; limite 1024." % (arq, ch["description"][1], len(desc)))
    comp = ch.get("compatibility")
    if comp and len(comp[0]) > 500:
        erros.append("%s:%d: compatibility com %d caracteres; limite 500." % (arq, comp[1], len(comp[0])))
    corpo = "\n".join(linhas[fim:])
    tokens = math.ceil(len(corpo) / 3.5)
    if tokens >= 3000:
        erros.append("%s: corpo com cerca de %d tokens (estimativa); limite 3.000." % (arq, tokens))
    return erros


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) != 1 or a[0] in ("-h", "--help"):
        print(AJUDA)
        return 2
    erros = validar(a[0])
    for e in erros:
        print(e)
    if erros:
        return 1
    print("aprovado: %s" % a[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
