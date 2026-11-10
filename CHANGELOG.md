# Mudanças

## 0.1.1 — 2026-11-10

Revisão da E1 (verificador, adversário, Resina e juiz) e conserto dos itens graves.

- `dossie.py marcar <slug> entrega` exige `--evidencia`, roda `rotular.py` e `lint_entrega.py`, confere o cabeçalho contra as respostas do dossiê e grava o sha256.
- Lint de entrega: texto antes da primeira seção reprova; tabela fora de Fatos e Números vira prosa; regra de tamanho E3 vale para todas as seções; seção extra reprova.
- Leitor só com WebFetch e WebSearch; retorno de texto livre de API passa por filtro de instrução.
- Ficha: cargo com cidade é identificação; cidade e tratamento sem distinção de caixa.
- Limpeza: CPF, CEP, telefone e logradouro em mais formatos; nomes em NFC; mapa com mkstemp e 0o600.
- Permissões 0o700 nas pastas de dados criadas pela skill; caminho relativo nas mensagens.
- `hash_arvore.py` inclui diretórios vazios, links e modo; ignora só ruído.

Não feito (ver README, "O que ainda não está garantido"): retenção de dados originais, gravação concorrente, saída existente sobrescrita, fechamento sem entrega, ensaios não executados.

## 0.1.0 — 2026-11-09

Primeira entrega (E1 Raiz). Sem painel de personas.

- Dossiê por empreitada com estado em disco, passos idempotentes e fechamento que exige registro de aprendizado.
- Triagem por tamanho (E0 a E3) e pergunta eleitoral obrigatória.
- Levantamento em blocos e formulário para o público em página única, sem rede.
- Dado público por script (IBGE, Banco Central, TSE, CNPJ), com lista fixa de endereços, sem redirecionamento e sem nome de pessoa em cache.
- Agente leitor só de leitura e validador da ficha que ele devolve. A busca na web fica desligada até o ensaio de isolamento ser executado.
- Troca de nomes, limpeza heurística de dado pessoal e validador de ficha de persona.
- Verificadores da entrega: rótulo e fonte em cada fato e número; barreira a previsão, parecer jurídico, trecho copiado, modo eleitoral e dinheiro alto sem coleta real.
- Papéis de entrevistador, mapeador, pré-mortem e juiz; moldes de dossiê, formulário, ficha e entrega.

Não feito nesta versão: painel, propagação em rede, medição de consumo, parada limpa, prova de fogo. A resolução do TSE sobre IA em campanha não foi lida na fonte oficial.
