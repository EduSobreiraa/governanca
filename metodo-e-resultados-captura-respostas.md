# Método e resultados da captura de respostas

**Atualizado em:** 7 de outubro de 2026  
**Escopo:** ensaios exploratórios de captura de respostas do ChatGPT pela rede, incluindo geração e download de arquivos.

## Resumo

O progresso estava documentado em dois arquivos: um protocolo de validação e um relatório experimental. Este documento reúne o método aplicado e os principais resultados num só lugar.

Até agora, a reconstrução de respostas foi verificada em capturas exploratórias feitas com CDP na mesma aba do navegador. Em um ensaio com CSV e PDF, a resposta textual e a transferência do arquivo apareceram em requisições distintas. O teste exploratório de arquivos foi bem-sucedido; ainda falta repetir os fluxos pela extensão de navegador, que é o mecanismo planejado para coleta em cada máquina.

## Objetivo e limites

O objetivo é reconstruir a resposta a partir dos eventos e corpos de resposta da rede, comparar o resultado com o que a interface exibiu e identificar metadados de arquivos. A interface serve como referência de comparação depois que a reconstrução é congelada.

Os ensaios descritos aqui usam captura exploratória via CDP. Eles demonstram o que foi possível observar nessa sessão e não comprovam que a extensão de navegador já captura os mesmos dados. A extensão é o caminho previsto para a coleta em cada máquina e precisa de validação própria.

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
| 1. Captura integral | Parcialmente validado | Em três respostas da mesma conversa sem anexos, o corpo recuperado correspondeu à soma de `dataLength`. | Repetir numa conversa independente. |
| 2. Decodificação e snapshots | Validado nos exemplos executados | Quatro respostas (duas em prosa, uma lista e um bloco de código) foram reconstruídas e comparadas com a interface. Foi observado substituir e acrescentar blocos. | Repetir via extensão. |
| 3. Formatos de resposta | Validado nos exemplos executados | Prosa, listas numeradas e com marcadores, código, caracteres especiais e Markdown misto corresponderam à interface. Uma lista teve `ERR_NETWORK_CHANGED`, mas a resposta terminou e a interface reconectou. | Repetir via extensão e cobrir variações adicionais. |
| 4. Identidade e regeneração | Parcial | Foram observados `Network.requestId`, `operationId` e `conversationId`. A semântica do `data-message-id` e o vínculo entre regenerações ainda não foram confirmados. | Investigar IDs em respostas e regenerações controladas. |
| 5. Interrupção e eventos auxiliares | Parcial | `ERR_ABORTED` apareceu após respostas completas e em ações de parar. Um ensaio longo interrompido mostrou resposta parcial na interface, mas não teve captura de rede correspondente. | Repetir com a extensão, cobrindo conclusão normal e pelo menos três interrupções. |
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

## Próximos passos

1. Repetir o ensaio CSV/PDF instrumentando a extensão e verificar se ela observa a resposta de conversa, o JSON de metadados e a transferência do conteúdo.
2. Validar o cálculo de tamanho e hash local pela extensão sem registrar URL assinada ou credenciais.
3. Repetir a captura integral e a reconstrução em conversa independente.
4. Concluir a semântica dos IDs e a associação de mensagens regeneradas.
5. Repetir o ensaio de interrupção com a extensão, incluindo conclusão normal e pelo menos três ações de parar.

## Documentos de referência

- [Protocolo de validação do streaming](protocolo-validacao-stream-llm.md)
- [Relatório experimental de streaming](relatorio-experimental-streaming.md)
