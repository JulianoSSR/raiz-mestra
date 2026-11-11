# Mudanças

## Não publicado — 2026-11-11

Conserto da leva de 2026-11-10 (dossiê, rótulo e lint, formulário e ficha, leitor).

- `dossie.py desmarcar <slug> <passo>`: desfaz a marcação de um passo e guarda o registro anterior em "desmarcados" no dossiê. Com a entrega marcada, `responder` de tamanho ou eleitoral é recusado até desmarcar.
- `dossie.py fechar` reconfere o sha256 e o cabeçalho da entrega marcada; fontes de pesquisa registradas.
- Rótulo e lint: a negação em "não prova" e em "Limites" vale na frase reunida; frase partida por linha em branco, item de lista ou linha de tabela é juntada; multiplicador composto ("2 mil e 500") vira um número só.
- Formulário recusa pedido de dado pessoal; validador de ficha com limite de 1024 caracteres; `test_orfas` mede alcance (confere o texto, não o uso).
- Ficha: cidade em minúsculo só conta colada a cargo público. "Secretário de Saúde" ainda casa como cargo + cidade (falso alarme, ver README).
- Ficha: tratamento (seu, dr., sr., sra.…) seguido de nome comum em minúsculo volta a reprovar, pela lista `NOMES_COMUNS` (não é lista completa). Com revisão marcada, vira aviso fora do modo eleitoral.
- Ficha: origem preenchida com o resto do modelo deixado reprova. Trecho `<...>`, linha entre parênteses e seção sem texto são erros do `ficha_lint`.
- Limpeza: CEP, toda sequência de oito dígitos vira `[cep removido]`, inclusive datas e números de pedido. Perda declarada: "mora em fortaleza" fora de cargo deixou de ser detectado (regressão R-4 consertada).
- `dossie.py marcar <slug> entrega` grava o caminho absoluto da entrega, para `fechar` funcionar de outra pasta.
- Leitor: `fetch_publico` com teto de 300 caracteres no retorno (S-2).
- `skill-trechos/` saiu do repositório, com o teste correspondente; a justificativa está no registro da tarefa.
- Revisão de G8 e G9 (resina-2, adversario-3 e adversario-4), consertada: os campos de texto que a skill lê passam pelo filtro de instrução e pelo teto (`_t`); números passam como número; `serie` só com valores numéricos e chave de período; contagem do TSE passa por `_t`; descrição do TSE tem a checagem antes do corte de 200; `professora` e `professor` contam como tratamento; "número 1234" e fixo com espaço saem na limpeza.
- LTDA (2062) não leva razão social nem nome fantasia, por decisão do usuário em 2026-11-11.
- Atenção ao atualizar: apague a pasta `cache_publico`. O cache de 24 h gravado antes desta versão pode devolver campos sem o filtro. Natureza 2321 (advocacia individual) não leva razão social. Lint da ficha reprova CEP e endereço. Telefone reconhece E.164, `wa.me/`, CPF com hífen, CEP com espaço e 0800. Separação de fichas só por `\n`. Padrão de `<...>` só casa texto do molde. Testes em `testes/test_revisao_g8_g9.py`.
- Riscos declarados resolvidos (impl-final-1, 2026-11-11): endereço de Brasília (SQS, QI, bloco, apto, quadra e lote) e logradouros Ladeira, Vila, Campo etc. saem; e-mail com "(at)", "[at]" ou "arroba" sai; intervalo de anos não vira telefone; instrução reformulada passa também por cópia normalizada (letras de outro alfabeto, separadores, leet) e ganhou padrões de imperativo.
- Limitações novas e antigas, declaradas no README: instrução reformulada fora dessas construções segue sem marca (contenção = leitor isolado, ensaio não executado); fixo real com cara de ano ("2020-1999") sai; rótulos diferentes para e-mail; "Campo"/"Vila"/"Ponte" + número saem como endereço; "QI 120" e "Bloco A" saem fora de endereço; russo, grego e código com dígito podem sair marcados como `[suspeito]`; linha inteira entre parênteses sem dois-pontos nem número é tratada como orientação do modelo.
- Correção da revisão final (impl-final-3, 2026-11-11): falsos positivos de "bloco a bloco", "cada bloco" e "apartamento 2 quartos" e de "arroba" em cotação não apagam mais texto comum; quadra com QNM, QE, Qd., Lt., apt. e nº passa a sair. Limites novos declarados no README: "bloco" minúsculo com letra fora de a, e ou o sai; "apartamento" + número sai fora da lista fechada de palavras seguintes; "arroba" com letra acentuada antes ou domínio com "www." não sai.
- SKILL.md, `moldes/entrega.md` e `moldes/ficha.md` atualizados (`ler_ficha`, `--so-limpeza`, `desmarcar`).

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
