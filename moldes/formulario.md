# Molde de levantamento e formulário

Duas partes. A primeira o orquestrador usa na conversa (papel entrevistador). A segunda, sob o título "Formulário para o público", é o que o usuário manda a clientes ou conhecidos; `scripts/formulario_html.py` transforma só essa parte em página HTML.

Regras das duas partes: toda pergunta é sobre fato passado e verificável (o que a pessoa fez, gastou, usou, tentou), nunca opinião sobre o futuro nem sobre a ideia. Bloco com no máximo 5 perguntas. Cada resposta recebe rótulo `[usuário]` com a data.

# Levantamento (conversa)

## Bloco 1: quem é você e o que já tem
- Qual é a sua ocupação hoje e há quanto tempo?
- O que você já tem pronto para esta empreitada (dinheiro guardado, equipe, clientes, ponto, equipamento, contatos)?
- O que você já fez antes que se parece com isto?
- Quantas horas por semana você tem livres para isto, hoje?
- Quem decide e quem paga, se não for você?

## Bloco 2: o problema e quem o tem
- Qual foi a última vez que você viu esse problema acontecer? Quando e com quem?
- Quantas pessoas ou empresas você conhece que passaram por ele nos últimos 12 meses?
- O que aconteceu com elas por causa dele (perda de dinheiro, de tempo, de cliente)?
- Quanto isso custou, na última ocorrência que você conhece?
- Como você ficou sabendo?

## Bloco 3: o que essas pessoas fazem hoje
- O que elas fazem hoje para resolver, passo a passo, na última vez?
- Quanto pagam, em dinheiro ou horas, pela solução atual?
- Que ferramenta, serviço ou pessoa elas usam?
- Já trocaram de solução alguma vez? Por quê, e quando?
- O que fazem quando nada disso está disponível?

## Bloco 4: dinheiro, tempo e apetite
- Quanto dinheiro você pode perder nesta empreitada sem comprometer o resto da sua vida?
- Quanto tempo (meses) você aceita dedicar antes de decidir continuar ou parar?
- Quanto você já gastou nisto até hoje?
- Qual é a sua renda mensal mínima que precisa ser mantida enquanto isto roda?
- Quem mais depende desse dinheiro ou desse tempo?

## Bloco 5: o que já foi tentado
- O que você já testou com gente real (conversa, venda, anúncio, protótipo)? Quando?
- Qual foi o resultado, em números (conversas, respostas, vendas)?
- Quem se comprometeu com algo (pagou, marcou reunião, indicou alguém)?
- O que deu errado nessas tentativas?
- Que dado você tem registrado (planilha, mensagens, notas)?

## Bloco 6: critério de abandono
- Que resultado, em número e data, faria você parar?
- Que resultado, em número e data, faria você continuar?
- Quem você avisaria se parasse, e o que perderia?
- Qual é a data limite para decidir?
- Que evidência faria você mudar de rumo em vez de parar?

# Formulário para o público

Aviso para o usuário antes de mandar: não peça nome, e-mail nem telefone. Texto livre pode identificar quem responde; peça respostas curtas e opcionais. Formato das perguntas (lido por `scripts/formulario_html.py`):

`N. [unica] Pergunta | opção | opção` (escolha única), `N. [multipla] Pergunta | opção | opção` (várias), `N. [texto] Pergunta` (texto curto e opcional). Cada pergunta numa linha. Cada `## ` abre um bloco.

# Pesquisa rápida sobre [assunto]

## Sobre a sua última vez
1. [unica] Quando foi a última vez que você precisou resolver [problema]? | Nos últimos 7 dias | No último mês | Nos últimos 6 meses | Há mais tempo | Nunca precisei
2. [multipla] O que você usou nessa vez? | Fiz sozinho(a) | Pedi a um conhecido | Contratei alguém | Usei um aplicativo ou site | Não resolvi
3. [unica] Quanto você gastou, somando dinheiro? | Nada | Até R$ 50 | De R$ 50 a R$ 200 | Mais de R$ 200
4. [texto] Qual foi a parte mais trabalhosa? (curto, sem nome nem contato)
