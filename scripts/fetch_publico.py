"""Consulta dados públicos brasileiros (IBGE, Banco Central, TSE, BrasilAPI) com cerca de segurança.

Regras fixas: só https; só os 4 hosts da lista; sem redirecionamento; teto de bytes lido;
timeout; argumentos validados por padrão estrito antes de entrar na URL. O cache em disco
guarda só o resumo já saneado e nunca nome de pessoa física.
A base de cada serviço só muda por parâmetro de função (teste), nunca por ambiente nem por linha de comando.
"""
import hashlib
import json
import os
import re
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dados  # noqa: E402
import ler_ficha  # noqa: E402

HOSTS_PERMITIDOS = (
    "servicodados.ibge.gov.br",
    "api.bcb.gov.br",
    "dadosabertos.tse.jus.br",
    "brasilapi.com.br",
)
BASES = {
    "ibge": "https://servicodados.ibge.gov.br",
    "bcb": "https://api.bcb.gov.br",
    "tse": "https://dadosabertos.tse.jus.br",
    "brasilapi": "https://brasilapi.com.br",
}
TETO_BYTES = 2 * 1024 * 1024
TIMEOUT = 15
PRAZO_TOTAL = 30  # segundos para uma consulta inteira (cabeçalho, corpo e repetição); o timeout vale por operação
VALIDADE_CACHE_S = 24 * 3600
# naturezas jurídicas de pessoa física que o cadastro público devolve com nome na razão social
NATUREZAS_INDIVIDUAIS = frozenset({"2135", "2305", "2321"})  # empresário individual, EIRELI, sociedade individual de advocacia (conferir tabela CONCLA antes de citar)
# sociedade empresária limitada (LTDA): razão social costuma trazer o nome do sócio; decisão do usuário em 2026-11-11
NATUREZAS_SEM_NOME = frozenset({"2062"})
UFS = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)


class ErroArgumento(ValueError):
    """Argumento recusado antes de qualquer consulta."""


class ErroUrl(ValueError):
    pass


class ErroFetch(Exception):
    """Falha da consulta (rede, HTTP, JSON, teto)."""


class _Transitorio(Exception):
    pass


# ---------- validação (funções puras) ----------

def validar_url(url, hosts=HOSTS_PERMITIDOS):
    """Confere a URL final montada: https, host da lista, sem credencial, sem porta estranha."""
    if not isinstance(url, str) or not re.fullmatch(r"[\x21-\x7e]+", url):
        raise ErroUrl("URL com caracteres inválidos.")
    p = urllib.parse.urlsplit(url)
    if p.scheme != "https":
        raise ErroUrl("só https é aceito: %s" % (p.scheme or "sem esquema"))
    if p.username is not None or p.password is not None:
        raise ErroUrl("URL com credencial recusada.")
    try:
        porta = p.port
    except ValueError:
        raise ErroUrl("porta inválida na URL.")
    if porta not in (None, 443):
        raise ErroUrl("porta fora do padrão recusada.")
    host = (p.hostname or "").lower()
    if host not in hosts:
        raise ErroUrl("host fora da lista permitida: %s" % host)
    if p.fragment:
        raise ErroUrl("URL com fragmento recusada.")
    return url


def _so(padrao, valor, nome):
    if not isinstance(valor, str) or not re.fullmatch(padrao, valor):
        raise ErroArgumento("%s inválido: formato não aceito." % nome)
    return valor


def validar_uf_ou_municipio(v):
    if isinstance(v, str) and re.fullmatch(r"[A-Za-z]{2}", v):
        if v.upper() not in UFS:
            raise ErroArgumento("sigla de UF desconhecida.")
        return v.upper()
    return _so(r"\d{7}", v, "uf/município (use sigla de 2 letras ou código IBGE de 7 dígitos)")


def validar_agregado(v):
    return _so(r"\d{1,6}", v, "agregado")


def validar_variavel(v):
    return _so(r"\d{1,6}", v, "variável")


def validar_localidade(v):
    return _so(r"N[1-7]\[(all|\d{1,7}(,\d{1,7}){0,19})\]", v, "localidade (ex.: N6[2304400])")


def validar_periodo(v):
    return _so(r"-\d{1,3}|\d{4,6}(-\d{4,6})?|\d{4,6}(\|\d{4,6}){1,9}", v, "período")


def validar_serie(v):
    return _so(r"\d{1,6}", v, "série")


def validar_ultimos(v):
    _so(r"\d{1,3}", v, "quantidade")
    n = int(v)
    if not 1 <= n <= 100:
        raise ErroArgumento("quantidade fora de 1 a 100.")
    return n


def validar_busca(v):
    return _so(r"[a-z0-9_-]{2,40}", v.lower() if isinstance(v, str) else v, "busca (minúsculas, dígitos, - e _)")


def cnpj_valido(c):
    if not isinstance(c, str) or not re.fullmatch(r"\d{14}", c) or len(set(c)) == 1:
        return False
    for n in (12, 13):
        pesos = list(range(n - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(int(d) * p for d, p in zip(c[:n], pesos))
        dv = 11 - soma % 11
        dv = 0 if dv >= 10 else dv
        if int(c[n]) != dv:
            return False
    return True


def validar_cnpj(v):
    _so(r"\d{14}", v, "CNPJ (14 dígitos, só números)")
    if not cnpj_valido(v):
        raise ErroArgumento("CNPJ com dígito verificador errado; nada foi consultado.")
    return v


# ---------- rede ----------

class _SemRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _normalizar(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


TETO_TEXTO = 300  # caracteres por campo de texto vindo da API


def _livre(valor):
    """Texto livre da API (nome, razão social, descrição): é dado de terceiro, passa pelo filtro de ficha.

    Só texto e número saem, cortados em TETO_TEXTO; objeto ou lista no lugar do texto vira None.
    """
    if valor is None or isinstance(valor, (dict, list, bool)):
        return None
    return ler_ficha.sanear_livre(valor, teto=TETO_TEXTO)


def _t(valor):
    """Qualquer campo de texto da API: número passa como está; texto passa por `_livre`; o resto some."""
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, (int, float)):
        return valor
    return _livre(valor) if isinstance(valor, str) else None


def _serie(valor):
    """Campo `serie` do agregado: só os valores numéricos de um objeto; texto e aninhamento saem."""
    if isinstance(valor, dict):
        # a chave também é texto da API: só período numérico (IBGE: 4 a 8 dígitos) passa
        return {k: v for k, v in valor.items() if re.fullmatch(r"\d{4,8}", str(k))
                and isinstance(v, (int, float)) and not isinstance(v, bool)}
    return _t(valor)


def _leva_razao_social(j):
    """Razão social só sai para natureza que a tem própria (órgão, sociedade, associação).

    Pessoa física, empresário individual, EI/EIRELI, MEI, LTDA e natureza não informada não levam: a razão
    social delas costuma ser o nome da pessoa (LTDA: nome do sócio). Faixas pela primeira posição do código (1, 2 e 3).
    """
    cod = str(j.get("codigo_natureza_juridica") or "")
    nat = _normalizar(j.get("natureza_juridica"))
    if not cod.isdigit() or cod[0] not in "123":
        return False
    if cod in NATUREZAS_INDIVIDUAIS or cod in NATUREZAS_SEM_NOME or "individual" in nat or "eireli" in nat:
        return False
    return j.get("opcao_pelo_mei") is not True


class Cliente:
    def __init__(self, bases=None, validar=validar_url, timeout=TIMEOUT, teto=TETO_BYTES,
                 espera_repeticao=1.0, usar_cache=True, validade_cache=VALIDADE_CACHE_S,
                 prazo=PRAZO_TOTAL):
        self.bases = dict(BASES if bases is None else bases)
        self.validar = validar
        self.timeout = timeout
        self.teto = teto
        self.prazo = prazo
        self.espera = espera_repeticao
        self.usar_cache = usar_cache
        self.validade = validade_cache
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _SemRedirect)

    def _prazo_estourado(self):
        return ErroFetch("a fonte demorou mais que o prazo de %d s; consulta cancelada." % self.prazo)

    def _ler_corpo(self, r, fim):
        """Lê em blocos conferindo o relógio: um servidor gotejando não segura a consulta além do prazo."""
        ler = getattr(r, "read1", r.read)
        corpo = bytearray()
        while len(corpo) <= self.teto:
            if time.monotonic() > fim:
                raise self._prazo_estourado()
            bloco = ler(min(65536, self.teto + 1 - len(corpo)))
            if not bloco:
                break
            corpo += bloco
        return bytes(corpo)

    def _tentar(self, url, fim):
        if time.monotonic() > fim:
            raise self._prazo_estourado()
        req = urllib.request.Request(url, headers={
            "User-Agent": "raiz-mestra/1.0 (consulta de dados publicos)",
            "Accept": "application/json",
        })
        try:
            with self._opener.open(req, timeout=self.timeout) as r:
                corpo = self._ler_corpo(r, fim)
        except urllib.error.HTTPError as e:
            c = e.code
            e.close()
            if 300 <= c < 400:
                raise ErroFetch("redirecionamento recusado (HTTP %d)." % c)
            if c == 429:
                raise ErroFetch("limite de requisições da fonte atingido (HTTP 429); espere e tente de novo, ou peça o dado manualmente.")
            if 500 <= c < 600:
                raise _Transitorio("HTTP %d" % c)
            raise ErroFetch("a fonte respondeu HTTP %d." % c)
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as e:
            raise _Transitorio("falha de rede (%s)" % type(e).__name__)
        if len(corpo) > self.teto:
            raise ErroFetch("resposta maior que o teto de %d bytes; reprovada." % self.teto)
        return corpo

    def get_json(self, url):
        self.validar(url)
        fim = time.monotonic() + self.prazo
        try:
            corpo = self._tentar(url, fim)
        except _Transitorio:
            time.sleep(self.espera)
            try:
                corpo = self._tentar(url, fim)
            except _Transitorio as e:
                raise ErroFetch("a fonte não respondeu após 1 repetição: %s." % e)
        try:
            return json.loads(corpo.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, RecursionError):
            raise ErroFetch("a resposta não é JSON válido.")

    # ---------- cache ----------

    def _arq_cache(self, url):
        nome = hashlib.sha256(url.encode("utf-8")).hexdigest()[:40] + ".json"
        return dados.dentro_da_pasta(dados.pasta_dados() / "cache_publico" / nome)

    def _ler_cache(self, url):
        if not self.usar_cache:
            return None
        try:
            arq = self._arq_cache(url)
            if time.time() - arq.stat().st_mtime > self.validade:
                return None
            obj = json.loads(arq.read_text(encoding="utf-8"))
            if isinstance(obj, dict) and obj.get("fonte") == url:
                obj["do_cache"] = True
                return obj
        except (OSError, ValueError, dados.ErroDados):
            return None
        return None

    def _gravar_cache(self, url, saida):
        if not self.usar_cache:
            return
        try:
            arq = self._arq_cache(url)
            arq.parent.mkdir(parents=True, exist_ok=True)
            tmp = arq.with_name(arq.name + ".tmp")
            tmp.write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, arq)
        except (OSError, dados.ErroDados):
            pass  # cache é conveniência; falhar nele não reprova a consulta

    def _resolver(self, url, resumir):
        guardado = self._ler_cache(url)
        if guardado is not None:
            return guardado
        bruto = self.get_json(url)
        try:
            dados_res, avisos = resumir(bruto)
        except (RecursionError, AttributeError, TypeError):
            raise ErroFetch("formato inesperado da fonte; a resposta não serve ao resumo.")
        saida = {"fonte": url, "consultado_em": date.today().isoformat(), "dados": dados_res}
        if avisos:
            saida["avisos"] = avisos
        self._gravar_cache(url, saida)
        saida = dict(saida)
        saida["do_cache"] = False
        return saida

    # ---------- serviços ----------

    def ibge_localidades(self, alvo):
        alvo = validar_uf_ou_municipio(alvo)
        tipo = "estados" if not alvo.isdigit() else "municipios"
        url = "%s/api/v1/localidades/%s/%s" % (self.bases["ibge"], tipo, alvo)

        def resumir(j):
            if not isinstance(j, dict):
                raise ErroFetch("formato inesperado do IBGE (esperava um objeto).")
            if tipo == "estados":
                return {"id": _t(j.get("id")), "sigla": _t(j.get("sigla")), "nome": _t(j.get("nome")),
                        "regiao": _t((j.get("regiao") or {}).get("nome"))}, []
            uf = (((j.get("microrregiao") or {}).get("mesorregiao") or {}).get("UF") or {})
            uf = uf or ((j.get("regiao-imediata") or {}).get("regiao-intermediaria") or {}).get("UF") or {}
            return {"id": _t(j.get("id")), "nome": _t(j.get("nome")), "uf": _t(uf.get("sigla")),
                    "regiao": _t((uf.get("regiao") or {}).get("nome"))}, []

        return self._resolver(url, resumir)

    def ibge_agregado(self, agregado, variavel, localidade, periodo="-1"):
        agregado, variavel = validar_agregado(agregado), validar_variavel(variavel)
        localidade, periodo = validar_localidade(localidade), validar_periodo(periodo)
        url = "%s/api/v3/agregados/%s/periodos/%s/variaveis/%s?localidades=%s" % (
            self.bases["ibge"], agregado, urllib.parse.quote(periodo, safe="|-"), variavel,
            urllib.parse.quote(localidade, safe="[],"))

        def resumir(j):
            if not isinstance(j, list):
                raise ErroFetch("formato inesperado do IBGE (esperava uma lista).")
            out, cortado = [], False
            for v in j:
                if not isinstance(v, dict):
                    continue
                res = []
                for r in v.get("resultados") or []:
                    for s in (r.get("series") or []):
                        if len(res) >= 50:
                            cortado = True
                            break
                        loc = s.get("localidade") or {}
                        res.append({"localidade_id": _t(loc.get("id")), "localidade": _t(loc.get("nome")),
                                    "serie": _serie(s.get("serie"))})
                out.append({"variavel": _t(v.get("variavel")), "unidade": _t(v.get("unidade")), "resultados": res})
            return out, (["resumo cortado em 50 séries"] if cortado else [])

        return self._resolver(url, resumir)

    def bcb_sgs(self, serie, ultimos=1):
        serie = validar_serie(serie)
        n = validar_ultimos(str(ultimos))
        url = "%s/dados/serie/bcdata.sgs.%s/dados/ultimos/%d?formato=json" % (self.bases["bcb"], serie, n)

        def resumir(j):
            if not isinstance(j, list):
                raise ErroFetch("formato inesperado do Banco Central (esperava uma lista).")
            return {"serie": serie, "pontos": [{"data": _t(p.get("data")), "valor": _t(p.get("valor"))}
                                              for p in j if isinstance(p, dict)]}, []

        return self._resolver(url, resumir)

    def tse_pacotes(self, busca=None):
        if busca is None:
            url = "%s/api/3/action/package_list" % self.bases["tse"]
        else:
            url = "%s/api/3/action/package_search?q=%s&rows=10" % (self.bases["tse"], validar_busca(busca))

        def resumir(j):
            r = j.get("result") if isinstance(j, dict) else None
            if busca is None:
                if not isinstance(r, list):
                    raise ErroFetch("formato inesperado do TSE (esperava uma lista de pacotes).")
                return {"total": len(r), "pacotes": [_livre(x) for x in r[:100]]}, (
                    ["lista cortada em 100 nomes"] if len(r) > 100 else [])
            itens = (r or {}).get("results") if isinstance(r, dict) else None
            if not isinstance(itens, list):
                raise ErroFetch("formato inesperado do TSE (esperava resultados de busca).")
            # descrição: a checagem de instrução vê o texto inteiro e só depois corta em 200 (adversario-4 R-04)
            return {"total": _t(r.get("count")), "pacotes": [
                {"nome": _livre(i.get("name")), "titulo": _livre(i.get("title")),
                 "descricao": ler_ficha.sanear_livre(i.get("notes"), teto=200)
                 if isinstance(i.get("notes"), str) else None} for i in itens if isinstance(i, dict)]}, []

        return self._resolver(url, resumir)

    def cnpj(self, numero):
        numero = validar_cnpj(numero)
        url = "%s/api/cnpj/v1/%s" % (self.bases["brasilapi"], numero)

        def resumir(j):
            if not isinstance(j, dict):
                raise ErroFetch("formato inesperado da BrasilAPI (esperava um objeto).")
            nat = j.get("natureza_juridica")
            d = {"cnpj": numero, "situacao": _livre(j.get("descricao_situacao_cadastral")),
                 "cnae_fiscal": _t(j.get("cnae_fiscal")), "cnae_descricao": _livre(j.get("cnae_fiscal_descricao")),
                 "municipio": _livre(j.get("municipio")), "uf": _t(j.get("uf")),
                 "data_inicio_atividade": _t(j.get("data_inicio_atividade")), "natureza_juridica": _livre(nat)}
            avisos = ["quadro societário, telefone, e-mail e endereço não são gravados."]
            if _leva_razao_social(j):
                d["razao_social"] = _livre(j.get("razao_social"))
                d["nome_fantasia"] = _livre(j.get("nome_fantasia"))
                avisos.append("razão social pode conter nome de pessoa em casos raros; confira antes de citar.")
            else:
                avisos.append("dados pessoais omitidos: natureza de pessoa física, empresário individual, EI/EIRELI, "
                              "MEI ou não informada; razão social e nome fantasia não foram gravados.")
            return d, avisos

        return self._resolver(url, resumir)


# ---------- linha de comando ----------

USO = ("uso: fetch_publico.py [--sem-cache] <subcomando> ...\n"
       "  ibge-localidades <uf|municipio>\n"
       "  ibge-agregado <agregado> <variavel> <localidade> [periodo]\n"
       "  bcb-sgs <serie> [ultimos N]\n"
       "  tse-pacotes [busca]\n"
       "  cnpj <14 dígitos>")


def main(argv=None, cliente=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    sem_cache = False
    if a and a[0] == "--sem-cache":
        sem_cache = True
        a = a[1:]
    if not a:
        print(USO)
        return 2
    cmd, args = a[0], a[1:]
    cli = cliente or Cliente(usar_cache=not sem_cache)
    try:
        if cmd == "ibge-localidades" and len(args) == 1:
            r = cli.ibge_localidades(args[0])
        elif cmd == "ibge-agregado" and len(args) in (3, 4):
            r = cli.ibge_agregado(*args)
        elif cmd == "bcb-sgs" and len(args) in (1, 3) and (len(args) == 1 or args[1] == "ultimos"):
            r = cli.bcb_sgs(args[0], args[2] if len(args) == 3 else 1)
        elif cmd == "tse-pacotes" and len(args) <= 1:
            r = cli.tse_pacotes(args[0] if args else None)
        elif cmd == "cnpj" and len(args) == 1:
            r = cli.cnpj(args[0])
        else:
            print(USO)
            return 2
    except (ErroArgumento, ErroUrl, dados.ErroDados) as e:
        print("argumento recusado: %s" % e)
        return 2
    except ErroFetch as e:
        print("consulta reprovada: %s" % e)
        return 1
    for av in r.get("avisos", []):
        print("aviso: %s" % av, file=sys.stderr)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
