## Dado pessoal (T-E1.7)

Antes de aceitar material de gente real (transcrição, mensagem, anotação):

1. Leia ao usuário o aviso de consentimento de `moldes/ficha.md`. Sem "sim", o material não entra. Diga também que o texto já colado na conversa foi enviado ao provedor do modelo.
2. Peça a lista de nomes (um por linha, inclusive primeiro nome isolado se for o caso) e salve em arquivo.
3. Rode `python3 scripts/pseudonimizar.py <entrada.txt> <saida.txt> --nomes <lista.txt> --dossie <slug>` ANTES de qualquer subagente receber texto de gente real. Subagente só lê a saída. Sem lista, rode com `--so-limpeza` e avise que os nomes não foram trocados. O mapa nome-código fica só na pasta de dados do dossiê; nunca o mostre nem o passe a subagente.
4. Repita ao usuário a contagem impressa e o aviso: limpeza por padrão, não é garantia.
5. Rode `python3 scripts/ficha_lint.py <ficha.md>` em toda ficha (com `--eleitoral` em empreitada eleitoral). Exit 1: corrija ou recuse; não entregue ficha reprovada. Aviso de cargo + cidade: confirme a revisão com o usuário.
6. Nunca guarde opinião política, saúde ou religião por indivíduo, nem a pedido. Só agregado.
7. Diga ao usuário o que os scripts não pegam: apelido sem tratamento, profissão rara em cidade pequena, descrição física, nome fora da lista, endereço por extenso sem número, identificação por combinação de detalhes.
