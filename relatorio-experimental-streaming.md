# Relatório experimental: reconstrução de respostas pelo stream

Datas das sessões: 2026-10-06 a 2026-10-08 (Bahia). Horários anteriores abaixo em UTC; para Bahia (UTC−3), subtrair 3 horas. Valores só são preenchidos quando foram observados nas capturas disponíveis. `n/d` significa que o campo não foi registrado; não deve ser inferido de outro teste.

## Objetivo atual: reconstruir a resposta a partir do stream

A investigação agora prioriza saber se o corpo de /conversation/updates pode ser capturado e decodificado para recuperar a resposta completa, com fidelidade verificável. O DOM fica como referência final de comparação; não é a fonte principal da captura. As medições deste relatório foram feitas por observação exploratória via CDP. A coleta em cada máquina está prevista por uma extensão de navegador, que ainda precisa ser validada separadamente.

### Evidência mais forte até agora

- Em duas execuções com formatos de prosa, o corpo da resposta foi reconstruído e coincidiu com a resposta visível após normalização de espaços.
- No Teste 1, três respostas (2, 8 e 16 parágrafos) tiveram corpo final recuperado; em todas, os bytes decodificados coincidiram exatamente com a soma de dataLength.
- A chamada inicial de Network.streamResourceContent trouxe 446 bytes nas três execuções, portanto esse buffer inicial não bastou. O corpo completo foi obtido após o encerramento: Network.getResponseBody em loadingFinished e nova chamada Network.streamResourceContent em loadingFailed.
- O corpo da resposta curta (168.282 bytes) foi maior que o médio (32.269) e o longo (49.048). Esses totais incluem quadros/controles e podem refletir contexto da conversa; não são uma medida direta do texto gerado nem sustentam proporcionalidade.
- Na captura mais recente, Network.streamResourceContent forneceu 21.485 bytes decodificados. A soma de dataLength nos 16 eventos Network.dataReceived também foi 21.485 bytes.
- O corpo continha 21 quadros DPU com snapshots repetidos de três blocos indexados. Processar os quadros e manter o estado final dos índices 0–2 recuperou os três parágrafos completos.
- O stream terminou em loadingFailed / ERR_ABORTED depois da resposta completa. Esse erro, sozinho, não identifica Stop.
- No Teste 2, quatro corpos foram decodificados e reconstruídos: duas respostas em prosa, uma lista numerada e um bloco de código com explicação. Todos coincidiram com o estado final visível; detalhes abaixo.
- No Teste 3, duas respostas por formato foram validadas para prosa, lista numerada, lista com marcadores, código, caracteres especiais e Markdown misto. Todos os corpos bateram com a soma de `dataLength`; a estrutura final também coincidiu com a UI.
- A associação de `message.id` com `data-message-id` foi confirmada em um turno sintético da conversa autenticada; ainda falta validar a generalização para outras rotas/versões e o comportamento de regeneração.

### Identidades: escopos observados

`Network.requestId` é o identificador de transporte do Chrome. `data-request-id` e `operationId` são campos do aplicativo observados no payload. Numa captura recente, `message.id` do stream correspondeu ao `data-message-id` do nó do assistente; o `conversation_id` correspondeu à rota e o `Network.requestId` diferiu do `metadata.request_id` da mensagem. Essa associação foi observada em um turno e ainda não deve ser generalizada para outras rotas, regenerações ou versões.

### Limites da amostra atual

A evidência direta inclui execuções na rota anônima `unauth-mweb` e, em 2026-10-08, na aba autenticada do ChatGPT via CDP da mesma aba. A reconstrução foi comparada à interface depois da resposta completa nos casos de reconstrução. Quadros, campos e semânticas podem variar entre rotas e versões.

## Captura direta mais recente

### Execução de captura — céu azul e pôr do sol

Prompt: “Explique por que o céu pode parecer azul durante o dia e avermelhado no pôr do sol. Responda em exatamente 3 parágrafos, com 3 frases completas em cada um, sem títulos.” Execução na rota anônima `unauth-mweb`; request `/unauth-mweb/conversation/updates`, HTTP 200, `Content-Type: text/vnd.openai.web-mobile-partial+html`. `Network.streamResourceContent` retornou um buffer de 21.485 bytes decodificados enquanto a request ainda estava ativa. A soma dos `dataLength` dos 16 eventos `Network.dataReceived` também foi exatamente 21.485 bytes, uma verificação independente do tamanho do buffer nesta execução.

Identidades observadas no payload: `Network.requestId=89373.274` (transporte Chrome), `data-request-id=1efac4ae-cce7-45fa-bb78-5959c8c81081`, `operationId=371bbdbe-4050-4049-aaa3-8d927c6328fb`, `conversationId=6ac58c4d-b934-83ea-8599-b852018212c1` e atributo `data-message-id=35c56eec-c322-42db-a85e-1ca1b21b646b`. O campo `data-message-id` foi registrado como aparece no markup; esta execução isolada não determina se ele identifica a mensagem do usuário ou a mensagem assistente. O `turnTraceId` não foi necessário para a reconstrução e foi omitido.

O corpo continha 21 quadros DPU e snapshots repetidos dos blocos indexados 0–2. Retendo o snapshot mais recente de cada índice e juntando-os em ordem, foram obtidos três parágrafos. O resultado bateu com os três parágrafos do assistente na interface, preservando texto e pontuação após normalizar espaços.

Horários em UTC (a hora local de Bahia é UTC−3). A amostra da interface foi coletada depois do término, então esta execução confirma a reconstrução e a igualdade final, mas não mede quando cada bloco ficou visível.

| UTC | Evento | Evidência |
| --- | --- | --- |
| 00:04:08.232 | Início da request de conversa | `requestId=89373.274` |
| 00:04:08.309 | Cabeçalhos da resposta | HTTP 200, `text/vnd.openai.web-mobile-partial+html` |
| 00:04:08.316 | Primeiro `dataReceived` | `dataLength=446`, `encodedDataLength=0` |
| 00:04:09.163–00:04:11.245 | Eventos 2–14 | 13 blocos de transporte adicionais; detalhes abaixo |
| 00:04:12.237 | Evento 15 | `dataLength=4.547`, `encodedDataLength=2.652` |
| 00:04:12.285 | Evento 16, último dado recebido | `dataLength=4.510`, `encodedDataLength=4.565` |
| 00:04:12.291 | Encerramento observado | `loadingFailed`, `net::ERR_ABORTED`; a resposta de três parágrafos já estava completa na UI |

| # | UTC | `dataLength` | `encodedDataLength` |
| ---: | --- | ---: | ---: |
| 1 | 00:04:08.316 | 446 | 0 |
| 2 | 00:04:09.163 | 180 | 0 |
| 3 | 00:04:09.175 | 1.239 | 198 |
| 4 | 00:04:09.212 | 1.269 | 1.248 |
| 5 | 00:04:09.260 | 742 | 1.287 |
| 6 | 00:04:09.363 | 407 | 751 |
| 7 | 00:04:09.583 | 445 | 416 |
| 8 | 00:04:09.784 | 1.656 | 454 |
| 9 | 00:04:09.988 | 455 | 1.674 |
| 10 | 00:04:10.199 | 420 | 464 |
| 11 | 00:04:10.402 | 1.685 | 429 |
| 12 | 00:04:10.613 | 430 | 1.694 |
| 13 | 00:04:11.000 | 420 | 439 |
| 14 | 00:04:11.245 | 2.634 | 429 |
| 15 | 00:04:12.237 | 4.547 | 2.652 |
| 16 | 00:04:12.285 | 4.510 | 4.565 |

**Texto reconstruído do payload:**

O céu parece azul durante o dia principalmente por causa do espalhamento da luz solar na atmosfera. A luz do Sol contém várias cores, e as moléculas de gases presentes no ar espalham mais intensamente as ondas de menor comprimento, especialmente as azuis. Por isso, a luz azul se distribui pelo céu e chega aos nossos olhos de diferentes direções.

No pôr do sol, a luz solar precisa atravessar uma camada muito maior da atmosfera antes de chegar aos nossos olhos. Nesse percurso mais longo, grande parte das cores azuladas é espalhada para fora da direção do Sol, enquanto tons vermelhos, alaranjados e amarelos conseguem atravessar melhor. Assim, o Sol e a região próxima ao horizonte podem adquirir uma aparência avermelhada ou alaranjada.

A quantidade de partículas e gotículas presentes na atmosfera também pode alterar a intensidade e as tonalidades dessas cores. Poeira, fumaça, poluição e aerossóis podem espalhar ou absorver a luz de maneiras diferentes, tornando o pôr do sol ainda mais colorido. Portanto, a mudança entre o azul do dia e os tons avermelhados do entardecer resulta principalmente da interação entre a luz solar e a atmosfera.

**Leitura:** esta execução confirma que o corpo de `/conversation/updates` pode conter informação suficiente para reconstruir a resposta sem usar o DOM como fonte primária do texto. `ERR_ABORTED` voltou a ocorrer após a resposta completa, portanto não indica por si só cancelamento solicitado pelo usuário. O teste não capturou snapshots da UI durante o stream e não prova causalidade temporal entre um chunk específico e a renderização.

## Teste 1 — captura integral do corpo

Foram capturadas três respostas na mesma conversa anônima e na mesma rota, solicitando 2, 8 e 16 parágrafos, sempre com três frases por parágrafo. As três respostas apareceram completas na interface. Para cada operação, o corpo final recuperado coincidiu em bytes com a soma de dataLength dos eventos Network.dataReceived.

A chamada inicial a Network.streamResourceContent, feita após responseReceived, retornou somente os primeiros 446 bytes em todas as execuções. A captura integral exigiu uma recuperação final: Network.getResponseBody após loadingFinished na resposta curta; uma segunda chamada a Network.streamResourceContent após loadingFailed nas respostas média e longa. Isso é parte do procedimento a repetir, não uma suposição sobre o protocolo.

| Tamanho | Request CDP | Eventos | Quadros DPU | Bytes do corpo final | Σ dataLength | Σ encodedDataLength | Encerramento |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Curta, 2 parágrafos | 89373.381 | 13 | 18 | 168.282 | 168.282 | 168.196 | loadingFinished |
| Média, 8 parágrafos | 89373.360 | 22 | 28 | 32.269 | 32.269 | 20.403 | loadingFailed, ERR_ABORTED |
| Longa, 16 parágrafos | 89373.427 | 31 | 36 | 49.048 | 49.048 | 32.509 | loadingFailed, ERR_ABORTED |

Os totais não cresceram com o tamanho pedido: o corpo curto foi maior que os corpos médio e longo. Os bytes incluem quadros e controles, e a conversa acumulava contexto; a causa da diferença não foi determinada. Portanto, este ensaio confirma recuperação e consistência de bytes, não uma relação entre tamanho do corpo e extensão da resposta.

Os identificadores de cada execução estão na tabela consolidada. O atributo data-message-id foi anotado, mas seu papel semântico continua em aberto. Os timestamps e tamanhos individuais por evento estão abaixo; horários em UTC, com data 2026-10-07 (dia local 2026-10-06 na Bahia).

### Curta — 2 parágrafos

| # | UTC | dataLength | encodedDataLength |
| ---: | --- | ---: | ---: |
| 1 | 00:20:48.036 | 446 | 0 |
| 2 | 00:20:49.745 | 2.660 | 0 |
| 3 | 00:20:49.788 | 836 | 3.550 |
| 4 | 00:20:49.949 | 498 | 0 |
| 5 | 00:20:50.156 | 1.721 | 507 |
| 6 | 00:20:50.360 | 448 | 1.730 |
| 7 | 00:20:50.510 | 2.889 | 457 |
| 8 | 00:20:55.101 | 16.366 | 2.907 |
| 9 | 00:20:55.105 | 25.799 | 16.384 |
| 10 | 00:20:55.121 | 8.218 | 34.080 |
| 11 | 00:20:55.154 | 16.366 | 0 |
| 12 | 00:20:55.159 | 36.864 | 16.384 |
| 13 | 00:20:55.162 | 55.171 | 92.197 |

### Média — 8 parágrafos

| # | UTC | dataLength | encodedDataLength |
| ---: | --- | ---: | ---: |
| 1 | 00:19:07.967 | 446 | 0 |
| 2 | 00:19:10.534 | 180 | 0 |
| 3 | 00:19:10.550 | 1.239 | 189 |
| 4 | 00:19:10.604 | 1.241 | 1.257 |
| 5 | 00:19:10.637 | 723 | 1.268 |
| 6 | 00:19:10.727 | 402 | 732 |
| 7 | 00:19:10.930 | 1.479 | 411 |
| 8 | 00:19:11.170 | 423 | 1.488 |
| 9 | 00:19:11.347 | 1.483 | 432 |
| 10 | 00:19:11.557 | 465 | 1.492 |
| 11 | 00:19:11.850 | 1.530 | 474 |
| 12 | 00:19:12.003 | 1.478 | 1.539 |
| 13 | 00:19:12.251 | 465 | 1.487 |
| 14 | 00:19:12.412 | 1.468 | 474 |
| 15 | 00:19:12.593 | 420 | 1.477 |
| 16 | 00:19:13.232 | 403 | 429 |
| 17 | 00:19:13.324 | 1.533 | 412 |
| 18 | 00:19:14.552 | 408 | 1.542 |
| 19 | 00:19:14.683 | 380 | 417 |
| 20 | 00:19:14.786 | 1.642 | 389 |
| 21 | 00:19:14.853 | 2.807 | 1.651 |
| 22 | 00:19:17.419 | 11.654 | 2.843 |

### Longa — 16 parágrafos

| # | UTC | dataLength | encodedDataLength |
| ---: | --- | ---: | ---: |
| 1 | 00:22:35.373 | 446 | 0 |
| 2 | 00:22:36.600 | 180 | 0 |
| 3 | 00:22:36.654 | 1.237 | 189 |
| 4 | 00:22:36.762 | 249 | 1.264 |
| 5 | 00:22:36.764 | 1.028 | 258 |
| 6 | 00:22:36.815 | 738 | 1.037 |
| 7 | 00:22:36.918 | 404 | 747 |
| 8 | 00:22:37.120 | 1.506 | 413 |
| 9 | 00:22:37.322 | 1.441 | 1.515 |
| 10 | 00:22:37.547 | 473 | 1.450 |
| 11 | 00:22:37.750 | 1.604 | 482 |
| 12 | 00:22:37.981 | 1.265 | 1.613 |
| 13 | 00:22:38.208 | 822 | 1.274 |
| 14 | 00:22:38.680 | 3.091 | 831 |
| 15 | 00:22:38.799 | 466 | 3.109 |
| 16 | 00:22:38.990 | 1.568 | 475 |
| 17 | 00:22:39.188 | 1.481 | 1.577 |
| 18 | 00:22:39.398 | 1.154 | 1.490 |
| 19 | 00:22:39.606 | 762 | 1.163 |
| 20 | 00:22:39.816 | 1.492 | 771 |
| 21 | 00:22:40.020 | 449 | 1.501 |
| 22 | 00:22:40.243 | 1.491 | 458 |
| 23 | 00:22:40.551 | 414 | 1.500 |
| 24 | 00:22:40.695 | 1.508 | 423 |
| 25 | 00:22:40.858 | 1.554 | 1.517 |
| 26 | 00:22:41.059 | 456 | 1.563 |
| 27 | 00:22:41.267 | 436 | 465 |
| 28 | 00:22:41.472 | 1.638 | 445 |
| 29 | 00:22:41.711 | 2.871 | 1.647 |
| 30 | 00:22:42.896 | 425 | 2.898 |
| 31 | 00:22:42.950 | 16.399 | 434 |


## Registro consolidado dos ensaios

## Teste 2 — decodificação de quadros e snapshots

Executado em 2026-10-07, na mesma sessão anônima da rota `unauth-mweb`, com quatro prompts sequenciais: duas respostas em parágrafos, uma lista numerada e um bloco de código. Cada request retornou HTTP 200 e `Content-Type: text/vnd.openai.web-mobile-partial+html`. A UI mostrou todas as respostas completas.

| Formato | `Network.requestId` | Eventos `dataReceived` | Quadros DPU | Bytes decodificados / Σ `dataLength` | Operações DPU (`append` / `replace`) | Encerramento | Reconstrução vs. UI |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| Prosa — arco-íris | `13763.285` | 13 | 17 | 15.999 / 15.706 | 14 / 5 | `loadingFinished` | blocos 0–1, igualdade exata |
| Prosa — mar | `13763.315` | 11 | 17 | 16.339 / 8.978 | 14 / 5 | `loadingFailed`, `ERR_ABORTED` | blocos 0–1, igualdade exata |
| Lista numerada | `13763.331` | 9 | 14 | 15.578 / 8.494 | 10 / 5 | `loadingFailed`, `ERR_ABORTED` | um bloco ordenado, 3 itens na mesma ordem |
| Código Python | `13763.348` | 9 | 14 | 17.429 / 9.315 | 11 / 5 | `loadingFailed`, `ERR_ABORTED` | bloco de código (índice 0) e explicação (índice 1) coincidem |

Nas quatro respostas, o corpo foi recuperado após a conclusão: `Network.getResponseBody` para `loadingFinished` e uma nova chamada a `Network.streamResourceContent` para os três `loadingFailed`. Os bytes decodificados coincidiram exatamente com a soma de `dataLength`. As respostas com `ERR_ABORTED` estavam completas na UI e não houve ação explícita de Stop.

O processamento em ordem mostrou dois padrões: `replace` forneceu snapshots revisados do alvo; `append` acrescentou fragmentos/caudas ou controles. Não foi observada operação `remove`. Os alvos observados, sem os IDs variáveis, foram `conversation-partial-control`, `conversation-image-gen-upgrade` e elementos `assistant-pending-*` (conteúdo e caudas). Para as duas respostas em prosa, manter o snapshot final por índice produziu blocos 0–1 completos (230 e 286 caracteres; 263 e 316 caracteres) que coincidiram exatamente com os parágrafos da UI. A lista apareceu como um único `<ol>` no bloco 0; o último snapshot continha os três itens, na ordem exibida. No exemplo de código, os blocos finais foram um `<pre><code>` no índice 0 e uma explicação no índice 1; ambos coincidiram com a UI, inclusive a indentação do código.

Limites do registro: IDs internos do aplicativo (`data-request-id`, `operationId`, `conversationId` e `data-message-id`) e o tamanho do buffer inicial não foram preservados nesta rodada. Os quatro testes ocorreram na mesma conversa anônima; os resultados mostram reconstrução nestes exemplos, sem estabelecer semântica universal para outros controles/formatos. A repetição por formato pertence ao Teste 3.

| Campo não preservado | Estado |
| --- | --- |
| IDs internos do aplicativo | n/d |
| Tamanho do `bufferedData` inicial | n/d |

Os eventos `dataReceived` foram recuperados do buffer CDP após as capturas. A tabela registra o delta em milissegundos desde `requestWillBeSent` e os pares `dataLength/encodedDataLength`; o início local é Bahia (UTC−3).

| Request | Início local | Eventos (`ms: dataLength/encodedDataLength`) |
| --- | --- | --- |
| `13763.285` | 2026-10-07 09:40:43.337 | 74: 446/0; 987: 180/0; 1.009: 1.237/189; 1.105: 249/1.246; 1.111: 986/0; 1.173: 701/1.963; 1.407: 389/0; 1.616: 1.489/398; 2.100: 366/1.507; 2.505: 511/375; 2.537: 2.508/529; 3.711: 425/2.526; 3.723: 6.512/6.973 |
| `13763.315` | 2026-10-07 09:41:50.244 | 73: 446/0; 1.709: 1.417/0; 1.733: 1.255/1.435; 1.775: 731/1.282; 1.881: 384/740; 2.084: 451/393; 2.296: 1.624/460; 2.494: 451/1.633; 2.622: 2.539/469; 7.211: 451/2.566; 7.223: 6.590/0 |
| `13763.331` | 2026-10-07 09:41:57.673 | 83: 446/0; 1.207: 180/0; 1.225: 1.237/189; 1.264: 249/1.255; 1.266: 1.196/258; 1.306: 1.122/1.214; 1.401: 1.398/1.140; 1.436: 2.986/1.416; 8.277: 6.764/3.022 |
| `13763.348` | 2026-10-07 09:42:06.186 | 64: 446/127; 1.071: 180/0; 1.090: 1.237/198; 1.137: 249/1.255; 1.143: 1.188/267; 1.181: 1.305/1.197; 1.240: 2.500/1.314; 1.279: 2.421/2.518; 8.255: 7.903/2.439 |
| Identificadores internos do aplicativo | n/d |
| Tamanho do `bufferedData` inicial | n/d |

## Registro consolidado dos ensaios

## Teste 3 — fidelidade e cobertura de formatos

Executado em 2026-10-07 na mesma conversa anônima e rota `/unauth-mweb/conversation/updates` (HTTP 200; `text/vnd.openai.web-mobile-partial+html`). Duas respostas em prosa e uma resposta de código do Teste 2 foram aproveitadas como repetições válidas; nove capturas novas completaram as duas execuções de cada formato. A comparação foi feita entre o estado final reconstruído do corpo e o que apareceu na UI.

| Formato | `Network.requestId` | Eventos | DPU | Bytes do corpo / Σ `dataLength` | Σ `encodedDataLength` | `append` / `replace` | Encerramento e resultado |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Lista numerada 1 | `13763.386` | 4 | 12 | 8.832 / 8.832 | 8.485 | 7 / 5 | `ERR_NETWORK_CHANGED`; 3 itens reconstruídos e UI completa após reconexão |
| Lista numerada 2 | `13763.722` | 9 | 15 | 15.712 / 15.712 | 8.579 | 11 / 5 | `ERR_ABORTED`; 3 itens na mesma ordem da UI |
| Lista com marcadores 1 | `13763.702` | 10 | 16 | 16.986 / 16.986 | 9.752 | 11 / 6 | `ERR_ABORTED`; 3 itens na mesma ordem da UI |
| Lista com marcadores 2 | `13763.741` | 8 | 14 | 16.151 / 16.151 | 8.848 | 10 / 5 | `ERR_ABORTED`; 3 itens na mesma ordem da UI |
| Código — `eh_impar` | `13763.672` | 8 | 13 | 16.290 / 16.290 | 9.011 | 10 / 4 | `ERR_ABORTED`; código e indentação coincidem com a UI |
| Caracteres especiais 1 | `13763.760` | 7 | 13 | 12.917 / 12.917 | 6.058 | 10 / 4 | `ERR_ABORTED`; acentos, aspas curvas, símbolos e emoji preservados |
| Caracteres especiais 2 | `13763.777` | 6 | 13 | 12.839 / 12.839 | 6.497 | 10 / 4 | `ERR_ABORTED`; acentos, aspas curvas, símbolos e emoji preservados |
| Markdown misto 1 | `13763.794` | 7 | 14 | 21.987 / 21.987 | 21.640 | 13 / 5 | `loadingFinished`; título, negrito, tabela e link coincidem |
| Markdown misto 2 | `13763.811` | 10 | 15 | 21.597 / 21.597 | 21.295 | 13 / 5 | `loadingFinished`; título, itálico, tabela e link coincidem |

As duas amostras de prosa já estão na tabela do Teste 2 (`13763.285` e `13763.315`), e a amostra de código com explicação é `13763.348`. Em prosa, os blocos indexados coincidiram com os parágrafos visíveis. As duas listas numeradas vieram como `<ol>` e as duas listas com marcadores como `<ul>`; os três itens e sua ordem coincidiram com a UI. Os dois blocos de código preservaram o texto e a indentação. Nas duas amostras especiais, as respostas repetiram exatamente os caracteres pedidos e o corpo correspondeu à UI. As duas amostras de Markdown preservaram headings, `strong`/`em`, tabela com cabeçalho e células, e links com seus destinos.

Todas as nove novas capturas tiveram o corpo decodificado em bytes igual à soma de `dataLength`. O erro `ERR_NETWORK_CHANGED` da primeira lista numerada ocorreu durante uma oscilação da conexão; a reconstrução continha os três itens completos, e a interface mostrou o mesmo resultado depois de reconectar. Nas demais capturas com `ERR_ABORTED`, a UI também estava completa; esse código isolado continua sem provar cancelamento por Stop.

As amostras vieram da mesma rota e da mesma conversa anônima. O Teste 3 confirma a fidelidade nestes exemplos e estruturas específicas; ainda não generaliza para outras rotas, versões do frontend ou variações arbitrárias de Markdown.

| Teste | Request CDP | `data-request-id` | operationId | conversationId | messageId | Chunks | Bytes (`dataLength` / `encodedDataLength`) | Resultado | Encerramento |
| --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| Teste 1 — curta, 2 parágrafos | `89373.381` | `2902c495-7c59-4673-8de0-c69b8854bd63` | `a4d81aad-bb15-4907-8181-4bafe751e036` | `6ac58c4d-b934-83ea-8599-b852018212c1` | `56b23e87-f42e-4970-9fb6-5f5048b663a3`* | 13 / 18 DPU | 168.282 / 168.196 | corpo final=Σ `dataLength`; UI completa | `loadingFinished` |
| Teste 1 — média, 8 parágrafos | `89373.360` | `4bf774df-a944-480b-a4f2-4c037323542f` | `0e2eb450-778f-473e-9d07-f084a761839d` | `6ac58c4d-b934-83ea-8599-b852018212c1` | `f13b3524-27f8-4402-8a67-c8b575093954`* | 22 / 28 DPU | 32.269 / 20.403 | corpo final=Σ `dataLength`; UI completa | `loadingFailed`, `ERR_ABORTED` |
| Teste 1 — longa, 16 parágrafos | `89373.427` | `bf42c2d5-2523-435a-af6b-ec5b6c712da9` | `82fa1318-5f14-4389-92be-3c4f2c0907e8` | `6ac58c4d-b934-83ea-8599-b852018212c1` | `47b27dbf-b00b-4a23-8937-12f565236d52`* | 31 / 36 DPU | 49.048 / 32.509 | corpo final=Σ `dataLength`; UI completa | `loadingFailed`, `ERR_ABORTED` |
| Longa — abelhas | `46709.407` | n/d | n/d | `6ac57ffa-9cd0-83ea-b7c7-5ac0290222a0` | n/d | 24 | 23.681 / 20.821 | concluído | `loadingFinished` |
| Curta — marés, captura de payload | `46709.434` | `bd60c82a-bde8-4288-b508-f90f663a796e` | `1b96ae9c-cf52-497a-ad2a-362d32be3356` | `6ac57ffa-9cd0-83ea-b7c7-5ac0290222a0` | `0e8315d0-acf6-4890-8e4f-9146ebb61506` | 14 quadros HTML DPU | 13.054 bytes decodificados / n/d | concluído | marcadores terminais e `ERR_ABORTED`; sem `loadingFinished` |
| Longa — floresta, Stop | `46709.491` | n/d | n/d | `6ac57ffa-9cd0-83ea-b7c7-5ac0290222a0` | n/d | ≥10 observados | n/d | interrompido | endpoint Stop `46709.497` retornou 200; stream `loadingFailed`, `ERR_ABORTED` |
| Regenerar resposta | — | — | — | — | — | — | — | não executado | sessão não apresentou ação Regenerar/Tentar novamente |
| Ciclo rede → DOM → texto visível (execução 1) | `46709.509` | n/d | n/d | `6ac57ffa-9cd0-83ea-b7c7-5ac0290222a0` | n/d | n/d (resposta inteira observada; contagem desta captura incompleta) | n/d | concluído | `loadingFinished`; primeira tentativa não armou a árvore DOM |
| Ciclo rede → DOM → texto visível (execução 2) | `46709.535` | n/d | n/d | `6ac57ffa-9cd0-83ea-b7c7-5ac0290222a0` | `e0f04e25-dae7-469c-9000-e81f2ec094c7` | 16 | 27.547 / 16.688 somados dos eventos `dataReceived` | resposta completa, 6 parágrafos | DOM marcou `data-message-complete`; stream terminou em `loadingFailed`, `ERR_ABORTED` (sem `loadingFinished`) |
| Conteúdo bruto — formação de nuvem | `46709.564` | `7a222f4f-596e-4692-9409-80408ec48a8a` | `43fb9370-3658-4668-a7f5-517461acc12c` | `6ac57ffa-9cd0-83ea-b7c7-5ac0290222a0` | `ababc9dd-852f-4d76-be0c-def0a8bdb89a` | 17 | 137.262 / 137.322 somados dos eventos `dataReceived` | conteúdo reconstruído; igualdade exata com o texto visível | `loadingFinished`, 138.134 bytes codificados no total da request |
| Reconstrução — céu azul e pôr do sol | `89373.274` | `1efac4ae-cce7-45fa-bb78-5959c8c81081` | `371bbdbe-4050-4049-aaa3-8d927c6328fb` | `6ac58c4d-b934-83ea-8599-b852018212c1` | `35c56eec-c322-42db-a85e-1ca1b21b646b`* | 16 eventos / 21 quadros DPU | 21.485 / 16.700 somados dos eventos `dataReceived` | 3 blocos reconstruídos, iguais à UI após normalizar espaços | `loadingFailed`, `ERR_ABORTED` 6 ms após último chunk; UI completa |
| Teste 2 — prosa arco-íris | `13763.285` | n/d | n/d | n/d | n/d | 13 / 17 DPU | 15.999 / 15.706 | blocos 0–1; igualdade exata com a UI | `loadingFinished` |
| Teste 2 — prosa mar | `13763.315` | n/d | n/d | n/d | n/d | 11 / 17 DPU | 16.339 / 8.978 | blocos 0–1; igualdade exata com a UI | `loadingFailed`, `ERR_ABORTED`; UI completa |
| Teste 2 — lista numerada | `13763.331` | n/d | n/d | n/d | n/d | 9 / 14 DPU | 15.578 / 8.494 | bloco 0; três itens em ordem iguais à UI | `loadingFailed`, `ERR_ABORTED`; UI completa |
| Teste 2 — código Python | `13763.348` | n/d | n/d | n/d | n/d | 9 / 14 DPU | 17.429 / 9.315 | blocos 0–1; código e explicação iguais à UI | `loadingFailed`, `ERR_ABORTED`; UI completa |
| Teste 3 — lista numerada 1 | `13763.386` | n/d | n/d | n/d | n/d | 4 / 12 DPU | 8.832 / 8.485 | 3 itens iguais à UI após reconexão | `loadingFailed`, `ERR_NETWORK_CHANGED` |
| Teste 3 — lista numerada 2 | `13763.722` | n/d | n/d | n/d | n/d | 9 / 15 DPU | 15.712 / 8.579 | 3 itens na mesma ordem da UI | `loadingFailed`, `ERR_ABORTED` |
| Teste 3 — marcadores 1 | `13763.702` | n/d | n/d | n/d | n/d | 10 / 16 DPU | 16.986 / 9.752 | 3 itens na mesma ordem da UI | `loadingFailed`, `ERR_ABORTED` |
| Teste 3 — marcadores 2 | `13763.741` | n/d | n/d | n/d | n/d | 8 / 14 DPU | 16.151 / 8.848 | 3 itens na mesma ordem da UI | `loadingFailed`, `ERR_ABORTED` |
| Teste 3 — código `eh_impar` | `13763.672` | n/d | n/d | n/d | n/d | 8 / 13 DPU | 16.290 / 9.011 | código igual à UI | `loadingFailed`, `ERR_ABORTED` |
| Teste 3 — caracteres especiais 1 | `13763.760` | n/d | n/d | n/d | n/d | 7 / 13 DPU | 12.917 / 6.058 | conteúdo igual à UI e ao texto solicitado | `loadingFailed`, `ERR_ABORTED` |
| Teste 3 — caracteres especiais 2 | `13763.777` | n/d | n/d | n/d | n/d | 6 / 13 DPU | 12.839 / 6.497 | conteúdo igual à UI e ao texto solicitado | `loadingFailed`, `ERR_ABORTED` |
| Teste 3 — Markdown misto 1 | `13763.794` | n/d | n/d | n/d | n/d | 7 / 14 DPU | 21.987 / 21.640 | heading, negrito, tabela e link iguais à UI | `loadingFinished` |
| Teste 3 — Markdown misto 2 | `13763.811` | n/d | n/d | n/d | n/d | 10 / 15 DPU | 21.597 / 21.295 | heading, itálico, tabela e link iguais à UI | `loadingFinished` |

\* IDs copiados do atributo `data-message-id`; seu papel semântico não foi confirmado nestas execuções.

## Evidências históricas e ensaios auxiliares

### Ensaio exploratório — volume e tamanho das respostas

Executado em 2026-10-06 na mesma conversa/rota anônima, com o mesmo tema e três prompts idênticos por tamanho: 2, 8 e 16 parágrafos, sempre com 3 frases por parágrafo. Cada resposta apareceu completa na UI. O contexto acumulado da conversa pode influenciar respostas posteriores.

| Tamanho | Rep. | Request CDP | HTTP | Chunks | Σ `dataLength` | Σ `encodedDataLength` | Caracteres na UI | Encerramento de rede |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Curta (2 parágrafos) | 1 | `46709.597` | 200 | 8 | 16.658 | 8.942 | 639 | `loadingFailed`, `ERR_ABORTED`; UI completa |
| Curta (2 parágrafos) | 2 | `46709.613` | 200 | 12 | 24.318 | 12.853 | 630 | `loadingFailed`, `ERR_ABORTED`; UI completa |
| Curta (2 parágrafos) | 3 | `46709.633` | 200 | 11 | 17.190 | 16.906 | 647 | `loadingFinished`, 17.881 bytes; UI completa |
| Média (8 parágrafos) | 1 | `46709.652` | 200 | 21 | 34.081 | 21.564 | 2.190 | `loadingFailed`, `ERR_ABORTED`; UI completa |
| Média (8 parágrafos) | 2 | `46709.669` | 200 | 21 | 33.223 | 20.971 | 2.262 | `loadingFailed`, `ERR_ABORTED`; UI completa |
| Média (8 parágrafos) | 3 | `46709.686` | 200 | 20 | 31.794 | 19.806 | 2.123 | `loadingFailed`, `ERR_ABORTED`; UI completa |
| Longa (16 parágrafos) | 1 | `46709.705` | 200 | 39 | 55.798 | 37.959 | 4.415 | `loadingFailed`, `ERR_ABORTED`; UI completa |
| Longa (16 parágrafos) | 2 | `46709.722` | 200 | 44 | 57.070 | 55.022 | 4.736 | `loadingFailed`, `ERR_ABORTED`; UI completa |
| Longa (16 parágrafos) | 3 | `46709.739` | 200 | 41 | 57.630 | 47.004 | 4.681 | `loadingFailed`, `ERR_ABORTED`; UI completa |

| Tamanho | Mediana de chunks | Faixa de chunks | Mediana de `dataLength` | Faixa de `dataLength` | Mediana de caracteres UI |
| --- | ---: | ---: | ---: | ---: | ---: |
| Curta | 11 | 8–12 | 17.190 | 16.658–24.318 | 639 |
| Média | 21 | 20–21 | 33.223 | 31.794–34.081 | 2.190 |
| Longa | 41 | 39–44 | 57.070 | 55.798–57.630 | 4.681 |

**Leitura provisória:** entre os três tamanhos, texto visível, contagem de chunks e soma de `dataLength` crescem em ordem. A mediana de `dataLength` passa de 17.190 para 33.223 e 57.070 bytes; já a contagem de chunks passa de 11 para 21 e 41. Isso sustenta, nesta rota e amostra, que respostas maiores tendem a produzir mais tráfego e mais eventos de transporte. Os valores não são proporcionais de forma exata e há variação entre repetições do mesmo tamanho.

`dataLength` inclui o corpo de quadros DPU, controles e possivelmente outras estruturas do stream; não equivale a bytes de texto do modelo. A soma de `encodedDataLength` varia bastante entre respostas semelhantes e não acompanha os caracteres de modo estável. O teste não capturou `operationId` nem decodificou o payload bruto nas nove execuções.

Oito requests terminaram em `ERR_ABORTED`, embora a resposta estivesse completa na interface e não tenha havido ação Stop. Portanto, neste fluxo esse encerramento não pode ser usado sozinho como resultado de cancelamento. Para confirmar o padrão, repetir em outra conversa/sessão e, se possível, em outra condição de rota.

Limitação desta captura: foram preservadas as contagens e somas por request, mas não os timestamps do primeiro e último `dataReceived` de todas as nove repetições. Use estes resultados para comparar volume e contagem; não os use para estimar duração ou cadência de chunks.

### Evidência auxiliar — rede, DOM e primeira visibilidade

Prompt: “Explique como uma gota de chuva atravessa o ciclo da água. Escreva 6 parágrafos, com 3 frases completas em cada um, sem títulos.” A resposta final ficou visível na conversa e o botão de interrupção desapareceu.

| UTC | Evento | Evidência |
| --- | --- | --- |
| 23:43:52.388 | Início do POST `/unauth-mweb/conversation/updates` | `requestId=46709.535`; HTTP 200 recebido às 23:43:52.460 |
| 23:43:52.471 | Primeiro `Network.dataReceived` do stream | `dataLength=446`, `encodedDataLength=0`; conteúdo textual ainda não foi confirmado na UI |
| 23:43:53.553 | Outro `dataReceived` | `dataLength=180`, `encodedDataLength=0` |
| 23:43:53.607 | `dataReceived` | `dataLength=1.237`, `encodedDataLength=189` |
| 23:43:53.629 | `dataReceived` | `dataLength=1.268`, `encodedDataLength=2.532` |
| ~23:43:53.649 | Eventos `DOM.childNodeInserted` e mudanças de atributos, após os chunks anteriores na sequência CDP | Inserções observadas na árvore solicitada previamente; CDP não inclui timestamp próprio nesses eventos, então o horário é o do ciclo de leitura que os recebeu |
| 23:43:53.661 | `dataReceived` próximo à primeira aparição do texto | `dataLength=745`, `encodedDataLength=0`; mutações relevantes da mensagem aparecem imediatamente antes dele na sequência CDP |
| 23:43:53.667 | Primeira amostra em que o texto do assistente estava visível | Polling DOM encontrou texto não vazio com retângulo visível, cerca de 6 ms após o chunk acima; `messageId=e0f04e25-dae7-469c-9000-e81f2ec094c7` |
| 23:43:53.751–23:43:55.804 | Chunks subsequentes | 10 eventos `dataReceived` adicionais, com pausas de aproximadamente 0,09–0,39 s |
| 23:43:58.517 | Último `dataReceived` observado | `dataLength=10.584`, `encodedDataLength=3.123` |
| 23:43:58.537 | Fim do stream no CDP | `loadingFailed`, `net::ERR_ABORTED`; apesar disso, a resposta estava completa na UI e o DOM continha `data-message-complete` |

O primeiro texto visível foi observado aproximadamente 6 ms após o `dataReceived` de 23:43:53.661. A sequência CDP coloca os primeiros eventos DOM relevantes antes desse chunk e depois dos chunks de 23:43:53.607 e 23:43:53.629; logo, os dados sustentam uma ligação temporal estreita entre chegada do stream, criação/atualização do conteúdo e visibilidade, mas não identificam um único chunk como causa exclusiva. O primeiro `dataReceived` ocorreu cerca de 1,20 s antes da primeira amostra com texto visível, sugerindo que nem todos os blocos recebidos representam texto renderizável.

### Limites das observações de rede e DOM

- Nesta execução há precedência temporal e proximidade entre chunks do stream, mutações no DOM e texto observável. Isso apoia a hipótese de que a UI reage ao stream; uma correlação em uma execução não prova causalidade exclusiva. Outras mensagens de estado, preparação e renderização também alteram o DOM.
- O horário dos eventos de rede foi convertido de `Network.*.timestamp` usando o par monotônico/parede de `requestWillBeSent`. Eventos `DOM.*` não incluem timestamp CDP, portanto seus horários são estimativas limitadas pelo polling (~30–80 ms observado). A primeira aparição foi determinada por texto DOM não vazio e caixa com retângulo visível; não é uma medição de pixels/paint do compositor, e sua resolução fica limitada pelo polling (~30 ms).
- `dataLength` e `encodedDataLength` foram somados separadamente conforme reportados por `Network.dataReceived`. `encodedDataLength` pode ser zero em vários eventos; a soma não é uma medida independente do tamanho lógico do conteúdo.
- `ERR_ABORTED` não significa sozinho que o usuário interrompeu a geração: no ensaio 5 a UI completou a resposta e sinalizou `data-message-complete` antes do aborto do stream. No teste Stop, a evidência de cancelamento foi a chamada explícita ao endpoint Stop e o estado parcial da UI.
- O teste 5 não capturou `operationId` nem o conteúdo bruto dos quadros da execução. Os IDs de outros ensaios não foram reutilizados para preencher esses campos.

### Captura anterior — formação de nuvem

Prompt: “Descreva a formação de uma nuvem desde a evaporação até a chuva. Escreva 5 parágrafos com 3 frases completas em cada um, sem títulos.” A captura usou `Network.streamResourceContent` durante a resposta. O conteúdo ficou temporariamente no REPL e os tokens/resume-token foram excluídos deste relatório.

- O corpo capturado tinha 72 quadros HTML DPU. Os controles observados incluíram `started`, `conversation-id`, `assistant-content-started`, `assistant-end-turn-rendered`, `message-stream-complete`, `terminal-received` e `complete`.
- O stream continha o mesmo `message_id` e `request_id` em seus fragmentos; continha também `operation_id` e `conversation_id`. Os valores estão na tabela, separados do `Network.requestId` do Chrome.
- Foram encontrados 11 snapshots de blocos de texto, nos índices 0–4. Para cada índice, manter a ocorrência mais recente e ordená-los produziu cinco blocos cuja junção bateu exatamente com o texto final da interface (1.608 caracteres, normalizando espaços).
- Linha do tempo UTC: request às 23:51:47.546; HTTP 200 às 23:51:47.624; primeiro chunk às 23:51:47.628; chunk às 23:51:49.042; primeira amostra de texto visível às 23:51:49.055 (13 ms depois); dois chunks finais às 23:51:54.133 e 23:51:54.145; `loadingFinished` observado no mesmo instante final, em sequência CDP posterior ao último chunk.
- A primeira parcela de 446 bytes chegou antes do conteúdo textual visível; os fragmentos iniciais subsequentes precederam a primeira aparição. Isso reforça que a stream inclui controles/estrutura além do texto, e que uma estratégia de reconstrução precisa respeitar blocos indexados e substituições.

| Chunk | UTC | `dataLength` | `encodedDataLength` |
| ---: | --- | ---: | ---: |
| 1 | 23:51:47.628 | 446 | 155 |
| 2 | 23:51:48.865 | 180 | 0 |
| 3 | 23:51:48.988 | 2.480 | 198 |
| 4 | 23:51:49.042 | 714 | 3.230 |
| 5 | 23:51:49.196 | 469 | 0 |
| 6 | 23:51:49.235 | 1.571 | 478 |
| 7 | 23:51:49.437 | 534 | 1.580 |
| 8 | 23:51:49.642 | 1.683 | 543 |
| 9 | 23:51:49.844 | 454 | 1.692 |
| 10 | 23:51:50.044 | 1.571 | 463 |
| 11 | 23:51:50.249 | 485 | 1.580 |
| 12 | 23:51:50.458 | 1.638 | 494 |
| 13 | 23:51:50.663 | 499 | 1.647 |
| 14 | 23:51:50.760 | 1.343 | 508 |
| 15 | 23:51:50.778 | 1.212 | 1.352 |
| 16 | 23:51:54.133 | 47.826 | 1.230 |
| 17 | 23:51:54.145 | 74.157 | 122.172 |

## Próximos ensaios prioritários

1. Confirmar a associação de IDs em mais turnos e numa regeneração quando a interface oferecer essa ação.
2. Repetir o Teste 5 pela extensão, comparando uma conclusão normal com as três interrupções já observadas via CDP.
3. Repetir o Teste 6 pela extensão; o CDP cobriu CSV e PDF na mesma aba, com transferências e metadados conferidos.
4. Repetir o protocolo em outra rota/versão se estiver disponível; registrar divergências sem generalizar do frontend atual.
5. Manter a correlação DOM/rede como observação auxiliar para validar respostas reconstruídas.

### Tentativas exploratórias de 2026-10-07 sem captura de rede

- **Stop (Teste 5):** no chat anônimo, foi enviado um pedido de resposta longa e a ação `Interromper geração` foi acionada enquanto estava disponível. A interface manteve uma resposta visivelmente parcial. Isso confirma apenas o comportamento visual nesta tentativa: a aba correspondente não estava acessível pela ferramenta de captura de rede, portanto não há eventos, status de encerramento nem request de cancelamento para correlacionar.
- **CSV (Teste 6):** foi solicitado um CSV sintético para download. A resposta informou que aquele chat não podia criar/anexar o arquivo; não apareceu link nem artefato baixável. Isso não testa o transporte de arquivos e não conta como execução do Teste 6.

### Teste 6 — captura de CSV e PDF pela mesma aba

Em 2026-10-07, numa sessão autenticada do ChatGPT, foi solicitado `teste-captura-completo.csv` com as colunas `id,nome,valor` e três linhas fictícias. O cartão `Planilha` e as opções de download apareceram. Com o cursor de eventos armado antes do prompt, a resposta veio por `POST /backend-api/f/conversation`, status 200 e `Content-Type: text/event-stream`. `Network.getResponseBody` retornou 37.372 bytes, exatamente a soma de `dataLength` dos eventos `Network.dataReceived`; `encodedDataLength` foi 40.567 bytes. O nome do arquivo aparece como texto no stream, mas a inspeção das chaves nos 43 quadros JSON não encontrou campos explícitos de arquivo/artefato, MIME, tamanho ou URL. As três linhas de dados do CSV baixado não aparecem no corpo do stream.

A UI acionou `GET /backend-api/conversation/:conversationId/interpreter/download`, status 200 e `application/json` (341 bytes de `dataLength`). O JSON informou `status: success` e continha as chaves `download_url`, `file_name`, `mime_type` e `file_size_bytes`; os campos de nome, tipo e tamanho vieram nulos. O valor de `download_url` não foi registrado. Em seguida, houve `GET /backend-api/estuary/content`, status 200, `Content-Type: text/csv` e `Content-Disposition: attachment; filename="teste-captura-completo.csv"`. O evento terminou com `ERR_ABORTED`, embora o evento de download tenha sido concluído e o arquivo estivesse salvo em [teste-captura-completo.csv](/home/edupires/Downloads/teste-captura-completo.csv). O arquivo local foi identificado como CSV, tem 78 bytes e SHA-256 `f72e692706aff4ecf2f6f4ff54004dd43c0a1d862ad16a4c28bf9d8fcca42e8d`; o conteúdo foi verificado como cabeçalho mais três linhas sintéticas.

Para o PDF, também foi capturado `POST /backend-api/f/conversation` (status 200, `text/event-stream`): o corpo teve 23.176 bytes, igual à soma de `dataLength`, e `encodedDataLength` foi 26.359. O stream menciona `teste-captura.pdf`, mas não contém o marcador `%PDF-`, o título do documento nem chaves explícitas de arquivo/MIME/tamanho/URL. A chamada `GET /backend-api/conversation/:conversationId/interpreter/download` retornou status 200 e `application/json` (451 bytes de `dataLength`); o JSON informou `status: success`, `file_name: teste-captura.pdf` e `mime_type: application/pdf`, enquanto `file_size_bytes` veio nulo. O valor de `download_url` e o valor de `metadata.file_id` não foram registrados. O request subsequente a `/backend-api/estuary/content` retornou status 200, `application/pdf` e `Content-Disposition: attachment; filename="teste-captura.pdf"`. Embora o evento de rede terminasse em `ERR_ABORTED`, o evento de download concluiu e o arquivo foi salvo em [teste-captura.pdf](/home/edupires/Downloads/teste-captura.pdf); ele tem 26.770 bytes, SHA-256 `7a3512d12586ea163009803ab583bce3b2f30edf42642142a7a41b899733f023`, uma página e o título/tabela sintéticos esperados.

Nos dois tipos, o stream da conversa contém o nome do arquivo, mas não os bytes do artefato nem campos explícitos de arquivo; o conteúdo foi entregue por um request separado a `/backend-api/estuary/content`. A resposta JSON de download forneceu nome e MIME para o PDF, mas veio com esses campos nulos para o CSV. Em ambos, o tamanho foi conferido no arquivo baixado, pois não veio preenchido no JSON nem em `Content-Length`. O Teste 6 está concluído para a captura exploratória via CDP nesta sessão; falta validar o fluxo pela extensão do navegador.

Essas tentativas não alteram os critérios de conclusão: repetir os ensaios pela extensão do navegador e capturar os dados de rede na mesma sessão da interface.

### Ensaios via CDP na aba autenticada — 2026-10-08

A configuração do navegador do Codex tornou a capacidade CDP acessível diretamente na mesma aba autenticada do ChatGPT. O cursor dos eventos foi marcado antes de cada ação; nenhuma sessão DevTools separada foi usada para atribuir os eventos.

**Conversa independente, formatos e reconstrução:** foi enviado um prompt sintético pedindo título, lista numerada com três itens, Unicode e bloco de código. A primeira tentativa falhou com `net::ERR_NETWORK_CHANGED`; após novo envio, `POST /backend-api/f/conversation` retornou status 200 e `text/event-stream`. O corpo teve 11.981 bytes, exatamente a soma de `dataLength` em 11 eventos `Network.dataReceived`. Foram decodificados 21 frames JSON sem conservar o frame de token de retomada. As operações DPU reconstruíram o título, os itens e o código; após normalizar a sintaxe Markdown e os espaços, o texto coincidiu com os nós renderizados no DOM.

**Identidade dos IDs:** num segundo turno sintético da conversa, `message.id` no stream correspondeu ao `data-message-id` do nó do assistente. O `conversation_id` do stream correspondeu à rota; `Network.requestId` do CDP foi distinto de `metadata.request_id` da mensagem. Os três nós de resposta observados no DOM tinham IDs únicos. Em 8 de outubro, a inspeção do menu de uma resposta interrompida e de uma resposta curta concluída (`OK`) também não encontrou ação de regeneração; essa semântica permanece sem confirmação.

**Interrupção (três tentativas):** em cada tentativa, foi enviada uma solicitação sintética longa e clicado `Parar` quando já havia texto parcial visível. Nas três, `POST /backend-api/stop_conversation` retornou 200, o botão de parada desapareceu e a resposta exibida ficou parcial. Nas tentativas 1 e 3, o stream terminou com `Network.loadingFailed`, `net::ERR_ABORTED` e `canceled=true`. Na tentativa 2, o stream terminou com `Network.loadingFinished`, mas o snapshot DPU ainda indicava status `in_progress` e `end_turn=null`. Logo, encerramento de transporte normal não equivale necessariamente a resposta concluída; a classificação precisa combinar o evento Stop, o estado final DPU e a UI.

Para detalhes do procedimento e critérios de avanço, consulte [protocolo-validacao-stream-llm.md](protocolo-validacao-stream-llm.md).
