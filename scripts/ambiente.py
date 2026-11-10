"""Único módulo que lê variáveis de ambiente. Lista fixa; nunca imprime valor."""
import os

PERMITIDAS = ("RAIZ_MESTRA_DADOS", "RAIZ_MESTRA_CHAVE_API", "HOME", "USERPROFILE")


class VariavelNaoPermitida(ValueError):
    pass


def _checar(nome):
    if nome not in PERMITIDAS:
        raise VariavelNaoPermitida("variável fora da lista permitida: %s" % nome)


def ler(nome):
    """Devolve o valor (ou None). Quem chama não deve imprimi-lo."""
    _checar(nome)
    return os.environ.get(nome)


def tem(nome):
    """Devolve só se a variável existe e não está vazia."""
    _checar(nome)
    return bool(os.environ.get(nome))
