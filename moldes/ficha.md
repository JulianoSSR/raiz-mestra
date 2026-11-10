# Molde da ficha de persona

A ficha descreve um tipo de pessoa em categorias. Não leva nome próprio, CPF, e-mail, telefone nem endereço. Valide toda ficha com `scripts/ficha_lint.py <ficha.md>` (e `--eleitoral` em empreitada eleitoral).

## Aviso de consentimento (o orquestrador lê ao usuário antes de aceitar material de gente real; não copiar para a ficha)

> Você vai me passar material de pessoas reais (entrevista, mensagem, anotação). Antes: (1) só use quem sabe e concordou que o conteúdo seja usado nesta análise; (2) o que você cola na conversa já é enviado ao provedor do modelo, e a limpeza que eu faço depois é heurística, não garantia; (3) eu não guardo opinião política, saúde nem religião de pessoa individual, só em agregado; (4) me dê a lista de nomes que devem virar código. Você confirma que tem o consentimento? Responda sim ou não.

Sem "sim" do usuário, o material de gente real não entra. A resposta registra-se no campo `consentimento:` de cada ficha.

## Modelo (copiar a partir daqui)

```
origem: arquetipo            # real | arquetipo
consentimento: nao se aplica # sim | nao se aplica (obrigatório "sim" se origem for real)
fonte:                       # id do registro de coleta; só quando origem for real
identificacao_indireta_revisada: nao   # sim | nao; "sim" só depois de reler a ficha

## Papel na decisão
(decide, paga, usa, influencia ou barra)

## Contexto de vida e trabalho
(categorias: ramo, porte, rotina; sem nome, bairro pequeno ou cargo + cidade)

## O que faz hoje para resolver o problema

## Restrições
(dinheiro, tempo)

## O que valoriza

## Do que desconfia
```

## Regras

- Nada de opinião política, saúde ou religião atribuída a uma pessoa. Isso só entra como número agregado de um grupo.
- Cargo (prefeito, vereador, secretário, diretor etc.) junto com cidade pode identificar: tire um dos dois ou releia e marque `identificacao_indireta_revisada: sim`. Em `--eleitoral` marcar não basta.
- O lint não pega apelido, profissão rara em cidade pequena, descrição física nem combinação de detalhes. A releitura humana continua necessária.
