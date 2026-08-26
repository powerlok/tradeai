# Processos operacionais — Trading AI

Este documento descreve passo a passo os processos operacionais para desenvolver e rodar o scaffold do projeto: inicializar stack Docker, aplicar migrations, iniciar o coletor WebSocket, e comandos úteis para desenvolvimento e troubleshooting.

## 1. Preparação do ambiente

1. Entre na pasta do repositório dentro do WSL:

```bash
cd /mnt/c/Users/paulo.laredo/Documents/projetos/pessoal/trade
```

2. Copie o arquivo de exemplo de variáveis de ambiente e edite se necessário:

```bash
cp .env.example .env
# ou no PowerShell
Copy-Item .env.example .env
```

Ajuste `DATABASE_URL`, `REDIS_URL`, `OLLAMA_URL` conforme seu ambiente. No Docker nativo do WSL, `DATABASE_URL` usa `postgres` e `REDIS_URL` usa `redis`.

## 2. Subir a stack Docker (sem recriar containers existentes)

Foram providos dois scripts que evitam recriar containers quando já existem: `scripts/start_stack.sh` (Bash) e `scripts/start_stack.ps1` (PowerShell). Eles verificam se os containers nomeados existem e então apenas os iniciam; caso contrário criam a stack.

- Linux / macOS (Bash):

```bash
chmod +x ./scripts/start_stack.sh
./scripts/start_stack.sh
```

- Windows (PowerShell):

```powershell
# abrir PowerShell com permissões adequadas
.\scripts\start_stack.ps1        # inicia sem rebuild
.\scripts\start_stack.ps1 -Build  # força rebuild do backend
```

Observações:
- Para forçar rebuild manualmente com `docker compose`: `docker compose up -d --build`.
- Os containers possuem nomes fixos (ver `docker-compose.yml`): `trading_postgres`, `trading_redis`, `trading_backend`, `trading_ollama`.
- O MCP usa o container `trading_mcp_market` e a porta `9000`.

Para sincronizar a senha administrativa configurada no `.env` com o hash do usuário no PostgreSQL:

```bash
docker compose restart backend
docker compose exec backend python scripts/sync_admin_password.py
```

## 3. Aplicar migrations / criar schema inicial

Arquivo SQL inicial: `migrations/init.sql`.

Execute após o container `trading_postgres` estar rodando:

```bash
docker exec -i trading_postgres psql -U trader -d trading < migrations/init.sql
```

Se preferir, abra um client psql e cole o conteúdo de `migrations/init.sql`.

> Recomenda-se adicionar Alembic posteriormente para migrações controladas.

## 4. Rodar o coletor WebSocket

Opções:

- Dentro do container `trading_backend` (recomendado, mantém ambiente idêntico):

```bash
docker exec -it trading_backend python scripts/run_collector.py
```

- Local (se tiver Python e dependências instaladas):

```bash
pip install -r requirements.txt
python scripts/run_collector.py
```

O coletor inicia streams públicos da Binance (`trade` e `depth`) para os símbolos definidos em `app/market/ws_collector.py`.

## 5. Logs e diagnóstico

- Verificar containers e status:

```bash
docker compose ps
```

- Ver logs em tempo real:

```bash
docker compose logs -f
# ou logs de um container específico
docker logs -f trading_backend
```

- Se `docker compose up` falhar com Exit Code 1, veja logs com `docker compose logs` e corrija o erro; mensagens comuns:
  - Dependências Python faltando (`pip install -r requirements.txt`).
  - Porta em uso (verificar `8001`, `4173`, `5432`, `6379`, `11434`).
  - Volume/path permission issues em Windows — execute PowerShell como administrador se necessário.

## 6. Parar e remover

- Parar containers:

```bash
docker compose stop
```

- Parar e remover (recria todo o estado na próxima vez):

```bash
docker compose down
```

## 7. Fluxo recomendado para desenvolvimento

1. Ajustar `.env` conforme ambiente.
2. `./scripts/start_stack.sh` ou `.	ests
un_collector.ps1` para levantar serviços.
3. Aplicar `migrations/init.sql` (apenas na primeira vez).
4. Rodar coletor e observar logs.
5. Executar endpoints locais (FastAPI em `http://localhost:8001/api/health`).

## 8. Operar e validar o MCP

O MCP é complementar e isolado. Não precisa de PostgreSQL nem de uma segunda instância do Ollama. Depende do Redis para cache e consulta Binance, CoinGecko e RSS públicos.

```bash
docker compose up -d --build mcp_market
docker compose ps mcp_market redis
docker compose logs --tail=100 mcp_market
```

Listar ferramentas:

```bash
curl -X POST http://localhost:9000/mcp -H 'Accept: application/json, text/event-stream' -H 'Content-Type: application/json' -H 'MCP-Protocol-Version: 2025-06-18' -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

Ferramentas: `get_market_overview`, `get_multi_timeframe_analysis`, `get_market_news` e `research_assets`. O overview CoinGecko fica em cache por 60 segundos; notícias RSS por 300 segundos. Falhas de feeds são parciais e não devem derrubar o chat.

## 9. Diagnóstico do chat

1. Confirme `trading_backend`, `trading_mcp_market`, `trading_redis` e `trading_ollama` ativos.
2. Verifique `curl http://localhost:8001/api/health`.
3. Liste as ferramentas MCP com o comando acima.
4. Observe `docker compose logs backend mcp_market` durante uma pergunta.
5. Se o MCP falhar, o backend deve continuar com a pesquisa direta.

O `model_retrainer` é limitado a 1 CPU no Compose. O treinamento usa validação cruzada e pode consumir múltiplos núcleos; o limite evita que esse processo concorra com o backend, frontend e MCP durante o uso interativo.

## 10. Próximos passos/automatizações sugeridas

- Adicionar Alembic para gerenciar migrations e criar um comando `scripts/apply_migrations.sh`.
- Incluir um `entrypoint` no container `backend` que aplique migrations automaticamente em dev (opcional) e depois inicie o servidor.
- Adicionar healthchecks Docker para `trading_postgres` e `trading_ollama`.
- Automatizar a provisão de modelos Ollama (se aplicável) no diretório `./ollama-data`.

---

Se quiser, eu posso:
- criar `scripts/apply_migrations.*` que aplicam `migrations/init.sql` automaticamente após `start_stack`, ou
- configurar Alembic e adicionar a etapa de `alembic upgrade head` no processo de start.

Diga qual automação prefere que eu implemente. 
