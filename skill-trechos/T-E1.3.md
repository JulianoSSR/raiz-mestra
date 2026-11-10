## Triagem (antes de qualquer levantamento)

Antes de levantar dados, classifique a empreitada e pergunte sobre eleição. O `dossie.py` recusa avançar enquanto `tamanho` e `eleitoral` não estiverem gravados.

**1. Tamanho.** Proponha um e mostre ao usuário o motivo em uma linha; ele pode corrigir. Na dúvida entre dois, suba um.
| Tam. | Quando | Liga | Desliga |
|---|---|---|---|
| E0 | conversa ou dúvida pontual | resposta direta; rótulo em todo número | dossiê, formulário, painel |
| E1 | decisão pequena e reversível | 1 bloco de levantamento, entrega curta com teste barato | painel, mapa extenso |
| E2 | dinheiro ou meses em jogo | levantamento completo, mapa do que existe, pré-mortem, entrega completa, painel se instalado | nada |
| E3 | dinheiro alto ou decisão difícil de desfazer | tudo de E2; registros de coleta real antes de qualquer recomendação; perguntas ao profissional obrigatórias | recomendação sem registro de coleta |

Gravar: `python3 scripts/dossie.py responder <slug> tamanho E2`. Reclassificar só para cima, e regrave.

**2. Pergunta eleitoral, obrigatória, ao usuário, nunca presumida.** Faça literalmente: "Esta empreitada envolve eleição, candidato, partido ou cargo eletivo? (sim/não)". Mesmo que o tema pareça óbvio, pergunte. Resposta diferente de sim ou não, ou "não sei": pergunte de novo, não grave. Gravar: `python3 scripts/dossie.py responder <slug> eleitoral sim` (ou `não`).
- `sim`: carregue `referencias/eleitoral.md` e passe a seção 3 dela como checklist ao verificador.
- Em qualquer resposta, `referencias/travas-legais.md` vale.

**3. Referências sob demanda.** `referencias/metodos.md` quando for escolher o método do passo; `referencias/travas-legais.md` quando surgir pergunta jurídica, contábil, de dado pessoal ou de cópia. Não cite artigo, número de lei ou prazo que não esteja nelas com URL oficial e data.
