## Entrega sem painel (T-E1.8)

Sequência após o levantamento e o mapa: conceitos, pré-mortem, entrega, juiz, fechamento. Em todos os comandos, `<slug>` é o dossiê e `$D` é `<pasta de dados>/dossies/<slug>`.

1. **Conceitos.** Escreva 2 ou 3 conceitos só com o que está em Fatos e Números (ponteiros F#/N#). Cada um: para quem é, o que sustenta, o que é hipótese e critério de abandono com data. Se `tamanho: E3` e não há coleta real registrada, os conceitos viram perguntas em aberto e o teste barato, sem recomendação. Se `eleitoral: sim`, leia `referencias/eleitoral.md` antes e respeite os cinco itens proibidos.
   `python3 scripts/dossie.py marcar <slug> conceitos --evidencia <arquivo>`
2. **Pré-mortem.** Em contexto limpo (subagente com `papeis/pre-mortem.md`), entregue só o dossiê resumido e os conceitos. Corrija conceito ou teste onde uma causa mostrou furo. Resuma na seção "Pré-mortem".
   `python3 scripts/dossie.py marcar <slug> pre-mortem --evidencia <arquivo>`
3. **Entrega.** Copie `moldes/entrega.md` para `$D/entrega.md` e preencha. Rode, nesta ordem, e corrija até os dois darem exit 0:
   `python3 scripts/rotular.py $D/entrega.md`
   `python3 scripts/lint_entrega.py $D/entrega.md --pesquisa <fonte>` (um `--pesquisa` por fonte lida)
   Só depois: `python3 scripts/dossie.py marcar <slug> entrega --evidencia $D/entrega.md --pesquisa <fonte>` (os mesmos `--pesquisa` do lint). O `dossie.py` exige a `--evidencia`, roda de novo `rotular.py` e `lint_entrega.py` sobre o arquivo e só grava o passo, com o sha256 da entrega conferida, se os dois derem exit 0; senão mostra a saída do verificador e sai com exit 1. Passo já marcado não é reconferido: se a entrega mudar depois, rode os dois scripts de novo e compare o sha256 com o do `estado`.
4. **Juiz.** Em contexto limpo (subagente com `papeis/juiz.md`), entregue a entrega, o dossiê e a pesquisa. Veredito `devolvida`: cada achado volta para correção, depois repita rotular, lint e juiz. Achado do juiz não se ignora nem se discute; se o orquestrador discorda, mostra a divergência ao usuário.
5. **Mostrar ao usuário.** A entrega só é apresentada como pronta com `rotular.py` e `lint_entrega.py` em exit 0 **e** veredito `aprovada` do juiz. Antes disso, só como rascunho, dizendo qual portão falta. Diga também, na mesma resposta, que os lints são heurísticos e o que o juiz não pôde conferir.
6. **Fechamento.** Pergunte o que a skill aprendeu com esta empreitada (proposta de melhoria, sujeita à aprovação do usuário) e grave:
   `python3 scripts/dossie.py responder <slug> aprendizado "proposto"` ou `"nada a propor"`
   `python3 scripts/dossie.py marcar <slug> aprendizado`
   `python3 scripts/dossie.py fechar <slug>` (falha sem a resposta de aprendizado).

Exit 1 em qualquer script: corrija o que a mensagem aponta (arquivo:linha); não ajuste o texto só para escapar do padrão.
