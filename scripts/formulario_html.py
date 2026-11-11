#!/usr/bin/env python3
"""Gera uma página HTML estática (um arquivo, sem rede) a partir do molde de formulário.

Uso: formulario_html.py <formulario.md> <saida.html>
Lê a parte "# Formulário para o público" do molde (ou o arquivo todo, se não houver).
Perguntas: `N. [unica|multipla|texto] Pergunta | opção | opção`.

Pergunta (ou opção) que pede nome da pessoa, CPF, telefone, e-mail ou endereço reprova,
e a página não é gerada. A conferência é por lista de palavras: não pega pedido escrito
de outro jeito ("como te encontro?", "RG", "onde você mora?") e reprova também a pergunta
que só cita a palavra ("não escreva seu telefone"). O campo de texto livre continua
aceitando o que a pessoa digitar.
"""
import html
import re
import sys
import unicodedata
from pathlib import Path

SECAO = "# Formulário para o público"
PERGUNTA = re.compile(r"^\s*\d+\.\s*\[(unica|multipla|texto)\]\s*(.+?)\s*$")

# Casados contra o texto em minúsculas e sem acento.
DADO_PESSOAL = (
    ("nome", re.compile(r"\bnome completo\b|\bsobrenome\b|\b(?:seu|teu) nome\b|\bnome d[eo] (?:voce|senhora?)\b"
                        r"|\bcomo (?:voce |o senhor |a senhora )?se chama\b")),
    ("CPF", re.compile(r"\bcpf\b")),
    ("telefone", re.compile(r"\btelefones?\b|\bcelular(?:es)?\b|\bwhats\s?app\b|\bzap\b")),
    ("e-mail", re.compile(r"\be-?mails?\b")),
    ("endereço", re.compile(r"\benderecos?\b|\bcep\b")),
)

CSS = (
    "body{font-family:sans-serif;max-width:40rem;margin:1rem auto;padding:0 1rem;line-height:1.4}"
    "fieldset{margin:1rem 0;border:1px solid #888;border-radius:6px}"
    "label{display:block;margin:.25rem 0}textarea{width:100%;box-sizing:border-box}"
    ".aviso{background:#fff4d6;color:#222;padding:.6rem;border-radius:6px}"
    "button{padding:.5rem 1rem;margin:.5rem .5rem .5rem 0}"
)

JS = """
function montar(){
  var f=document.getElementById('f');var out=[document.title];var n=0;
  var sets=f.querySelectorAll('fieldset');
  for(var i=0;i<sets.length;i++){
    var s=sets[i];var leg=s.querySelector('legend').textContent;var resp=[];
    var marcados=s.querySelectorAll('input:checked');
    for(var j=0;j<marcados.length;j++){resp.push(marcados[j].value);}
    var t=s.querySelector('textarea');
    if(t&&t.value.trim()){resp.push(t.value.trim());}
    n++;out.push(n+'. '+leg+' -> '+(resp.length?resp.join('; '):'(sem resposta)'));
  }
  document.getElementById('saida').value=out.join('\\n');
}
function copiar(){
  var s=document.getElementById('saida');s.select();
  try{document.execCommand('copy');}catch(e){}
}
"""


def _secao_publica(texto):
    linhas = texto.splitlines()
    for i, l in enumerate(linhas):
        if l.strip() == SECAO:
            return linhas[i + 1:]
    return linhas


def _sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", t)
                   if unicodedata.category(c) != "Mn").lower()


def dados_pessoais(texto):
    """Devolve [(linha, [dado])] das perguntas da parte pública que pedem dado pessoal."""
    todas = texto.splitlines()
    publica = _secao_publica(texto)
    desloc = len(todas) - len(publica)
    achados = []
    for i, l in enumerate(publica, desloc + 1):
        if not PERGUNTA.match(l):
            continue
        plano = _sem_acento(l)
        pedidos = [nome for nome, pad in DADO_PESSOAL if pad.search(plano)]
        if pedidos:
            achados.append((i, pedidos))
    return achados


def analisar(texto):
    """Devolve (titulo, blocos); bloco = (nome, [pergunta]); pergunta = (tipo, texto, [opcoes])."""
    titulo = "Formulário"
    blocos = []
    titulo_achado = False
    for l in _secao_publica(texto):
        if re.match(r"^# (?!#)", l) and not titulo_achado:
            titulo = l[2:].strip() or titulo
            titulo_achado = True
            continue
        if l.startswith("## "):
            blocos.append((l[3:].strip(), []))
            continue
        m = PERGUNTA.match(l)
        if m:
            tipo, resto = m.group(1), m.group(2)
            partes = [p.strip() for p in resto.split("|")]
            perg, opcoes = partes[0], [p for p in partes[1:] if p]
            if not blocos:
                blocos.append(("Perguntas", []))
            blocos[-1][1].append((tipo, perg, opcoes))
    return titulo, blocos


def gerar(texto):
    titulo, blocos = analisar(texto)
    e = lambda s: html.escape(s, quote=True)
    partes = [
        "<!doctype html>",
        '<html lang="pt-BR"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        "<title>%s</title>" % e(titulo),
        "<style>%s</style></head><body>" % CSS,
        "<h1>%s</h1>" % e(titulo),
        '<p class="aviso">Não escreva seu nome, e-mail nem telefone. '
        "O texto livre pode identificar você; se responder, seja breve e evite dados pessoais. "
        "Nada é enviado por esta página: você copia o texto e manda a quem pediu.</p>",
        '<form id="f" onsubmit="return false">',
    ]
    q = 0
    for nome, perguntas in blocos:
        partes.append("<h2>%s</h2>" % e(nome))
        for tipo, perg, opcoes in perguntas:
            q += 1
            partes.append("<fieldset><legend>%s</legend>" % e(perg))
            if tipo == "texto":
                partes.append(
                    '<textarea name="q%d" rows="3" maxlength="280" '
                    'aria-label="Resposta curta, opcional"></textarea>' % q
                )
            else:
                kind = "radio" if tipo == "unica" else "checkbox"
                for k, op in enumerate(opcoes):
                    partes.append(
                        '<label><input type="%s" name="q%d" value="%s"> %s</label>'
                        % (kind, q, e(op), e(op))
                    )
            partes.append("</fieldset>")
    partes += [
        "</form>",
        '<button type="button" onclick="montar()">Montar respostas</button>',
        '<button type="button" onclick="copiar()">Copiar texto</button>',
        '<textarea id="saida" rows="10" readonly aria-label="Texto das respostas"></textarea>',
        "<script>%s</script>" % JS,
        "</body></html>",
    ]
    return "\n".join(partes) + "\n"


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("uso: formulario_html.py <formulario.md> <saida.html>")
        return 2
    entrada, saida = Path(argv[0]), Path(argv[1])
    if not entrada.is_file():
        print("%s: arquivo de entrada não existe" % entrada)
        return 2
    texto = entrada.read_text(encoding="utf-8")
    _, blocos = analisar(texto)
    if not any(b[1] for b in blocos):
        print("%s: nenhuma pergunta no formato 'N. [unica|multipla|texto] ...'" % entrada)
        return 1
    pedem = dados_pessoais(texto)
    for n, pedidos in pedem:
        print("%s:%d: pergunta pede dado pessoal (%s); tire a pergunta. Página não gerada."
              % (entrada, n, ", ".join(pedidos)))
    if pedem:
        return 1
    saida.write_text(gerar(texto), encoding="utf-8")
    print("%s: página gerada" % saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
