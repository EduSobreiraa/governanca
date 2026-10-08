# Método e resultados da captura de respostas

**Atualizado em:** 8 de outubro de 2026

**Escopo:** ensaios exploratórios de captura de respostas do ChatGPT pela rede, incluindo geração e download de arquivos.

## Resumo

O progresso estava documentado em dois arquivos: um protocolo de validação e um relatório experimental. Este documento reúne o método aplicado e os principais resultados num só lugar.

Até agora, a reconstrução de respostas foi verificada em capturas exploratórias feitas com CDP na mesma aba do navegador. Em 8 de outubro, uma conversa independente validou prosa, lista, Unicode e bloco de código: o corpo de 11.981 bytes igualou a soma de `dataLength` e a reconstrução normalizada coincidiu com o DOM. Três interrupções também foram capturadas. Em um ensaio anterior com CSV e PDF, a resposta textual e a transferência do arquivo apareceram em requisições distintas. Ainda falta comparar esses resultados com a extensão no ambiente em que ela será ativada.

## Objetivo e limites

O objetivo é reconstruir a resposta a partir dos eventos e corpos de resposta da rede, comparar o resultado com o que a interface exibiu e identificar metadados de arquivos. A interface serve como referência de comparação depois que a reconstrução é congelada.

Os ensaios descritos aqui usam captura exploratória via CDP. Eles demonstram o que foi possível observar nessa sessão e não comprovam que a extensão de navegador já captura os mesmos dados. A extensão é o caminho previsto para a coleta em cada máquina e precisa de validação própria.

## Sequência de trabalho combinada

1. Terminar os métodos e casos com a captura exploratória. A conversa independente, os formatos Markdown e três interrupções já foram cobertos; a regeneração continua pendente porque a interface não ofereceu essa ação.
2. Comparar a captura da extensão numa sessão em que ela esteja ativada no ambiente de teste.
3. Adaptar a extensão ao método de captura que passar pela validação exploratória e comparativa.

## Método de captura usado

### Respostas em streaming

1. Usar uma única aba do ChatGPT e registrar, para o ensaio, data, rota e ação executada. Não persistir cookies, tokens, URLs assinadas, identificadores de sessão ou cabeçalhos de autenticação.
2. Conectar o CDP diretamente à aba em teste e habilitar o domínio `Network`. Marcar o cursor dos eventos antes de enviar a solicitação, interromper ou regenerar uma resposta.
3. Identificar a requisição pelo caminho, sem parâmetros de query. Registrar método, status, `Content-Type` e contexto do ensaio, omitindo dados sensíveis.
4. Durante a resposta, `Network.streamResourceContent` pode retornar apenas o buffer já acumulado. Em capturas iniciais, esse buffer continha 446 bytes e não representava o corpo inteiro.
5. Reunir os eventos `Network.dataReceived` até `Network.loadingFinished` ou `Network.loadingFailed`. Depois de `loadingFinished`, obter o corpo com `Network.getResponseBody`; em caso de falha, tentar novamente `Network.streamResourceContent` quando aplicável.
6. Se o corpo vier em Base64, decodificá-lo. Comparar o tamanho do corpo recuperado com a soma de `dataLength` dos eventos `dataReceived`; registrar também `encodedDataLength` quando disponível.
7. Registrar eventos da interface, como desaparecimento do botão de parar. `ERR_ABORTED` isoladamente não prova cancelamento: nos ensaios de download abaixo, o evento apareceu apesar de o arquivo ter sido baixado com sucesso.
8. Reconstruir a resposta sem consultar o texto final da interface. Só então comparar a reconstrução com a resposta exibida.

### Acesso à aba e diferença em relação à extensão

Nos ensaios mais recentes, o CDP foi obtido da própria aba aberta no navegador do aplicativo (`agent.browsers.get("2")`, `browser.tabs.get("1")` e `agentTab.capabilities.get("cdp")`). Isso corrigiu uma divergência anterior: uma sessão DevTools separada estava mostrando outra página e um desafio Cloudflare, não a aba do ensaio.

Os IDs de navegador/aba são transitórios e não são identificadores de produção. A captura direta via CDP é uma ferramenta de exploração e não deve ser confundida com a implementação da extensão. A extensão precisa ser testada no mesmo fluxo e fornecer, por máquina, os dados que a solução pretende coletar.

### Reconstrução dos blocos

Nos exemplos observados, os frames DPU carregam snapshots de blocos. Processar os frames em sequência, substituir o estado do bloco correspondente ao índice indicado, manter os blocos finais e ordenar pelo índice antes de concatenar. Foi observado comportamento de substituição e acréscimo; não foi observado remoção nos exemplos testados. A comparação final com o DOM/UI ocorreu somente depois da reconstrução.

## Matriz de resultados

| Ensaio | Situação | Resultado observado | Próximo passo |
|---|---|---|---|
| 1. Captura integral | Validado exploratoriamente em conversa independente | Além das três respostas anteriores, uma resposta nova teve corpo de 11.981 bytes igual à soma de `dataLength`. A primeira tentativa falhou com `ERR_NETWORK_CHANGED`; o reenvio capturou o stream completo. | Repetir na extensão quando ela estiver disponível. |
| 2. Decodificação e snapshots | Validado nos exemplos executados | A resposta de teste foi reconstruída das operações DPU e coincidiu com o DOM após remover marcadores Markdown e normalizar espaços. | Repetir via extensão. |
| 3. Formatos de resposta | Validado nos exemplos executados | Prosa, listas, código, caracteres especiais, Markdown misto e Unicode (`βeta`) corresponderam ao conteúdo renderizado. | Repetir via extensão e cobrir variações adicionais. |
| 4. Identidade e regeneração | Parcial | Em três mensagens do assistente na conversa, os `data-message-id` do DOM eram únicos; o `message.id` do segundo turno capturado no stream correspondeu ao DOM. `conversation_id` do stream correspondeu à rota; o ID de requisição CDP diferiu do `metadata.request_id` do backend. Em 8/10, inspecionei o menu de uma resposta interrompida e de uma resposta concluída (resposta sintética `OK`); nenhuma ofereceu regeneração. | Correlacionar mais turnos e repetir regeneração quando houver controle disponível. |
| 5. Interrupção e eventos auxiliares | Três interrupções exploratórias via CDP | Em 3/3 o endpoint `POST /backend-api/stop_conversation` retornou 200 e a UI ficou parcial. Dois streams terminaram com `ERR_ABORTED` (`canceled=true`); um terminou com `loadingFinished`, embora o DPU ainda marcasse `in_progress` e `end_turn=null`. | Repetir via extensão e comparar também com geração normal. |
| 6. Geração e transferência de arquivos | Executado exploratoriamente via CDP | CSV e PDF foram gerados e baixados. A resposta de conversa, os metadados do download e a transferência do conteúdo apareceram em requisições separadas. | Repetir os mesmos casos pela extensão. |

## Ensaio 6: CSV e PDF

Os arquivos continham dados sintéticos. Os valores abaixo descrevem a captura local e as respostas observadas; URLs assinadas, IDs de conversa e valores de credenciais não foram retidos.

### CSV

- Solicitação de geração: `POST /backend-api/f/conversation`, status 200, `Content-Type: text/event-stream`.
- Corpo do stream: 37.372 bytes, igual à soma de `dataLength`; `encodedDataLength`: 40.567; foram observados 43 frames JSON.
- O nome do arquivo apareceu no texto da resposta. As linhas do CSV e campos explícitos de artefato (tipo, MIME, tamanho ou URL) não apareceram no stream.
- Metadados: `GET /backend-api/conversation/:conversationId/interpreter/download`, status 200, `application/json`, `dataLength` 341. O status era `success`, mas `file_name`, `mime_type` e `file_size_bytes` estavam nulos.
- Transferência: `GET /backend-api/estuary/content`, status 200, `text/csv`; `Content-Disposition` indicou `teste-captura-completo.csv`.
- O evento de rede terminou como `ERR_ABORTED`, mas o evento de download do Playwright terminou e o arquivo estava presente.
- Arquivo local `teste-captura-completo.csv`: 78 bytes; MIME `text/csv`; SHA-256 `f72e692706aff4ecf2f6f4ff54004dd43c0a1d862ad16a4c28bf9d8fcca42e8d`. Cabeçalho e três linhas sintéticas foram conferidos.

### PDF

- Solicitação de geração: `POST /backend-api/f/conversation`, status 200, `Content-Type: text/event-stream`.
- Corpo do stream: 23.176 bytes, igual à soma de `dataLength`; `encodedDataLength`: 26.359.
- O nome apareceu na resposta, mas o marcador `%PDF-`, o título e o conteúdo da tabela não apareceram no stream.
- Metadados: `GET /backend-api/conversation/:conversationId/interpreter/download`, status 200, `application/json`, `dataLength` 451; status `success`, `file_name=teste-captura.pdf`, `mime_type=application/pdf` e `file_size_bytes` nulo.
- Transferência: `GET /backend-api/estuary/content`, status 200, `application/pdf`; `Content-Disposition` indicou `teste-captura.pdf`.
- Também houve `ERR_ABORTED` na observação de rede, embora o download tenha sido concluído.
- Arquivo local `teste-captura.pdf`: 26.770 bytes; SHA-256 `7a3512d12586ea163009803ab583bce3b2f30edf42642142a7a41b899733f023`. Uma página e o texto do documento foram conferidos.

### Conclusão do ensaio de arquivos

Nos dois casos, a resposta em streaming mencionou o nome, mas não continha os bytes do arquivo. O conteúdo veio por uma requisição separada para `/backend-api/estuary/content`. A resposta JSON de metadados apresentou nome e MIME do PDF, mas não tamanho; para o CSV, nome, MIME e tamanho vieram nulos. Portanto, foi possível obter os metadados do PDF pela resposta JSON e do CSV pelos cabeçalhos da transferência, e verificar tamanho e hash nos arquivos baixados localmente.

## Ensaios adicionais em conversa independente e interrupções — 8 de outubro de 2026

### Formatos e reconstrução

Foi enviada uma resposta sintética com título, lista numerada contendo `alpha`, `βeta` e `linha 3`, e um bloco de código `txt` com `A&B <C>`. O primeiro envio terminou em `net::ERR_NETWORK_CHANGED` e a interface mostrou erro. Após reenviar o mesmo prompt numa conversa independente, o stream `POST /backend-api/f/conversation` retornou status 200 e `text/event-stream`.

O corpo recuperado teve 11.981 bytes, exatamente a soma de `dataLength` em 11 eventos `Network.dataReceived`. Após excluir do processamento o frame de token de retomada, foram decodificados 21 frames JSON. As operações DPU de texto reconstruíram o título, os três itens e o código. Removendo da reconstrução apenas a sintaxe Markdown e normalizando espaços, o resultado coincidiu com o texto dos nós de resposta no DOM. A comparação é normalizada porque o DOM renderiza a lista sem os numerais e remove as cercas do bloco de código.

### Identificadores

Na mesma conversa, um segundo turno sintético confirmou que `message.id` no snapshot de rede correspondeu ao `data-message-id` do respectivo nó do assistente no DOM. O `conversation_id` do stream correspondeu à rota da conversa. O `Network.requestId` do CDP era distinto do `metadata.request_id` presente na mensagem. Os três nós de resposta observados no DOM tinham IDs distintos. A opção de regenerar não apareceu nos controles disponíveis nessa conversa; a semântica de IDs em regenerações continua em aberto.

Em 8 de outubro, enviei também um turno curto sintético (`Teste de regeneração: responda apenas com a palavra OK.`), que terminou com `OK`. O menu de ações da resposta concluída ofereceu visualizar fontes, derivar chat e leitura em voz alta, sem opção de regenerar. Portanto, o caso de regeneração não pôde ser exercitado pela UI; não inferir seu comportamento a partir desse teste.

### Interrupções controladas

Foram iniciadas três respostas sintéticas longas e acionado `Parar` quando já havia texto parcial visível. Em todas as três, o endpoint auxiliar `POST /backend-api/stop_conversation` retornou status 200, o botão de parada desapareceu e a interface preservou uma resposta parcial.

- Interrupções 1 e 3: o stream terminou com `Network.loadingFailed`, `net::ERR_ABORTED` e `canceled=true`.
- Interrupção 2: o stream terminou com `Network.loadingFinished`, sem erro de transporte; ainda assim, o snapshot final permaneceu com status `in_progress` e `end_turn=null`, e a resposta visível estava incompleta.

Esse terceiro resultado confirma que `loadingFinished` sozinho não basta para classificar uma resposta como completa. É necessário considerar o estado DPU, a chamada de interrupção e a interface.

## Próximos passos

1. Comparar pela extensão a geração normal, os três fluxos interrompidos e a captura integral.
2. Repetir via extensão os casos CSV/PDF e verificar stream da conversa, JSON de metadados e transferência do conteúdo.
3. Validar tamanho e hash local pela extensão sem registrar URLs assinadas ou credenciais.
4. Concluir a semântica dos IDs em vários turnos e em regenerações quando a interface oferecer a ação.

## Documentos de referência

- [Protocolo de validação do streaming](protocolo-validacao-stream-llm.md)
- [Relatório experimental de streaming](relatorio-experimental-streaming.md)
