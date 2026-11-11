# Raiz Mestra

**Da ideia ao plano com fonte.** Uma skill de agente que conduz uma empreitada (empresa, produto, jogo, campanha, imagem pessoal, negociação) perguntando antes de desenhar, buscando dado público do Brasil, mapeando o que já existe e atacando o próprio plano antes de entregar. Cada fato da entrega diz de onde veio.

Da mesma família da [Seiva](https://github.com/JulianoSSR/seiva) e da [Humanize-me Brasil-IA](https://github.com/JulianoSSR/humanize-me-brasil-ia).

## Leia antes de usar

- **Ela não prevê.** Não diz quantas pessoas vão comprar, aderir ou votar. Entrega objeções, comparações, o que ainda é hipótese e o próximo teste real, que é com gente de verdade.
- **Skill nenhuma fura cota de assinatura.** Se a sessão parar no meio, a Raiz Mestra retoma do estado gravado em disco, sem refazer o que já concluiu. Ela não promete rodar sem parar.
- **O que você cola na conversa já foi ao provedor do modelo.** A skill troca nomes e limpa dados por heurística antes de passar o texto a subagentes. O texto original continua no disco até você apagá-lo, e o envio ao provedor não tem como ser desfeito. Não cole o que não pode sair da sua máquina.
- **Os verificadores conferem forma, não verdade.** Eles conferem que cada linha das tabelas de fatos e números tem rótulo e fonte, e que os padrões proibidos listados não aparecem. Afirmação em prosa, sem número, não tem essa conferência. Não garantem que a fonte diz o que o texto afirma.
- **Dados e travas legais são do Brasil.** IBGE, Banco Central, TSE e consulta de CNPJ; LGPD e regras eleitorais brasileiras. Fora do Brasil, o método serve e os dados não.
- **Não substitui advogado nem contador.** Dúvida jurídica, contábil ou fiscal sai como pergunta para levar ao profissional.
- **Estado: versão 0.1.1, revisada e ainda sem uso real.** Sem painel de personas, sem medição de consumo, sem prova de fogo. Veja "O que existe hoje".

## O que existe hoje (entrega E1)

| Passo | O que faz |
|---|---|
| Triagem | Classifica o tamanho da empreitada (E0 a E3) e pergunta se envolve eleição |
| Levantamento | Entrevista em blocos sobre fatos passados; gera formulário em página única, sem rede, para mandar ao público |
| Mapa | Busca dado público por script; lê concorrentes com um agente que só lê |
| Conceitos e pré-mortem | Dois ou três caminhos com critério de abandono datado; ataque em contexto limpo |
| Entrega | Fatos e números com fonte, perguntas ao profissional, "o que isto não prova" |
| Fechamento | Correções viram proposta de aprendizado; o dossiê fecha |

Ainda não existe: painel de personas, propagação em rede, medição de consumo de tokens, parada limpa automática e a prova de fogo. Estão planejados nas entregas seguintes.

## Instalar

Em desenvolvimento, por link simbólico (Linux, macOS, WSL):

```bash
ln -s ~/projetos/raiz-mestra ~/.claude/skills/raiz-mestra
```

Para desfazer, remova só o link:

```bash
rm ~/.claude/skills/raiz-mestra
```

Como plugin do Claude Code (traz também o agente `leitor`), depois que o repositório estiver publicado. **Não testado ainda:**

```bash
claude plugin marketplace add JulianoSSR/raiz-mestra
```

```bash
claude plugin install raiz-mestra@raiz-mestra
```

Requisito: Python 3, só a biblioteca padrão. Nenhum pacote a instalar.

Testado em Linux sob WSL. **Não testado:** Windows nativo e macOS.

## Onde ficam os seus dados

Fora da pasta da skill, em `~/.raiz-mestra/`, ou na pasta que você indicar na variável `RAIZ_MESTRA_DADOS`. Cada empreitada é um dossiê. Atualizar ou remover a skill não apaga os dossiês.

## A busca na web começa desligada

O agente que lê páginas de concorrentes foi definido com ferramentas só de leitura. Se essa restrição vale de fato no seu aplicativo, só um ensaio diz. O roteiro está em `testes/ensaios/leitor-isolamento.md`. Enquanto ele não for executado e registrado como aprovado, a skill não usa busca na web: o mapa sai dos scripts de dado público e do texto que você colar.

## O que ainda não está garantido

Estes limites foram medidos na revisão de 2026-11-10 e continuam abertos. Cada um diz o que fazer.

- **Ensaios não executados.** `testes/ensaios/e1-levantamento.md`, `e1-ponta-a-ponta.md` e `leitor-isolamento.md` são roteiros; nenhum foi rodado. Até o do leitor ser registrado como aprovado, a busca web fica desligada.
- **Retorno do leitor sem filtro antes do orquestrador.** O texto que o leitor devolve entra no contexto antes de `ler_ficha.py`. Sem o ensaio, não se sabe se o modelo obedece a uma página hostil.
- **Entrega marcada não é reconferida.** Depois de `dossie.py marcar <slug> entrega`, mudar o arquivo não invalida o passo. O sha256 gravado mostra a mudança, mas nenhum comando compara sozinho. Se o juiz devolver a entrega, rode `rotular.py` e `lint_entrega.py` de novo e confira o sha256 no `estado`.
- **Sem `--pesquisa`, o trecho copiado não é conferido.** O `marcar entrega` aceita a entrega sem a checagem de cópia se você não listar as fontes.
- **Caso "sem dado nenhum" não tem teste automático.** Só o roteiro do ensaio cobre.
- **Dados em claro até apagar.** O original e a lista de nomes ficam no disco até você apagá-los; a skill não apaga.
- **Saída existente é sobrescrita.** `formulario_html.py` e `pseudonimizar.py` gravam em caminho já existente, inclusive por link simbólico, sem aviso. Não aponte a saída para um arquivo que você quer manter.
- **Fechamento não exige entrega.** `dossie.py fechar` aceita um dossiê sem o passo `entrega`; e `marcar` continua aceitando passos depois de fechado.
- **Gravação concorrente.** Dois comandos ao mesmo tempo no mesmo dossiê podem perder uma alteração. Uso sequencial não corre esse risco.
- **Ficha em lote sem teto.** `ler_ficha.py` não limita o número de fichas; a saída pode ser grande.

- **Cargo + cidade tem falso alarme.** Cidade conta em qualquer lugar pelo nome de capital ou pelo formato "de/em <Capitalizada>"; em minúsculo, só colada a cargo público ("prefeito de sobral"). Por isso "Secretário de Saúde" casa como cargo + cidade. Na ficha comum a saída é marcar `identificacao_indireta_revisada: sim`; em `--eleitoral` é tirar um dos dois.
- **Tratamento em minúsculo só pega nome da lista.** "seu joão" e "dr. carlos" são pegos porque estão em `NOMES_COMUNS`; nome comum fora dessa lista em minúsculo passa sem marca. A lista não é completa.
- **Datas e números de oito dígitos viram CEP.** `20261109` sai como `[cep removido]`. Telefone de dez dígitos sem pontuação não é pego.
- **Razão social de empresário individual não sai.** MEI, EI e EIRELI saem sem nome na saída e no cache, de propósito; sociedades e órgãos mantêm o nome. A tabela de naturezas jurídicas foi escrita sem conferir na fonte oficial (CONCLA), e os testes usam servidor local com códigos inventados.
- **Texto da API passa pelo filtro de instrução e pelo teto de tamanho nos campos que a skill lê** (IBGE, BCB, BrasilAPI, TSE e pacotes). Número passa como número; objeto ou lista no lugar de texto sai vazio. Chave de série do IBGE sai só se for período numérico (4 a 8 dígitos).
- **Cache de 24 h da versão anterior.** Quem atualizou a skill deve apagar a pasta `cache_publico` (fica na pasta de dados). Até apagar, o cache gravado antes desta correção pode devolver campos sem o filtro, por até 24 h.
- **Nome com apóstrofo reto não troca apóstrofo tipográfico.** "D'Ávila" na lista não casa "D’Ávila" no texto; o aviso de "nome não apareceu" sai.
- **LTDA não leva razão social nem nome fantasia.** Decisão do usuário, em 2026-11-11: a razão social de LTDA costuma trazer o nome do sócio. Quem precisar do nome da empresa consulta a fonte oficial e cita com a fonte. Sociedade individual de advocacia (2321) também não leva. Outras sociedades e órgãos mantêm o nome.
- **Prazo de leitura não cobre o cabeçalho HTTP.** Servidor que goteja só os cabeçalhos depende do timeout por operação (15 s).
- **Pastas que já existem com outra permissão não são corrigidas.** As permissões 0o700 valem para pastas criadas pela skill a partir desta versão.

## O que os verificadores não pegam

- **Fonte verdadeira.** Se a URL existe, se a data é real, se o número está certo.
- **Número por extenso** ("trinta por cento", "dois mil") e unidade trocada.
- **Previsão dita com outras palavras**, fora das listas de expressões.
- **Parecer jurídico dito de forma incomum** e recomendação implícita.
- **Cópia por paráfrase ou tradução**; só trecho de oito palavras iguais é detectado.
- **Dado pessoal fora do padrão:** apelido, endereço por extenso sem número, profissão rara em cidade pequena, descrição física, nome que você não listou, RG, placa, data de nascimento. Endereço de Brasília (SQS, quadra, lote) e e-mail com "(at)", "[at]" ou "arroba" saem desde a versão de 2026-11-11.
- **Instrução maliciosa reformulada** em página lida: o filtro reconhece padrões conhecidos, mais letras de outro alfabeto, separadores entre letras e leet nos casos comuns. Reformulação fora dessas construções passa sem marca. A saída real é o agente leitor isolado, cujo ensaio ainda não foi executado.
- **Rótulos diferentes para e-mail.** E-mail disfarçado sai como `[e-mail removido]`; o comum continua `[email removido]`.
- **Remoção a mais em endereço.** "Vila", "Campo" ou "Ponte" seguidos de número em até sete palavras saem como endereço ("Campo de futebol com 11 jogadores"). "QI 120" e "Bloco A" saem mesmo fora de endereço. "Bloco" minúsculo seguido de letra que não seja a, e ou o também sai ("vende bloco b inteiro"). "Apartamento" seguido de número só fica se a palavra seguinte estiver numa lista fechada (quartos, suítes, dormitórios, vagas, banheiros, cômodos): "Apartamento 2 salas amplas" sai.
- **E-mail disfarçado que não sai.** "arroba" com letra acentuada antes ("joão arroba gmail.com") e domínio que começa por "www." ficam como estão.
- **Marca a mais em instrução.** Texto legítimo em russo ou grego, código com dígito, e frases honestas com "Recomenda ... única" ou "Diga ao usuário" podem sair com `[suspeito]`.

Onde erram por excesso, geram falso alarme; onde erram por falta, deixam passar casos como os listados acima. Exemplos de falso alarme: todo número de onze dígitos é tratado como CPF, "partido" e "PL" disparam alerta de opinião política, e um dado público com percentual de votos é barrado em empreitada eleitoral. Intervalo de anos ("2019-2023") não é mais telefone, mas um fixo real com cara de ano ("2020-1999") deixa de ser removido. Uma linha inteira entre parênteses sem dois-pontos nem número é tratada como orientação do modelo, mesmo que seja conteúdo ("(Nas férias quem decide é o sócio.)"). Marcar `identificacao_indireta_revisada: sim` não libera essa linha; a saída é reescrevê-la sem parênteses.

## Referências legais

Só entra na skill artigo, lei ou prazo lido em fonte oficial, com endereço e data na mesma linha. O que não foi lido está marcado "conferir antes de citar". **A resolução do TSE sobre uso de IA em campanha não pôde ser lida na fonte** (o site recusou o acesso): o modo eleitoral trava o que é claramente vedado e não orienta sobre artigo ou prazo.

## Testes

```bash
python3 -m unittest discover -s testes -t .
```

O formato da skill (campos do cabeçalho, nome igual ao da pasta, tamanho do SKILL.md) se confere à parte:

```bash
python3 scripts/validar_skill.py .
```

O que depende do comportamento do modelo não cabe em teste automático e fica em roteiros de ensaio. **Nenhum dos três foi executado até esta versão:**

| Ensaio | O que confere |
|---|---|
| `testes/ensaios/e1-levantamento.md` | a entrevista em blocos e o caso sem dado nenhum |
| `testes/ensaios/e1-ponta-a-ponta.md` | o fluxo inteiro numa empreitada fictícia, com pré-mortem e juiz |
| `testes/ensaios/leitor-isolamento.md` | se o agente leitor consegue escrever arquivo ou executar comando |

O ensaio do leitor compara a pasta antes e depois com `python3 scripts/hash_arvore.py <pasta>`: os dois resultados têm de ser iguais.

## Licença

MIT. As origens de cada ideia estão em [FONTES.md](FONTES.md).
