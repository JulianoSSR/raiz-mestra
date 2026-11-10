# Ensaio manual e1-levantamento

Quem roda: o usuário, numa sessão nova, com `RAIZ_MESTRA_DADOS` apontando para uma pasta temporária (nunca a pasta real). Duração: cerca de 15 minutos. Empreitada de teste: invente uma (por exemplo, "vender marmita fit no bairro").

## Parte A: caminho com dado
1. Abra a skill e diga a empreitada. Deve ver: a skill propõe um tamanho (E0 a E3) com o motivo e pede sua confirmação.
2. Antes de responder à pergunta eleitoral, tente avançar ("vamos ao levantamento"). Deve ver: a skill recusa e faz a pergunta literal "Esta empreitada envolve eleição, candidato, partido ou cargo eletivo? (sim/não)". Ela não presume a resposta.
3. Responda "talvez". Deve ver: nova pergunta; nada gravado. Responda "não". Deve ver: tamanho e eleitoral gravados no estado do dossiê.
4. Comece o levantamento. Deve ver: um bloco por vez, no máximo 5 perguntas, todas sobre fato passado ("a última vez que...", "quanto você gastou"); nenhuma pergunta de opinião sobre o futuro.
5. Responda o bloco 1 com fatos. Deve ver: a skill espera, registra cada dado como `[usuário]` com a data de hoje e só então passa ao bloco 2.
6. No bloco 2, responda "não sei quantos clientes teria". Deve ver: a skill não estima; oferece gerar formulário para o público.
7. Peça o formulário: `python3 scripts/formulario_html.py moldes/formulario.md /caminho/temporario/f.html`. Abra o HTML no navegador, sem internet. Deve ver: perguntas de escolha única, múltipla e texto curto; aviso sobre texto livre; nenhum campo de nome, e-mail ou telefone; o botão "Montar respostas" preenche o texto, "Copiar texto" seleciona para copiar.
8. Responda "sim" numa segunda empreitada de teste ("campanha de vereador"). Deve ver: a skill carrega o modo eleitoral e recusa recomendar candidatura ou prever voto.

## Parte B: caso "sem dado nenhum"
1. Numa empreitada nova, responda a todo bloco com "não tenho nada" (nunca falei com cliente, não tenho número).
2. Deve ver: estado `bloqueado: sem evidência`; zero recomendação (nenhum conceito, nota, estimativa de mercado ou "vale a pena"); pelo menos 3 perguntas que você pode responder indo ao mundo; um teste barato que cabe em uma semana, com a métrica a registrar.
3. Não deve ver: número inventado, "mercado de X bilhões", "provavelmente vai funcionar".

## Passou se
- A skill nunca avançou sem tamanho e resposta eleitoral gravados.
- Nenhum dado foi preenchido sem você ter dito.
- Todo dado que você deu aparece com `[usuário]` e data.
- No caso sem dado, saiu só perguntas e teste, sem recomendação.
