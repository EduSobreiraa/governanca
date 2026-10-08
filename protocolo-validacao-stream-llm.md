# Protocolo experimental: reconstrução de respostas pelo stream

## Objetivo atual

Verificar se o corpo de rede da conversa contém informação suficiente para reconstruir integralmente a resposta do assistente, e estabelecer como decodificar os quadros e distinguir texto final, revisões e controles. O DOM serve como referência de comparação depois da reconstrução; ele não é a fonte primária do texto neste estudo.

Os ensaios exploratórios deste protocolo usam observação manual via CDP. Para coleta em cada máquina, a instrumentação prevista é uma extensão de navegador; o CDP serve aqui para validar hipóteses e critérios de captura, não como mecanismo de implantação. Resultados coletados: [relatorio-experimental-streaming.md](relatorio-experimental-streaming.md).

## Instrumentação prevista por máquina

A extensão do navegador será o ponto de acesso à comunicação de rede em cada máquina. Ao avaliar uma captura exploratória feita por CDP, registre que ela valida o comportamento observado, mas ainda não demonstra que a extensão consegue obter os mesmos eventos e bytes. Antes de considerar um teste coberto pela solução, repita-o pela extensão e compare corpo reconstruído, IDs disponíveis e estado final da interface. A extensão deve guardar somente os campos necessários e sanitizados descritos neste protocolo.

## Modelo de trabalho

A rota observada é /conversation/updates. Na amostra móvel anônima, a resposta veio com Content-Type text/vnd.openai.web-mobile-partial+html. O corpo continha quadros DPU, metadados e snapshots de texto identificados por índice. Os eventos Network.dataReceived descrevem transporte e tamanho; eles não correspondem um a um a palavras, tokens ou parágrafos.

A hipótese que orienta os ensaios é: capturar o corpo durante a request, reconstituir as operações dos quadros em ordem, montar o estado final dos blocos de texto e só então comparar esse estado com a mensagem visível.

## Procedimento comum de captura

1. Registre data, fuso, origem/rota, estado de autenticação e a ação que será realizada. Use uma única aba durante cada execução.
2. Habilite Network e marque o cursor de eventos antes de enviar o prompt ou clicar em Stop/regenerar pela interface.
3. Identifique a request da conversa pelo caminho sem query e confirme-a com método, status, Content-Type e contexto temporal. Não registre cabeçalhos, cookies ou valores de parâmetros sensíveis.
4. Assim que a resposta estiver disponível e ainda ativa, chame Network.streamResourceContent e registre o tamanho do bufferedData inicial. Não o considere o corpo completo: nas três execuções recentes, essa chamada inicial continha apenas 446 bytes.
5. Leia Network.dataReceived até Network.loadingFinished ou Network.loadingFailed. Registre timestamp monotônico, dataLength e encodedDataLength em cada evento. Nesta interface, esses eventos trouxeram tamanhos, mas não os bytes do corpo.
6. Depois do encerramento, recupere o corpo final com Network.getResponseBody se houve loadingFinished. Se houve loadingFailed, tente Network.streamResourceContent novamente; nas duas falhas recentes, a chamada final retornou o corpo completo. Se nenhum método retornar o corpo integral, classifique a execução como incompleta.
7. Decodifique o corpo de acordo com base64Encoded/representação retornada. Compare seu tamanho em bytes com a soma de dataLength; investigue e registre diferenças, sem completar valores por inferência. Nas três execuções do Teste 1, os totais coincidiram exatamente.
8. Registre o estado final da interface e a presença ou ausência de ação explícita de Stop. ERR_ABORTED isolado não é prova de cancelamento pelo usuário.
9. Encerre a captura após validar o corpo. Não copie nem persista tokens, cookies, cabeçalhos, resume-token ou identificadores de sessão. Guarde apenas o texto experimental necessário, campos sanitizados e resumos.
10. Só consulte a resposta na interface depois de congelar a reconstrução, para reduzir viés. Declare qualquer normalização antes de avaliar igualdade.

## Reconstrução do conteúdo

1. Preserve a ordem dos quadros DPU e os controles observados, sem imprimir valores de tokens.
2. Identifique os alvos de conteúdo e os índices de bloco, como data-assistant-stream-block-index.
3. Aplique a operação indicada por cada quadro ao estado do alvo. Se o quadro indica replace, substitua o snapshot daquele alvo; se indicar outra operação, aplique-a conforme observada. Não suponha que cada fragmento seja append-only.
4. Para cada índice, determine o estado final após processar todos os quadros. Ordene os blocos pelo índice e monte o texto final, preservando acentos, pontuação, espaços, quebras, listas e código.
5. Compare o resultado com a resposta final visível. Informe igualdade exata ou, se houver normalização, igualdade após normalização. Registre diferenças com contexto mínimo e sem copiar dados incidentais do payload.

## Campos mínimos por execução

| Grupo | Registrar |
| --- | --- |
| Contexto | data/hora/fuso, rota, sessão autenticada/anônima, ação do usuário e formato solicitado |
| Transporte | Network.requestId do Chrome, caminho sem query, método, status, Content-Type, início e fim |
| Volume | número de eventos dataReceived; dataLength e encodedDataLength por evento e somas separadas |
| Operação | data-request-id, operationId, conversationId e message ID somente quando o papel do campo estiver explícito |
| Estrutura | contagem de quadros, controles por nome, índices de bloco, operações, snapshots por índice |
| Resultado | bytes decodificados do buffer, texto reconstruído, comparação final com a interface e encerramento |
| Limites | captura incompleta, payload não textual, normalização e qualquer ambiguidade |

IDs devem ser registrados no escopo em que aparecem. Network.requestId é identidade de transporte; operationId identifica uma operação observada; conversationId identifica uma conversa conforme o payload; data-request-id é outro campo do aplicativo. Não atribua significado a messageId sem confirmar o elemento ou entidade correspondente. Não misture identificadores de conversas diferentes.

## Plano de seis testes

| Nº | Teste | Questão principal | Critério de avanço | Estado |
| ---: | --- | --- | --- | --- |
| 1 | Captura integral do corpo | O corpo do endpoint de conversa pode ser recuperado e validado sem depender de inspeção DOM? | Em três execuções, obter o corpo final e confirmar que bytes decodificados igualam a soma de dataLength; a UI deve estar completa. | Confirmado em três respostas da mesma conversa e numa conversa independente. No caso independente, corpo de 11.981 bytes igualou a soma de dataLength; uma tentativa anterior falhou com ERR_NETWORK_CHANGED. Repetir via extensão. |
| 2 | Decodificação de quadros e snapshots | Como controles, alvos e atualizações transformam os quadros em texto final? | Em duas respostas, processar todos os quadros em ordem, reconstruir os blocos finais e documentar as operações observadas, sem escolher fragmentos manualmente. | Executado em 4 respostas nesta sessão (2 prosas, 1 lista, 1 código): reconstrução e comparação final confirmadas; `replace` e `append` observados. Repetições por formato continuam no Teste 3. |
| 3 | Fidelidade e cobertura de formatos | A reconstrução funciona para prosa, listas, código, caracteres especiais e Markdown misto? | Duas execuções por formato; correspondência integral de texto, pontuação, ordem e estrutura relevante, ou lacuna explicitamente documentada. | Executado com 2 respostas por formato: prosa, lista numerada, lista com marcadores, código, caracteres especiais e Markdown misto. Conteúdo e estrutura coincidiram com a UI; uma lista terminou em `ERR_NETWORK_CHANGED`, mas o corpo bateu com `dataLength` e a resposta final apareceu após reconexão. |
| 4 | Identidade entre operações | Quais IDs mudam por transporte, operação, conversa e mensagem? Como regeneração se comporta? | Registrar IDs em três turnos da mesma conversa, uma conversa nova e uma regeneração disponível; confirmar a semântica de message ID antes de generalizar. | Parcial: no segundo turno, message.id do stream correspondeu ao data-message-id do DOM; conversation_id correspondeu à rota; Network.requestId diferiu de metadata.request_id. Três IDs do DOM foram únicos. Em 8/10, resposta curta concluída também não exibiu ação de regeneração no menu. Repetir via extensão e quando a ação estiver disponível. |
| 5 | Terminação, Stop e tráfego auxiliar | Como distinguir resposta concluída, cancelamento explícito e requests auxiliares? | Comparar respostas normais com pelo menos três Stops explícitos. Cancelamento exige ação Stop e estado parcial; status de rede sozinho não basta. | Três Stops exploratórios via CDP: endpoint /backend-api/stop_conversation retornou 200 em todos e a UI ficou parcial. Dois streams terminaram com ERR_ABORTED/canceled=true; um com loadingFinished, mas DPU ainda in_progress/end_turn=null. Repetir via extensão e comparar com resposta normal. |
| 6 | Geração de arquivos e artefatos | O conteúdo do arquivo é transportado no stream da conversa ou por uma transferência/URL separada? Como associar o artefato à resposta? | Capturar pelo menos dois tipos de artefato; distinguir metadados/placeholder do conteúdo binário e validar tipo, tamanho e hash do arquivo baixado. | Executado exploratoriamente via CDP na mesma aba para CSV e PDF: stream e transferências separados; MIME, nome, tamanho e hash verificados. Falta validar o mesmo fluxo pela extensão. |

### Teste 1 — captura integral do corpo

Use três prompts que produzam respostas curtas (2 parágrafos), médias (8) e longas (16), mantendo idioma e formato. Capture desde responseReceived até o encerramento. Registre o buffer inicial, os eventos dataReceived, a forma usada para recuperar o corpo final, os tamanhos, o código de encerramento e o estado final da interface. Não use só a contagem de chunks como evidência de captura completa.

As medições exploratórias anteriores de volume podem servir como comparação auxiliar, não como prova de que o conteúdo foi integralmente recuperado. Bytes maiores em respostas longas sustentam apenas uma relação de volume, não uma regra de reconstrução. A amostra atual teve uma resposta curta com corpo maior do que as respostas média e longa; os totais incluem quadros, controles e possivelmente estado/contexto, portanto não estimam diretamente o texto da resposta.

### Teste 2 — decodificação de quadros e snapshots

Comece com duas respostas em parágrafos e avance para lista e código. Inspecione quadros DPU em sequência, registre nomes dos controles e campos de atualização que não sejam segredos. Aplique substituições/revisões na ordem de chegada; documente se o estado final depende do snapshot mais recente por índice ou de outra lógica. Compare o texto somente após obter todos os blocos finais.

Resultado de 2026-10-07: ver [Teste 2 no relatório experimental](relatorio-experimental-streaming.md#teste-2--decodificação-de-quadros-e-snapshots). Foram observadas operações `replace` para snapshots completos e `append` para conteúdo incremental/caudas; não apareceu operação `remove`. Os quatro corpos decodificados coincidiram em bytes com a soma de `dataLength`, e os estados finais reconstruídos coincidiram com a interface. Isso confirma o procedimento nestes quatro exemplos, não a semântica geral de todo controle ou formato.

### Teste 3 — fidelidade e cobertura de formatos

Executar, duas vezes cada:

- prosa em parágrafos;
- lista numerada e lista com marcadores;
- bloco de código com pontuação e delimitadores;
- texto com acentos, aspas, emoji e símbolos;
- Markdown misto com título, negrito, tabela simples e link textual.

Para cada saída, avalie texto e formatação separadamente. Igualdade textual após remover espaços não prova igualdade estrutural; registre exatamente o que foi normalizado. Use a interface apenas para validação final. A medição de timing DOM/rede é opcional e secundária a este objetivo.

Resultado de 2026-10-07: as duas amostras de prosa e uma de código do Teste 2 também serviram como repetições; no Teste 3 foram capturados os demais exemplos necessários. As nove capturas adicionais tiveram corpo decodificado igual à soma de `dataLength`. Veja a matriz por formato e os detalhes de operações no [relatório experimental](relatorio-experimental-streaming.md#teste-3--fidelidade-e-cobertura-de-formatos). Uma captura de lista teve `ERR_NETWORK_CHANGED`; ela só foi considerada completa após conferir o corpo e o estado final da UI depois da reconexão.

### Teste 4 — identidade entre operações

Na mesma conversa, envie três prompts um por vez; depois, em outra conversa, repita um prompt. Se regeneração estiver disponível, use a ação da interface e registre-a como operação própria. Para cada operação, correlacione Network.requestId, data-request-id, operationId, conversationId e quaisquer IDs explícitos da mensagem do usuário/assistente ou parentMessageId.

Não infira que um atributo chamado data-message-id seja ID do assistente. Para identificar seu papel, relacione-o ao alvo semântico no payload e ao estado final da conversa em mais de uma operação.

### Teste 5 — terminação, Stop e tráfego auxiliar

Faça uma resposta normal e pelo menos três respostas longas com Stop em momentos diferentes. Registre o momento da ação, request de cancelamento se houver, último dataReceived, controles terminais, estado parcial/final da UI e loadingFinished/loadingFailed. Compare requests auxiliares no mesmo intervalo pelo caminho sem query e função observada. Não interprete tráfego de telemetria ou preparação como conteúdo da resposta.

Classifique como cancelamento pelo usuário apenas quando a ação Stop, a evidência de cancelamento da operação e a UI parcial forem coerentes. ERR_ABORTED pode aparecer após conclusão normal.

### Teste 6 — geração de arquivos e artefatos

Gere pela interface pelo menos dois artefatos de tipos distintos, usando conteúdo sintético e não sensível (por exemplo, CSV e PDF ou planilha; inclua imagem gerada ou outro artefato semelhante quando estiver disponível). Para cada caso, registre a resposta em `/conversation/updates` e os requests relacionados ao link/controle de download. Correlacione-os à resposta somente por IDs ou relações efetivamente observados e pela sequência da interface.

Capture separadamente o corpo do stream e a resposta de download/artefato. Registre caminho sem query, status, MIME type, nome de arquivo, tamanho e hash local dos bytes baixados; não registre cookies, tokens, credenciais nem URLs assinadas completas. Verifique se o stream contém os bytes, apenas metadados/placeholder ou uma referência para transferência separada. Compare tamanho e hash do arquivo baixado com os bytes obtidos, e confirme que a interface apresenta o artefato final correto e permite abri-lo/baixá-lo. Se a captura de bytes não for possível, documente a lacuna em vez de tratar metadados como conteúdo.

## Como relatar

Use o relatório para registrar fatos observados, não hipóteses como fatos. Para toda conclusão, indique número de execuções, rota/sessão, critério de comparação e limites. Separe:

- **Confirmado nesta execução:** resultado diretamente observado.
- **Sustentado na amostra:** repetição suficiente para padrão provisório.
- **Hipótese:** explicação ainda sem validação.
- **Em aberto:** campo ou formato não capturado.

O objetivo experimental atual é reconstruir o conteúdo. Uma relação temporal entre rede e DOM pode ser registrada como evidência secundária, mas não substitui a validação de que o texto final veio do corpo capturado.
