# Handoff — captura de respostas em stream

**Atualizado em:** 8 de outubro de 2026

**Projeto:** POC isolada em `stream-capture-poc`

**Objetivo:** validar a captura de respostas do ChatGPT pela extensão de navegador e a persistência local em SQLite, sem associar dados a usuário, máquina, prompt ou conversa.

## Estado atual

A POC observa, no mundo `MAIN` da página, o `fetch` da rota `POST /backend-api/f/conversation` quando a resposta é `text/event-stream`. O parser interpreta frames DPU/SSE e tenta reconstruir o texto da resposta. Uma ponte envia o resultado à API local, que valida o token de laboratório e grava a captura no SQLite.

O corpo bruto da stream não é persistido. O registro inclui o texto reconstruído e metadados técnicos como status, MIME, bytes, chunks, frames, marcador de término, duração e resumos dos formatos de evento. A implementação não extraiu nem persiste metadados estruturados de arquivos nesta etapa.

O Brave foi usado pelo usuário para os ensaios da extensão. O controle de navegador disponível ao agente não expôs a sessão do Brave; portanto, os resultados abaixo vêm do diagnóstico da extensão e da consulta local ao SQLite, não de uma automação do navegador pelo agente.

## Resultados dos testes 1–4

Os quatro novos envios aparecem no SQLite com estado `complete`, marcador `[DONE]`, `protocol_done=1`, `reader_done=1` e `truncated=0`. Isso confirma recebimento e armazenamento da stream, mas não garante que o texto reconstruído esteja correto.

| Teste | Caso | Resultado armazenado | Avaliação |
|---|---|---|---|
| 1 | Resposta curta com duas linhas | `CAPTURA_INICIO\nlinha dois\nCAPTURA_FIM` | Reconstrução correta. 6.032 bytes, 15 frames. |
| 2 | Unicode e símbolos | `Ação: café, coração, ção.\nSímbolos: ✓ → • 😀` | Reconstrução correta, incluindo acentos, símbolos e emoji. 6.164 bytes, 15 frames. |
| 3 | Geração de arquivo TXT | `Arquivo \`poc-captBaixar o arquivo](sandbox:/mnt/data/poc-captura.txt)` | Captura armazenada, mas texto reconstruído está corrompido/incompleto. 14.540 bytes, 24 frames. |
| 4 | Geração de arquivo CSV | `Arquivo \`poc-captmnt/data/poc-captura.csv)` | Captura armazenada, mas texto reconstruído está corrompido/incompleto. 18.340 bytes, 25 frames. |

Há também um registro anterior de smoke test (`OK`), fora dos quatro testes acima.

## Conclusão técnica

- A extensão alcançou a API local e a API persistiu os quatro casos no SQLite.
- Os casos simples de texto, múltiplas linhas e Unicode passaram.
- Os dois casos de geração de arquivo expuseram uma falha no parser/reconstrutor de atualizações DPU: a resposta final foi armazenada como completa, mas seu texto ficou truncado ou montado incorretamente.
- `complete` descreve o encerramento observado da stream. Não é uma validação de fidelidade do texto reconstruído.
- A POC captura a resposta textual reconstruída e métricas técnicas. Não salva os bytes dos arquivos gerados nem os metadados estruturados de arquivo; isso ainda precisa ser investigado.

## Próximos passos

1. Corrigir o parser DPU para operações que substituem ou editam trechos já emitidos, preservando a ordem e os índices dos blocos.
2. Criar casos de teste sintéticos para snapshots, `append`, `replace`, patches em partes existentes, Markdown com links `sandbox:`, e atualizações que chegam em múltiplos frames.
3. Reexecutar os testes 1 e 2 como regressão e repetir os casos de TXT e CSV. Comparar o texto armazenado com a resposta final esperada.
4. Investigar separadamente a requisição de transferência do arquivo e onde os metadados (nome, MIME e tamanho) aparecem. Só então decidir como modelá-los no SQLite; não inferir metadados ausentes no stream da conversa.
5. Depois da fidelidade da reconstrução, validar limites: resposta interrompida, erro de rede, resposta sem texto e eventual PDF/arquivo adicional.
6. Documentar resultados novos aqui e atualizar o README da POC quando o comportamento deixar de ser experimental.

## Ambiente e notas de execução

- Extensão de navegador Manifest V3, API local em `127.0.0.1:8766` e SQLite local.
- Token de laboratório local; não incluir o token nem o `.env` no Git.
- A versão do adaptador estava em `0.1.2` nos diagnósticos fornecidos; o validador do backend foi ajustado para aceitar versões compatíveis `0.1.x`.
- A suíte do backend passou anteriormente: 5 testes. Não foi executada novamente durante a consolidação deste handoff.
- Evitar incorporar a pasta irmã `GovernancaCode-main` ou seus arquivos a esta POC/commit. Ela é um projeto separado.

## Como retomar em outro chat

Comece lendo este documento e `stream-capture-poc/README.md`. Em seguida, inspecione `stream-capture-poc/extension/src/content/network-probe-main.js`, em especial o processamento de patches DPU e a montagem de `textParts`. Mantenha conteúdo sintético e não armazene o corpo SSE bruto. A primeira entrega deve ser uma correção coberta por testes sintéticos, seguida da repetição dos casos TXT e CSV no Brave.
