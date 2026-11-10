"""Pasta de dados da skill e proteção de caminho."""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ambiente  # noqa: E402

SLUG_RE = re.compile(r"^[a-z0-9-]{1,40}$")


class ErroDados(ValueError):
    pass


def pasta_dados():
    base = ambiente.ler("RAIZ_MESTRA_DADOS")
    if base:
        p = Path(base)
    else:
        casa = ambiente.ler("HOME") or ambiente.ler("USERPROFILE")
        if not casa:
            raise ErroDados("não achei a pasta de dados: defina RAIZ_MESTRA_DADOS.")
        p = Path(casa) / ".raiz-mestra"
    p.mkdir(mode=0o700, parents=True, exist_ok=True)
    real = Path(os.path.realpath(p))
    (real / "cache_publico").mkdir(mode=0o700, exist_ok=True)
    return real


def exibir(caminho):
    """Caminho para mensagem: relativo à pasta de dados. Fora dela, só o nome do arquivo."""
    base = pasta_dados()
    for cand in (os.path.abspath(caminho), os.path.realpath(caminho)):
        try:
            return Path(cand).relative_to(base).as_posix()
        except ValueError:
            pass
    return "<fora da pasta de dados>/%s" % Path(caminho).name


def validar_slug(slug):
    if not isinstance(slug, str) or not SLUG_RE.match(slug):
        raise ErroDados("slug inválido: use de 1 a 40 caracteres entre a-z, 0-9 e hífen.")
    return slug


def dentro_da_pasta(caminho):
    """Resolve o caminho e recusa se sair da pasta de dados (.. ou symlink)."""
    raiz = pasta_dados()
    real = Path(os.path.realpath(caminho))
    if real != raiz and raiz not in real.parents:
        raise ErroDados("caminho fora da pasta de dados: %s" % exibir(caminho))
    return real


def pasta_dossie(slug, criar=False):
    validar_slug(slug)
    p = dentro_da_pasta(pasta_dados() / "dossies" / slug)
    if criar:
        (pasta_dados() / "dossies").mkdir(mode=0o700, exist_ok=True)
        p.mkdir(mode=0o700, exist_ok=True)
        p = dentro_da_pasta(p)
    return p


def arquivo_no_dossie(slug, nome):
    """Caminho de um arquivo do dossiê, garantido dentro da pasta de dados."""
    return dentro_da_pasta(pasta_dossie(slug) / nome)
