**Visão Geral**

Este documento descreve o que foi implementado no projeto de coleta de mercado, armazenamento e observabilidade. Contém um resumo do trabalho, o fluxo de dados, instruções de execução e verificações rápidas.

**O que foi feito**

- Scaffold do repositório e ambiente Docker Compose para desenvolvimento.
- Backend FastAPI com coletor (`scripts/run_collector.py`).
- Implementação de `WebSocketCollector` e fallback REST (`rest_poller`).
- Persistência idempotente em PostgreSQL (`trades`, `order_book_snapshots`).
- Migrations para deduplicação e normalização (`migrations/012*`, `migrations/013*`).
- Conversão de snapshots para `jsonb` e adição de `bids_count`/`asks_count`.
- Instrumentação Prometheus e regras de alerta básicas.
- Chat contextual com Ollama, tool calling, MCP, Binance, CoinGecko e RSS de notícias.
- Cache Redis para overview de mercado e notícias, com fallback por fonte.
- Página React de notícias cripto em `/news`, com destaque, filtro por fonte e atualização manual.
- Endpoint autenticado `GET /api/news?limit=24` para notícias gerais de CoinDesk, Cointelegraph e Decrypt.
- Fase 2 de Market Data com candles `1d`, `4h`, `1h`, `15m` e `5m`, além de `bookTicker` WebSocket.
- Fase 3 de Normalização com contratos comuns para candles, trades, order book e `bookTicker`.
- APIs quantitativas para multi-timeframe, oportunidades, walk-forward e posições paper virtuais.
- Observabilidade Prometheus inclui sinais, rejeições de qualidade, notícias enriquecidas, validações LLM e operações paper; fora do container, a dependência é opcional para testes locais.
- Frontend 2.0 incremental: `/opportunities` apresenta ranking multiativo, alinhamento de timeframes, regime, score, probabilidade e R/R; Strategy Lab usa Backtest V2.

**Arquitetura e componentes principais**

- Coletor (processo Python): tenta WS → se falha, usa REST poller.
- Adaptadores de mercado: `app/market/binance_adapter.py` (REST) e `app/market/ws_collector.py` (WS).
- Backend: FastAPI serve APIs e executa o coletor no container `trading_backend`.
- Banco: PostgreSQL (`trading_postgres`) com constraints únicas e colunas `jsonb` para snapshots.
- Observability: `app/observability/metrics.py` expõe métricas Prometheus (porta 8001 no container).

**Fluxo de dados**

1. Coletor recebe dados (WS ou REST).
2. Para cada trade: `persist_trade()` executa `INSERT ... ON CONFLICT DO NOTHING` em `trades`.
3. Para cada snapshot: insere em `order_book_snapshots` como `jsonb` e grava `bids_count`/`asks_count`.
4. Migrations cuidaram da deduplicação histórica e normalização dos dados antigos.
5. Métricas são incrementadas após persistência bem-sucedida.

**Principais arquivos**

- `scripts/run_collector.py` — ponto de entrada do coletor (WS + fallback REST).
- `app/market/binance_adapter.py` — chamadas REST à Binance.
- `app/market/ws_collector.py` — lógica de WebSocket streaming.
- `app/market/normalizer.py` — normalização de payloads REST e WebSocket antes da persistência.
- `app/db/models.py` — modelos SQLAlchemy e constraints.
- `app/observability/metrics.py` — métricas Prometheus.
- `migrations/012_add_constraints_and_normalize.sql` — dedupe + jsonb + contagens.
- `migrations/013_rebuild_trades_dedup_swap.sql` — rebuild de `trades` sem duplicatas.
- `monitoring/prometheus/alerts.yml` — regras de alerta exemplo.

**Como executar (WSL recomendado)**

1. Subir/reconstruir stack:

```bash
wsl -e bash -lc "docker compose up -d --build"
```

2. Reiniciar apenas backend (quando necessário):

```bash
wsl -e bash -lc "docker compose restart backend"
```

3. Ver logs do backend:

```bash
wsl -e bash -lc "docker logs --since 1m trading_backend | tail -n 200"
```

4. Verificar últimas snapshots e contagens no Postgres:

```bash
wsl -e bash -lc 'docker exec trading_postgres psql -U trader -d trading -c "SELECT id, symbol, bids_count, asks_count FROM order_book_snapshots ORDER BY id DESC LIMIT 5;"'
```

5. Teste rápido de inserção DB (executa um `INSERT` que usa `jsonb_array_length` para computar contagens):

```bash
wsl -e bash -lc "docker exec -i trading_postgres psql -U trader -d trading <<'SQL'
INSERT INTO order_book_snapshots (symbol,event_time,bids,asks,bids_count,asks_count)
VALUES ('TEST1', 123456, '[ [\"1\",\"2\"], [\"3\",\"4\"] ]'::jsonb, '[ [\"5\",\"6\"] ]'::jsonb,
        jsonb_array_length('[ [\"1\",\"2\"], [\"3\",\"4\"] ]'::jsonb), jsonb_array_length('[ [\"5\",\"6\"] ]'::jsonb)
);
SELECT id, symbol, bids_count, asks_count FROM order_book_snapshots WHERE symbol='TEST1' ORDER BY id DESC LIMIT 1;
SQL"
```

**Verificações úteis**

- Métricas Prometheus: confirme que o collector chama `metrics.inc_trade()` e `metrics.inc_snapshot()` e que `/metrics` é acessível na porta 8001 do container.
- Confirme que `trades` e `order_book_snapshots` não têm duplicatas usando as constraints únicas.

**Problemas conhecidos & notas**

- Em Windows+WSL, eventuais problemas de egress/WS podem ocorrer; reiniciar o daemon Docker no WSL costuma resolver.
- Algumas linhas históricas (pré-migração) podem ter `bids_count`/`asks_count` iguais a zero; novos inserts devem preencher corretamente.
- A migration `migrations/014_market_data_timing_book_ticker.sql` adiciona `received_time` às tabelas de mercado e cria `book_tickers`.
- A migration `migrations/015_paper_trades.sql` cria a persistência de posições virtuais.
- A migration `migrations/016_news_intelligence.sql` cria o histórico de notícias enriquecidas.
- O container `trading_ollama` pode conflitar por porta (`11434`) com outras instâncias locais — ajuste `docker-compose` se necessário.

## MCP e notícias

O MCP está no container `trading_mcp_market`, disponível em `http://localhost:9000/mcp`. Ele depende apenas do Redis e consulta APIs públicas; não exige banco próprio, credenciais de exchange ou uma segunda instância do Ollama.

Ferramentas disponíveis:

- `get_market_overview`: CoinGecko.
- `get_multi_timeframe_analysis`: Binance.
- `get_market_news`: CoinDesk, Cointelegraph e Decrypt RSS.
- `research_assets`: pesquisa combinada por pergunta.

O chat chama `research_assets` ou `get_market_news` por tool calling e recebe os dados antes da resposta final em streaming. Notícias só entram na resposta quando possuem título, fonte, data e URL; ausência de notícia não é tratada como ausência de dados de preço.

A página `/news` usa diretamente `GET /api/news` e apresenta as manchetes recebidas dos feeds RSS. Ela não fabrica resumo, imagem ou categoria quando esses campos não são fornecidos pela fonte. O cache das notícias dura 300 segundos e a página permite atualização manual.

No ambiente atual, o Docker Engine roda nativamente dentro do WSL Ubuntu. O frontend fica disponível em `http://localhost:4173` e a API em `http://localhost:8001`.

O provider pode ser alternado sem alterar o frontend: `AI_PROVIDER=ollama` usa `llama3.2:latest` local; `AI_PROVIDER=groq` usa `GROQ_API_KEY` e `GROQ_MODEL`. O contrato de tool calling MCP e streaming é mantido nos dois adapters.

## Notificações

`GET /api/notifications` lista os eventos do usuário autenticado e `DELETE /api/notifications/{id}` remove um item. A resposta concluída do chat publica `chat_response` no Redis. O frontend consulta esse endpoint a cada 5 segundos e exibe uma notificação global. `trend_change` está reservado para um futuro monitor de tendência com regras verificadas.

Verificação:

```bash
docker compose ps mcp_market redis
docker compose logs --tail=100 mcp_market
```

**Próximos passos recomendados**

1. Confirmar que o processo do collector em `trading_backend` é o rebuild que inclui `bids_count`/`asks_count` e reiniciar se necessário.
2. Adicionar uma migration Alembic para gerenciar mudanças futuras de schema.
3. Configurar Prometheus scrape job + Alertmanager (Slack/email) para as regras em `monitoring/prometheus`.
4. Implementar Feature Engine e Dataset Builder conforme o roadmap.

---

Arquivo gerado automaticamente pelo assistente — adapte conforme desejar.
