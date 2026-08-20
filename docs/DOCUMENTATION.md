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
- O container `trading_ollama` pode conflitar por porta (`11434`) com outras instâncias locais — ajuste `docker-compose` se necessário.

**Próximos passos recomendados**

1. Confirmar que o processo do collector em `trading_backend` é o rebuild que inclui `bids_count`/`asks_count` e reiniciar se necessário.
2. Adicionar uma migration Alembic para gerenciar mudanças futuras de schema.
3. Configurar Prometheus scrape job + Alertmanager (Slack/email) para as regras em `monitoring/prometheus`.
4. Implementar Feature Engine e Dataset Builder conforme o roadmap.

---

Arquivo gerado automaticamente pelo assistente — adapte conforme desejar.
