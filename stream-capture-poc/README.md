# POC local de captura de stream

Variante isolada da POC de rede existente. Reaproveita o observador `fetch` no mundo `MAIN` e o parser DPU/SSE, mas remove associação a conta, pessoa, instalação, projeto, prompt e conversa. O objetivo é validar a captura da resposta e sua persistência local em SQLite.

## O que persiste

- Texto da resposta reconstruído em ordem de blocos DPU.
- Métricas e rótulos técnicos: endpoint, status, MIME, bytes, chunks, frames, marcador de fim, duração, forma dos eventos e sequência de tipos/formatos.
- Identificador aleatório por tentativa, usado apenas para idempotência.

Não guarda o corpo SSE bruto, prompt, URL da conversa, conta, pessoa, ID de máquina, cookies ou cabeçalhos da página. A sonda só observa `POST /backend-api/f/conversation` com `text/event-stream`; não altera a resposta consumida pelo ChatGPT. Snapshots completos e respostas parciais com texto são enviados com classificação explícita `complete`/`incomplete`; uma captura incompleta nunca declara conclusão do protocolo.

## Preparar e executar

Requer Python 3.11+ e Chrome ou Chromium. Não instala dependências Python nem usa a API oficial de identificação do backend.

1. O `backend/.env` local já foi criado a partir de `backend/.env.example`, com token aleatório próprio, banco em `backend/data/stream-captures.sqlite3`, retenção de sete dias e bind somente em `127.0.0.1:8766`. O `.env` e o banco estão ignorados pelo Git.
2. Inicie a API a partir desta pasta:

   ```sh
   cd backend
   python server.py
   ```

3. Em `chrome://extensions`, ative o modo do desenvolvedor e carregue a pasta `extension` como extensão descompactada. Depois, recarregue a aba do ChatGPT.
4. Abra o popup da extensão, cole o valor de `LAB_API_TOKEN` de `backend/.env` e marque **Ativar captura**. O token só fica em `chrome.storage.session`; será necessário inseri-lo de novo depois que o navegador encerrar a sessão.
5. Na aba do ChatGPT, use um prompt sintético. O popup lista capturas entregues; a API confirma o armazenamento em SQLite.

Para conferir uma captura armazenada, use o endpoint local autenticado `GET http://127.0.0.1:8766/v1/stream-captures/recent` com o token de laboratório. A rota devolve no máximo 20 respostas recentes. A rota pública `/health` confirma que a API e o SQLite inicializaram.

## Limites deste primeiro teste

- É uma prova de conceito dependente da implementação web atual; mudanças no formato DPU/SSE podem exigir atualização do parser.
- Os ensaios de geração de TXT e CSV pela extensão chegaram ao SQLite, mas a reconstrução do texto ficou incompleta/corrompida. A transferência do arquivo e seus metadados estruturados ainda não são capturados nesta variante; corrigir o parser DPU é o próximo passo. Consulte [PROGRESSO_TESTES_CAPTURA.md](PROGRESSO_TESTES_CAPTURA.md) para os resultados dos testes 1–4.
- Respostas interrompidas e erros de stream com texto parcial são armazenados como `incomplete`; a ausência de texto de resposta não cria registro.
- A comunicação com a API local exige token aleatório de laboratório; esse token autoriza escrita local, mas não identifica uma pessoa.
- Desative a captura no popup após os ensaios e use apenas conteúdo sintético enquanto a POC estiver ativa.

## Verificações locais

```sh
cd backend
python -m unittest discover -s tests -v
cd ../extension
node --check src/content/network-probe-main.js
node --check src/content/network-bridge.js
node --check src/background/service-worker.js
node --check src/popup/popup.js
```
