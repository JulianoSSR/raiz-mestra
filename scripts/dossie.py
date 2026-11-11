"""Dossiê da empreitada: estado.json por slug. Uso: dossie.py <subcomando> ..."""
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dados  # noqa: E402
import lint_entrega  # noqa: E402
import rotular  # noqa: E402

PASSOS = ["triagem", "levantamento", "mapa", "conceitos", "pre-mortem", "entrega", "aprendizado"]
VALORES = {
    "tamanho": ("E0", "E1", "E2", "E3"),
    "eleitoral": ("sim", "não"),
    "aprendizado": ("proposto", "nada a propor"),
}
TRAVA = ("tamanho", "eleitoral")  # respostas que a entrega conferida carrega no cabeçalho
# as mesmas extensões que lint_entrega.carregar_pesquisa lê de uma pasta
EXT_PESQUISA = (".md", ".txt", ".json", ".html", ".csv")


class ErroDossie(Exception):
    pass


def _arquivo(slug):
    return dados.arquivo_no_dossie(slug, "estado.json")


def _agora():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def carregar(slug):
    arq = _arquivo(slug)
    if not arq.exists():
        raise ErroDossie("dossiê '%s' não existe: rode init antes." % slug)
    try:
        est = json.loads(arq.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        raise ErroDossie("estado.json ilegível ou truncado (%s); não vou sobrescrever. "
                         "Confira o arquivo: %s" % (type(e).__name__, dados.exibir(arq)))
    if not isinstance(est, dict) or not isinstance(est.get("passos"), dict) \
            or not isinstance(est.get("respostas"), dict):
        raise ErroDossie("estado.json com estrutura inválida; não vou sobrescrever: %s" % dados.exibir(arq))
    return est


def gravar(slug, est):
    arq = _arquivo(slug)
    fd, tmp = tempfile.mkstemp(dir=str(arq.parent), prefix=".estado-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(est, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, arq)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def init(slug):
    dados.pasta_dossie(slug, criar=True)
    if _arquivo(slug).exists():
        raise ErroDossie("dossiê '%s' já existe." % slug)
    gravar(slug, {"slug": slug, "criado": _agora(), "fechado": None, "passos": {}, "respostas": {}})


def _sha256(arq):
    try:
        return hashlib.sha256(arq.read_bytes()).hexdigest()
    except OSError as e:
        raise ErroDossie("não consegui ler a entrega (%s): %s" % (type(e).__name__, dados.exibir(arq)))


def _conferir_cabecalho(arq, respostas, desfecho="passo entrega não gravado"):
    """O cabeçalho da entrega tem de dizer o que o usuário respondeu (tamanho e eleitoral)."""
    try:
        texto = arq.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise ErroDossie("não consegui ler a entrega (%s): %s" % (type(e).__name__, dados.exibir(arq)))
    cabecalho = rotular.parse_entrega(texto)["header"]
    for chave in TRAVA:
        lido = cabecalho.get(chave)
        if lido is None or rotular.sem_acento(lido).strip().upper() \
                != rotular.sem_acento(respostas[chave]).strip().upper():
            raise ErroDossie("cabeçalho da entrega diverge do dossiê: %s está '%s' no arquivo e '%s' "
                             "nas respostas (ausente conta como divergente); %s."
                             % (chave, lido or "ausente", respostas[chave], desfecho))


def _fontes_de_pesquisa(arq, sha, pesquisa, slug):
    """Lista (caminho e sha256) dos arquivos de --pesquisa que o lint lê.

    Recusa fonte que seja a própria entrega (pelo caminho ou pelo conteúdo) ou que
    esteja na pasta do dossiê: comparar a entrega com ela mesma não confere cópia.
    """
    entrega = Path(os.path.realpath(arq))
    pasta = dados.pasta_dossie(slug) if slug else None
    fontes = []
    for c in pesquisa:
        p = Path(c)
        if p.is_file():
            arqs = [p]
        else:
            arqs = sorted(q for q in p.rglob("*") if q.is_file() and q.suffix.lower() in EXT_PESQUISA)
        for a in [p] + arqs:
            real = Path(os.path.realpath(a))
            if real == entrega:
                raise ErroDossie("fonte de pesquisa recusada: %s é a própria entrega; "
                                 "passo entrega não gravado." % dados.exibir(a))
            if pasta is not None and (real == pasta or pasta in real.parents):
                raise ErroDossie("fonte de pesquisa recusada: %s está na pasta do dossiê; guarde a "
                                 "pesquisa fora dela. Passo entrega não gravado." % dados.exibir(a))
        for a in arqs:
            try:
                sha_fonte = hashlib.sha256(a.read_bytes()).hexdigest()
            except OSError:
                continue  # o lint também pula o que não consegue ler
            if sha_fonte == sha:
                raise ErroDossie("fonte de pesquisa recusada: %s tem o mesmo conteúdo da entrega; "
                                 "passo entrega não gravado." % dados.exibir(a))
            fontes.append({"caminho": str(a), "sha256": sha_fonte})
    return fontes


def conferir_entrega(evidencia, respostas, pesquisa=(), slug=None):
    """Roda rotular.py e lint_entrega.py sobre a entrega; devolve o que vai para o passo:
    o sha256 do arquivo conferido e a lista das fontes de pesquisa lidas.

    Antes, recusa se o cabeçalho divergir de `respostas` (tamanho e eleitoral) ou se
    alguma fonte de pesquisa for a própria entrega ou estiver na pasta do dossiê.
    A saída dos verificadores vai para a saída padrão. Os dois são heurísticos:
    passar aqui não prova que a entrega está certa.
    """
    if not evidencia:
        raise ErroDossie("o passo entrega exige --evidencia <arquivo> com a entrega a conferir.")
    arq = Path(evidencia)
    if not arq.is_file():
        raise ErroDossie("evidência da entrega não existe ou não é arquivo comum: %s" % dados.exibir(arq))
    sha = _sha256(arq)
    _conferir_cabecalho(arq, respostas)
    fontes = _fontes_de_pesquisa(arq, sha, pesquisa, slug)
    args_lint = [str(arq)]
    for fonte in pesquisa:
        args_lint += ["--pesquisa", str(fonte)]
    reprovou = []
    if rotular.main([str(arq)]) != 0:
        reprovou.append("rotular.py")
    if lint_entrega.main(args_lint) != 0:
        reprovou.append("lint_entrega.py")
    if reprovou:
        raise ErroDossie("entrega não passou em %s; passo entrega não gravado. Corrija o que "
                         "está apontado acima e marque de novo." % " e ".join(reprovou))
    if _sha256(arq) != sha:
        raise ErroDossie("a entrega mudou durante a conferência; passo entrega não gravado: %s"
                         % dados.exibir(arq))
    return {"sha256": sha, "pesquisa": fontes}


def marcar(slug, passo, evidencia=None, pesquisa=()):
    if passo not in PASSOS:
        raise ErroDossie("passo desconhecido: %s. Passos: %s" % (passo, ", ".join(PASSOS)))
    est = carregar(slug)
    if passo != "triagem":
        faltam = [c for c in ("tamanho", "eleitoral") if c not in est["respostas"]]
        if faltam:
            raise ErroDossie("não passo da triagem sem resposta de: %s (use responder)." % ", ".join(faltam))
    if passo in est["passos"]:
        return False
    if passo == "entrega" and evidencia:
        # caminho absoluto: o fechamento reconfere a entrega a partir de qualquer pasta
        evidencia = os.path.abspath(evidencia)
    registro = {"em": _agora(), "evidencia": evidencia}
    if passo == "entrega":
        registro.update(conferir_entrega(evidencia, est["respostas"], pesquisa, slug))
    est["passos"][passo] = registro
    gravar(slug, est)
    return True


def responder(slug, chave, valor):
    if chave in VALORES and valor not in VALORES[chave]:
        raise ErroDossie("valor inválido para %s: use %s." % (chave, "|".join(VALORES[chave])))
    est = carregar(slug)
    antiga = est["respostas"].get(chave)
    if chave in TRAVA and "entrega" in est["passos"] and valor != antiga:
        raise ErroDossie("a entrega foi conferida com a resposta antiga de %s ('%s'); não troco para '%s' "
                         "com o passo entrega marcado. Para trocar, rode `dossie.py desmarcar %s entrega` "
                         "(fica registrado), responda de novo e marque a entrega outra vez."
                         % (chave, antiga, valor, slug))
    est["respostas"][chave] = valor
    gravar(slug, est)


def desmarcar(slug, passo):
    """Tira a marca de um passo e guarda o registro anterior em `desmarcados`, para auditoria.

    Usado para trocar resposta de trava depois da entrega: o passo entrega sai, e a próxima
    marcação é conferida de novo com as respostas atuais.
    """
    if passo not in PASSOS:
        raise ErroDossie("passo desconhecido: %s. Passos: %s" % (passo, ", ".join(PASSOS)))
    est = carregar(slug)
    if passo not in est["passos"]:
        raise ErroDossie("o passo %s não está marcado; nada a desmarcar." % passo)
    anterior = est["passos"].pop(passo)
    est.setdefault("desmarcados", []).append({"em": _agora(), "passo": passo, "registro": anterior})
    gravar(slug, est)


def _reconferir_entrega(passo, respostas):
    """No fechamento: a entrega marcada ainda é o arquivo conferido e ainda bate com as respostas."""
    evidencia = passo.get("evidencia") if isinstance(passo, dict) else None
    if not evidencia:
        raise ErroDossie("não fecho: o passo entrega está marcado sem evidência para reconferir.")
    faltam = [c for c in TRAVA if c not in respostas]
    if faltam:
        raise ErroDossie("não fecho: entrega marcada e o dossiê está sem resposta de: %s." % ", ".join(faltam))
    arq = Path(evidencia)
    if _sha256(arq) != passo.get("sha256"):
        raise ErroDossie("não fecho: a entrega mudou depois de conferida (sha256 diferente do gravado "
                         "no passo): %s" % dados.exibir(arq))
    _conferir_cabecalho(arq, respostas, "não fecho")


def fechar(slug):
    est = carregar(slug)
    if est["respostas"].get("aprendizado") not in VALORES["aprendizado"]:
        raise ErroDossie("não fecho sem o registro de aprendizado: responda aprendizado "
                         "com 'proposto' ou 'nada a propor'.")
    if "entrega" in est["passos"]:
        _reconferir_entrega(est["passos"]["entrega"], est["respostas"])
    est["fechado"] = _agora()
    gravar(slug, est)


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    uso = ("uso: dossie.py init|estado|fechar <slug> | marcar <slug> <passo> [--evidencia caminho] "
           "| marcar <slug> entrega --evidencia <entrega.md> [--pesquisa <fonte>]... "
           "| responder <slug> <chave> <valor> | desmarcar <slug> <passo>")
    try:
        if not a:
            print(uso)
            return 2
        cmd, resto = a[0], a[1:]
        if cmd in ("init", "estado", "fechar") and len(resto) == 1:
            if cmd == "init":
                init(resto[0])
                print("dossiê criado: %s" % resto[0])
            elif cmd == "estado":
                print(json.dumps(carregar(resto[0]), ensure_ascii=False, indent=2))
            else:
                fechar(resto[0])
                print("dossiê fechado: %s" % resto[0])
            return 0
        if cmd == "marcar" and len(resto) >= 2 and len(resto) % 2 == 0:
            ev, pesq, opcoes = None, [], resto[2:]
            if opcoes:
                if opcoes[0] != "--evidencia":
                    print(uso)
                    return 2
                ev = opcoes[1]
                for i in range(2, len(opcoes), 2):
                    if opcoes[i] != "--pesquisa" or resto[1] != "entrega":
                        print(uso)
                        return 2
                    pesq.append(opcoes[i + 1])
            novo = marcar(resto[0], resto[1], ev, pesq)
            print("passo marcado: %s" % resto[1] if novo else "passo já estava marcado: %s" % resto[1])
            if novo and resto[1] == "entrega" and not carregar(resto[0])["passos"]["entrega"]["pesquisa"]:
                print("aviso: checagem de cópia não rodou (nenhuma fonte de pesquisa foi lida); "
                      "o passo foi marcado sem ela.")
            return 0
        if cmd == "responder" and len(resto) == 3:
            responder(*resto)
            print("resposta gravada: %s" % resto[1])
            return 0
        if cmd == "desmarcar" and len(resto) == 2:
            desmarcar(*resto)
            print("passo desmarcado: %s (registro anterior guardado em desmarcados)" % resto[1])
            return 0
        print(uso)
        return 2
    except (ErroDossie, dados.ErroDados) as e:
        print("reprovado: %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
