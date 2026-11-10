## Regra zero verificável (T-E1.5)

Antes de entregar qualquer empreitada, o orquestrador grava a entrega num arquivo no formato de `moldes/entrega.md` e roda, nesta ordem:

1. `python3 scripts/rotular.py <entrega.md>`: confere a forma (cabeçalho, 8 seções, rótulo e fonte por linha, número da prosa presente na tabela Números). Não confere verdade.
2. `python3 scripts/lint_entrega.py <entrega.md> --pesquisa <arquivo-ou-pasta>` (um `--pesquisa` por fonte lida): reprova percentual ou adoção ligados a [simulação]/[hipótese], frase normativa fora de "Perguntas para o profissional", trecho de 8 palavras ou mais copiado da pesquisa sem aspas e fonte, ausência de "O que isto não prova" e "Limites desta análise", e as regras do modo eleitoral e do tamanho E3.

Exit 1 em qualquer um: o orquestrador corrige o que a mensagem aponta (arquivo:linha) e roda de novo. Não entrega com exit 1 e não ajusta o texto só para escapar do padrão.

Aprovação nos dois scripts quer dizer "forma certa e nenhum padrão proibido da lista". Não quer dizer que os fatos sejam verdadeiros nem que a análise esteja certa: isso é o portão 2 (juiz). O README deve listar o que os lints não pegam (ver o topo de cada script).
