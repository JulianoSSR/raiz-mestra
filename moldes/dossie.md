# O dossiê

O dossiê é a pasta onde fica o registro de uma empreitada, do começo ao fim. Cada empreitada tem o seu, com um nome curto (letras minúsculas, números e hífen, até 40 caracteres).

Ele fica na sua pasta de dados (`~/.raiz-mestra/dossies/<nome>/`, ou onde você apontar em `RAIZ_MESTRA_DADOS`). Nada dele sobe para o repositório da skill.

## O que tem dentro

- `estado.json`: onde a empreitada está. Guarda os passos já feitos (com data, hora e a evidência de cada um), as suas respostas (tamanho E0 a E3, se envolve eleição, e o registro de aprendizado) e a data de fechamento.
- Os demais arquivos de cada passo (levantamento, mapa, conceitos, pré-mortem, entrega) entram na mesma pasta, conforme a skill avança.

## Os passos, em ordem

triagem, levantamento, mapa, conceitos, pré-mortem, entrega, aprendizado.

## Regras que você vai sentir

- Depois da triagem, a skill só avança se você já tiver respondido o tamanho e se a empreitada envolve eleição, candidato, partido ou cargo eletivo.
- Marcar o mesmo passo duas vezes não muda nada.
- Para fechar, é preciso registrar o aprendizado: "proposto" ou "nada a propor".
- Se o `estado.json` estiver quebrado, a skill avisa e para. Ela não apaga nem reescreve o arquivo por conta própria.
