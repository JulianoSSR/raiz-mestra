"""SHA-256 determinístico de uma árvore de diretório.

Entra no hash: caminho relativo, tipo (arquivo, pasta, link, outro), modo e conteúdo (ou alvo do link).
Pastas vazias e links contam. Ficam de fora só o que muda sem ser gravação do usuário:
__pycache__, .seiva, .git/index e .git/objects. O resto de .git (hooks, config, HEAD, refs) conta.
"""
import hashlib
import os
import stat
import sys
from pathlib import Path

IGNORAR = {"__pycache__", ".seiva"}
IGNORAR_GIT = {"index", "objects"}


def _ignorar(partes):
    if IGNORAR.intersection(partes):
        return True
    for i, p in enumerate(partes[:-1]):
        if p == ".git" and partes[i + 1] in IGNORAR_GIT:
            return True
    return False


def _entradas(raiz):
    itens = []
    for dp, dns, fns in os.walk(raiz):
        base = Path(dp)
        pai = base.relative_to(raiz).parts
        # os.walk não desce em link de pasta (followlinks=False); o link aparece aqui como entrada
        dns[:] = sorted(d for d in dns if not _ignorar(pai + (d,)))
        for d in dns:
            itens.append((pai + (d,), base / d))
        for f in fns:
            if not _ignorar(pai + (f,)):
                itens.append((pai + (f,), base / f))
    return sorted(itens, key=lambda x: "/".join(x[0]))


def hash_arvore(raiz):
    raiz = Path(raiz)
    h = hashlib.sha256()
    for partes, p in _entradas(raiz):
        rel = "/".join(partes).encode("utf-8")
        st = os.lstat(p)
        if stat.S_ISLNK(st.st_mode):
            tipo, dado = b"L", os.readlink(p).encode("utf-8")
        elif stat.S_ISDIR(st.st_mode):
            tipo, dado = b"D", b""
        elif stat.S_ISREG(st.st_mode):
            tipo, dado = b"F", p.read_bytes()
        else:
            tipo, dado = b"O", b""  # fifo, socket etc.: não lê, só registra que existe
        modo = (st.st_mode & 0o7777).to_bytes(2, "big")
        for bloco in (rel, tipo + modo, dado):
            h.update(len(bloco).to_bytes(8, "big") + bloco)
    return h.hexdigest()


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) != 1 or not Path(a[0]).is_dir():
        print("uso: hash_arvore.py <pasta>")
        return 2
    print(hash_arvore(a[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
