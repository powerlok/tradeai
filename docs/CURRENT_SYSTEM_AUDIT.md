| Ollama guardrails | saída estruturada validada e sem alterar score | Contrato agnóstico e endpoint de validação contextual | IMPLEMENTADA |
# CURRENT SYSTEM AUDIT

Data da auditoria: 2026-08-24
Escopo: Fase 0 do documento `docs/sistema.md`.

## Status do checkpoint

A Fase 0 foi executada sem iniciar a Fase 1. O sistema existente foi preservado. Este documento registra o estado observado, os desvios em relação ao alvo e o plano incremental.

## 1. Arquitetura atual

O sistema roda em Docker Compose com Docker Engine nativo dentro do WSL Ubuntu. O fluxo implementado é:

```text
Binance REST/WebSocket
        -> collectors
        -> PostgreSQL
        -> Feature Engine
        -> modelos ML
        -> sinais BUY/SELL/WATCH
        -> FastAPI
        -> React/Vite
```

O chat adiciona MCP, CoinGecko e feeds RSS de CoinDesk, Cointelegraph e Decrypt. O sistema permanece em análise/paper trading; `LIVE_TRADING_ENABLED=false` e não há envio de ordens reais.

## 2. Componentes existentes

- FastAPI em `app/main.py`.
- JWT/RBAC em `app/auth.py`, `app/api/login.py` e `app/security/password.py`.
- Binance REST em `app/market/binance_adapter.py`.
- Coleta REST de candles em `app/market/candle_sync.py`.
- Coleta WebSocket de trades e order book em `app/market/ws_collector.py`.
- PostgreSQL async via SQLAlchemy em `app/db/engine.py` e `app/db/models.py`.
- Redis para cache e notificações.
- Feature Engine em `app/ml/features.py`.
- Dataset Builder em `app/ml/dataset.py`.
- Modelos Logistic Regression, Random Forest e XGBoost em `app/ml/models.py`.
- Model Registry em `app/ml/registry.py`.
- Retreinamento em `app/ml/retrain_service.py`.
- Backtester em `app/ml/backtester.py` e `app/api/backtest.py`.
- Providers Ollama e Groq em `app/services/`.
- MCP em `app/mcp_server.py` e no serviço `mcp_market`.
- Notícias RSS e cache em `app/services/market_intelligence.py`.
- Página de notícias e endpoint REST `/api/news`.
- Frontend React/Vite com Dashboard, Strategy Lab, Model Registry, Crypto News, notificações e chat.

## 3. Dependências e infraestrutura

- Python 3.11 no backend.
- FastAPI, Uvicorn, SQLAlchemy async, asyncpg, Redis, httpx, websockets, NumPy, pandas e bibliotecas ML.
- React, TypeScript, Vite e Lucide no frontend.
- PostgreSQL 15, Redis 7 e Ollama em containers.
- Docker Engine 29.6.1 nativo no WSL Ubuntu 24.04.
- Portas publicadas: frontend `4173`, backend `8001`, MCP `9000`, Ollama `11434`.

## 4. Fluxo de dados observado

1. Binance REST fornece candles.
2. Binance WebSocket fornece trades e atualizações de order book.
3. Collectors persistem dados no PostgreSQL.
4. Features são calculadas sobre candles históricos.
5. Modelos carregam artefatos por símbolo/timeframe.
6. O endpoint de sinais retorna BUY, SELL ou WATCH conforme a probabilidade e o confidence gate.
7. O frontend consulta o backend por HTTP e atualiza o dashboard.
8. O chat consulta MCP ou usa pesquisa direta, combinando Binance, CoinGecko e RSS.

## 5. Banco de dados

Tabelas/modelos observados:

- `users`
- `candles`
- `trades`
- `order_book_snapshots`
- estruturas de order book/update existentes conforme migrations e modelos

Existe persistência de notícias enriquecidas em `news_items` e posições virtuais em `paper_trades`. Ainda não existe auditoria completa de sinais nem persistência de resultados walk-forward.

Migrations presentes: `migrations/init.sql`, `migrations/012_add_constraints_and_normalize.sql`, `migrations/013_rebuild_trades_dedup_swap.sql`, `migrations/014_market_data_timing_book_ticker.sql`, `migrations/015_paper_trades.sql` e `migrations/016_news_intelligence.sql`. Não há Alembic configurado.

## 6. APIs existentes

- `GET /api/health`
- `POST /api/auth/login`
- `GET /api/signals/latest`
- `GET /api/ml/features/{symbol}`
- `GET /api/ml/candles/{symbol}`
- `POST /api/ml/dataset/create`
- `POST /api/ml/models/train`
- `GET /api/ml/models/registry`
- `POST /api/ml/models/registry/{version}/approve`
- `POST /api/ml/models/predict`
- `GET /api/ml/models/info`
- `POST /api/ml/backtest/run`
- `GET /api/ml/backtest/strategies`
- `POST /api/ml/backtest/run-strategy`
- `POST /api/ml/backtest/run-walk-forward`
- `GET /api/ml/backtest/info`
- `GET /api/market/price`
- `GET /api/market/prices`
- `GET /api/market/orderbook`
- `POST /api/chat/message`
- `GET /api/notifications`
- `DELETE /api/notifications/{id}`
- `GET /api/news`
- `GET /api/opportunities`
- `GET /api/paper/positions`
- `POST /api/paper/positions`
- `POST /api/paper/positions/{trade_id}/close`
- `GET /api/paper/history?page=1&page_size=20`

Os endpoints protegidos usam Bearer JWT. Health e login são públicos.

## 7. ML

O pipeline atual usa features técnicas, divisão temporal e modelos Logistic Regression, Random Forest e XGBoost. O dashboard usa Logistic Regression por padrão. O registry mantém candidatos/ativos e o retrainer roda periodicamente.

Existe proteção contra alguns vazamentos por divisão temporal e validação temporal. Ainda não existe Dataset V2 orientado a LONG/SHORT/NO_TRADE nem calibração completa com Brier/reliability como contrato de produção.

## 8. Backtester

O backtester existente é causal: decisão no fechamento do candle e execução na abertura do candle seguinte. Possui taxas, slippage, turnover, retorno, buy-and-hold, Sharpe, drawdown, win rate e equity curve.

Não existe ainda Backtest Engine 2.0 com stop, take profit, time exit, long/short/no-trade completo ou resultados segmentados por regime.

## 9. Ollama e camada de linguagem

Ollama e Groq são providers configuráveis. O chat usa tool calling MCP e streaming. As instruções exigem português do Brasil, notícias traduzidas/humanizadas e respostas com parágrafos.

O provider ainda retorna texto de chat; não existe o contrato estruturado de validação do sinal descrito no alvo, nem validação Pydantic de `APPROVE`, `REJECT` e `FLAG_CONFLICT`.

## 10. MCP

O serviço `mcp_market` expõe ferramentas para:

- overview via CoinGecko;
- análise multi-timeframe via Binance;
- notícias via RSS;
- pesquisa combinada de ativos.

O MCP usa Redis e não depende de PostgreSQL para operar.

## 11. Notícias

Fontes atuais: CoinDesk, Cointelegraph e Decrypt RSS.

Existem:

- `MarketIntelligenceService.get_news()`;
- deduplicação por título;
- cache Redis de 300 segundos;
- filtro por ativo no contexto do chat;
- notícias gerais em `GET /api/news`;
- página `/news` com destaque, filtro por fonte, data e link original.

Não existem ainda News Intelligence Engine completo, persistência de notícias, extração de ativos formal, sentimento, impacto, tipo de evento ou confiança estruturados.

## 12. Frontend

Tecnologia: React + TypeScript + Vite.

Rotas atuais:

- `/dashboard`
- `/strategy`
- `/models`
- `/news`

Também existem login, autenticação persistida em `localStorage`, chat, notificações e dashboard com preço, candles, indicadores, order book e sinal.

A seleção do Market Desk possui 20 pares USDT configurados. O frontend consome valores calculados pelo backend e não calcula score, risco ou probabilidade.

## 13. Testes e validações executadas

- `python -m pytest tests -q`: 5 testes passaram.
- `npm run build` no diretório `frontend`: compilação TypeScript/Vite passou.
- Docker Compose: serviços backend, frontend, PostgreSQL, Redis, collectors, retrainer, Ollama e MCP observados em execução.
- Health backend: `GET http://localhost:8001/api/health` respondeu `200` quando o Engine estava estável.
- Frontend: `http://localhost:4173` respondeu `200`.
- Dashboard e página `/news` foram validados no navegador.
- Coleta Binance foi validada com respostas `200` e candles persistidos para novos pares.

## 14. Problemas encontrados

1. Documentação estava divergente das portas e do runtime atual; README, arquitetura e processos foram atualizados.
2. O proxy Vite usava hostname Docker quando executado fora do Compose; foi parametrizado.
3. Dois Docker Engines no WSL foram identificados: serviço Docker do sistema e serviço Snap. A desativação do daemon duplicado foi proposta, mas não executada nesta auditoria porque a operação foi cancelada.
4. Reinícios do WSL/daemons provocaram quedas conjuntas dos containers; há evidência de `systemd` demorando no boot, não de OOM.
5. Ao expandir para 20 ativos, os collectors inicialmente falharam por ausência do import `os`; corrigido e validado.
6. Alguns novos símbolos podem não ter dados imediatos até o primeiro ciclo de sincronização ou snapshot WebSocket.
7. O documento arquitetural inicial e memórias históricas ainda contêm afirmações antigas; a documentação principal foi atualizada, mas memórias legadas devem ser tratadas como históricas.

## 15. EXPECTED vs ACTUAL em relação ao alvo

| Área | Expected | Actual | Estado |
| --- | --- | --- | --- |
| Data Quality | Engine com VALID/WARNING/INVALID bloqueando dados inválidos | Sem engine dedicado | GAP |
| Market Data | 1d, 4h, 1h, 15m, 5m | Candles nos cinco timeframes; WS trades/order book/bookTicker com timing | IMPLEMENTADA |
| Normalização | Adapter -> Normalizer -> Validator -> Persistence | Normalizadores comuns para candles, trades, order book e bookTicker antes da persistência | IMPLEMENTADA |
| Multi-timeframe | Engine formal com 1d/4h/1h/15m/5m | Engine causal e endpoint `/api/market/multi-timeframe` | IMPLEMENTADA |
| Features | Feature Engine 2.0 com volume, momentum, ADX, VWAP e volatilidade ampliada | `app/quant/feature_v2.py` disponível como núcleo determinístico | IMPLEMENTADA |
| Microstructure | Engine com imbalance, pressão, trades e profundidade | `app/quant/engines.py` consumido pelo Signal Engine | IMPLEMENTADA |
| Regime | TREND_UP/DOWN, SIDEWAYS, volatilidade, TRANSITION | Classificador determinístico consumido por sinais e MTF | IMPLEMENTADA |
| News | Pipeline persistente com assets/sentiment/impact/event/confidence | RSS enriquecido, migration `016`, arquivo histórico e endpoint `/api/news/history` | IMPLEMENTADA |
| Dataset V2 | LONG/SHORT/NO_TRADE por horizonte | Targets V2 e contrato walk-forward disponíveis | IMPLEMENTADA |
| ML V2 | calibração, Brier, profit factor e estabilidade por regime | Trainer registra Brier/ECE e estabilidade por regime; retrainer aplica gates | IMPLEMENTADA |
| Signal Engine | serviço dedicado com score e conflito | Decision engine integrado a `/api/signals/latest` | IMPLEMENTADA |
| Risk Engine | entrada, stop, alvo, R/R e MAE | Stop, alvo e R/R integrados ao sinal | PARCIAL |
| Backtest V2 | stop/target/time exit e regimes | `engine_version=v2` com MAE/MFE, expectancy, profit factor e regimes | IMPLEMENTADA |
| Walk-forward | janelas train/validation/test | Utilitários de janelas disponíveis; Strategy Lab agora aceita período histórico explícito, mas ainda não persiste uma grade walk-forward completa | PARCIAL |
| Paper Trading | posições virtuais, PnL, MFE/MAE e auditoria | Posições persistentes, PnL realizado/não realizado, histórico paginado, WebSocket, fechamento a mercado e saída automática por stop/alvo | PARCIAL |
| Ollama guardrails | saída estruturada validada e sem alterar score | chat textual com regras de prompt | PARCIAL |
| Opportunities | scanner e ranking multiativo | Ranking das 20 moedas configuradas, com LONG/SHORT, entrada, stop, alvo, risco por unidade, R/R e abertura pré-preenchida no Paper | IMPLEMENTADA |
| Frontend | dashboard completo com opportunities, asset detail, risco e paper | Dashboard, Opportunities acionável, Paper com PnL e Strategy Lab multiativo/estratégias/períodos | PARCIAL |
| Observability | métricas de sinais, qualidade, notícias e LLM | logs/health existentes; cobertura alvo incompleta | PARCIAL |
| Segurança | sem ordens reais e secrets protegidos | paper-only preservado; `.env` contém credenciais expostas | RISCO |

## 16. Alterações necessárias e ordem aprovada

Seguir a ordem de `docs/sistema.md`, com checkpoint após cada fase:

0. Auditoria: concluída neste documento.
1. Data Quality Engine.
2. Expansão de market data para 15m e 5m após validação de custo.
3. Normalização.
4. Multi-timeframe.
5. Feature Engine 2.0.
6. Microstructure.
7. Market Regime.
8. News Intelligence.
9. Dataset V2.
10. ML Engine V2 e calibração.
11. Signal Engine.
12. Risk Engine.
13. Backtest V2.
14. Walk-forward.
15. Paper Trading.
16. Ollama estruturado e validado.
17. Opportunity Scanner.
18. Frontend 2.0.
19. Observabilidade.
20. Validação final.

A Fase 1 não deve começar antes da validação deste checkpoint.

## 17. Riscos técnicos

- Concorrência entre dois Docker Engines nativos no WSL pode continuar derrubando a stack.
- Volume montado do projeto permite que alterações locais entrem nos containers sem rebuild; isso exige reinício consciente dos processos.
- Feeds RSS públicos podem falhar, atrasar ou alterar XML.
- Expansão para 20 ativos aumenta volume de trades/order book e custo de armazenamento.
- Modelos ativos podem não existir para todo símbolo/timeframe novo.
- O chat é dependente do provider e não deve ser tratado como camada quantitativa.
- Credenciais presentes no `.env` foram expostas e precisam ser rotacionadas antes de qualquer uso real.
- O sistema não deve habilitar trading real enquanto as fases de qualidade, risco, validação e paper trading não forem concluídas.

## 18. Atualização da Fase 1

A Fase 1 foi implementada após a validação da auditoria:

- Criado `app/quality/data_quality.py` com `VALID`, `WARNING` e `INVALID`.
- Criados testes em `tests/test_data_quality.py`.
- Candles inválidos são rejeitados antes da persistência.
- Candles inválidos históricos são excluídos antes de features e dataset.
- Gaps, duplicidades, ordenação, incompletude e faixas extremas são identificados.
- Nenhuma alteração de banco foi necessária; não há migration nesta fase.

## 20. Atualização da Fase 2

A Fase 2 foi implementada mantendo REST e WebSocket:

- O collector de candles passou a sincronizar `1d`, `4h`, `1h`, `15m` e `5m` por padrão.
- `MARKET_TIMEFRAMES` permite configurar os intervalos explicitamente; `1m` continua desabilitado por padrão.
- O WebSocket passou a assinar `bookTicker` além de trades e order book.
- Trades, snapshots e atualizações de order book passaram a registrar `received_time` junto de `event_time`.
- A tabela `book_tickers` foi adicionada na migration `014_market_data_timing_book_ticker.sql`.

## 21. Decisão do checkpoint

**PHASE CHECKPOINT**

- Phase: 2 — MARKET DATA
- Status: IMPLEMENTADA; validação automatizada concluída
- Files created: `migrations/014_market_data_timing_book_ticker.sql`
- Files modified: `app/market/candle_sync.py`, `app/market/ws_collector.py`, `app/db/models.py`, `migrations/init.sql`, `docker-compose.yml`
- Database changes: migration aditiva para timing e `book_tickers`
- Known issues: a migration precisa ser aplicada no banco existente; Compose deve ser validado pelo Docker Engine no WSL
- Next phase: Fase 3 — NORMALIZAÇÃO

## 22. Atualização da Fase 3

A Fase 3 foi implementada sem remover os collectors REST ou WebSocket:

- Criados contratos imutáveis para candle, trade, order book e `bookTicker`.
- Criado `app/market/normalizer.py` para converter payloads Binance em estruturas comuns.
- Símbolos são normalizados para maiúsculas e trades recebem lado `buy`/`sell` a partir de `buyer maker`.
- REST e WebSocket usam o mesmo formato normalizado antes da criação dos modelos de persistência.
- O adapter Binance passou a expor `get_book_ticker()`.
- Testes em `tests/test_market_normalizer.py` cobrem payloads válidos e incompletos.

## 23. Decisão do checkpoint

**PHASE CHECKPOINT**

- Phase: 3 — NORMALIZAÇÃO
- Status: IMPLEMENTADA E VALIDADA
- Files created: `app/market/normalizer.py`, `tests/test_market_normalizer.py`
- Files modified: `app/market/contracts.py`, `app/market/binance_adapter.py`, `app/market/candle_sync.py`, `app/market/ws_collector.py`, `README.md`, `docs/ARCHITECTURE.md`
- Database changes: nenhuma
- Tests: 14 testes passaram em `tests/` após o restart
- Next phase: Fase 4 — MULTI-TIMEFRAME

## 24. Implementação incremental das fases quantitativas

Foram adicionados módulos puros em `app/quant/` para:

- Feature Engine 2.0: retornos, range, corpo, pavios, volatilidade, volume relativo e VWAP.
- Microstructure: spread, spread em bps, imbalance e pressão do book.
- Market Regime: `TREND_UP`, `TREND_DOWN`, `SIDEWAYS`, `VOLATILE` e `UNKNOWN`.
- Signal/Risk: score, estados `SETUP`, `HIGH_CONVICTION`, `NO_TRADE`, stop, alvo e R/R.
- Dataset V2: alvos `LONG`, `SHORT`, `NO_TRADE`, Brier score e janelas walk-forward.
- Paper Trading: posições virtuais, marcação, PnL e taxas, sem chamada de exchange.
- Opportunity ranking: ordenação de oportunidades quantitativas válidas.

O endpoint de sinal existente delega regime e risco ao núcleo quantitativo, preservando o contrato legado. O endpoint autenticado `/api/market/multi-timeframe` expõe as leituras dos cinco intervalos.

Ainda permanecem como trabalho de integração: auditoria completa de paper trading. O primeiro slice do Frontend 2.0 foi integrado em `/opportunities`.

O retrainer passou a usar por padrão `1d,4h,1h,15m,5m`; candidatos que não atingem AUC mínimo ou pioram calibração permanecem pendentes. As métricas Prometheus agora cobrem sinais, qualidade, notícias, validações LLM e operações paper.

## 25. Frontend 2.0 incremental

- Criada a tela `/opportunities` com ranking real do endpoint `/api/opportunities`.
- A tela exibe alinhamento `1d/4h/1h/15m/5m`, regime, direção, estado, score, probabilidade e R/R.
- O Strategy Lab passou a executar o Backtest V2 com stop ATR, alvo e limite de barras.
- A navegação lateral foi atualizada e o build TypeScript/Vite foi validado.
- A tela `/paper` recebeu gráfico, 20 ativos, PnL não realizado em tempo real e fechamento a mercado.
- O `ws_collector` encerra posições paper automaticamente quando um tick atinge stop ou alvo; sem conexão de mercado, a posição permanece aberta até a reconexão ou fechamento manual.
- O monitor de oportunidades avalia as 20 moedas a cada 60 segundos e publica alertas Redis por usuário para novas oportunidades, aproximação/atingimento de stop loss e aproximação/atingimento de take profit; cooldown de 15 minutos evita spam.
- Alertas de stop/alvo foram restringidos a símbolos com posição paper `OPEN`; usuários sem operação aberta recebem somente novas oportunidades. A central ganhou limpeza global via `DELETE /api/notifications`.
- A tela `/opportunities` passou a exibir plano operacional LONG/SHORT com entrada, stop loss, take profit, risco por unidade, R/R e ação `Abrir no Paper`.
- O ranking de oportunidades passou a descontar taxa e slippage de ida e volta, exibir custo total, retorno bruto/líquido no alvo e perda líquida no stop; setups cujo alvo não cobre os custos são excluídos.
- O ranking passou a exigir edge direcional acima do break-even, valor esperado positivo acima da margem de segurança e movimento mínimo seguro; a tela exibe probabilidade direcional, break-even, valor esperado, margem e retorno líquido.
- O Paper Trading passou a expor histórico paginado com PnL realizado, vitórias e perdas; o Strategy Lab permite variar taxa, slippage, confiança, stop ATR, alvo R/R e máximo de barras para comparar cenários no holdout temporal.
- O Strategy Lab passou a aceitar médias móveis, RSI e breakout, uma ou várias das 20 moedas, múltiplos timeframes e período de datas; cada resultado usa execução causal com stop, alvo, time exit, taxas e slippage.
- Criado Strategy Engine determinístico com médias móveis, reversão pelo RSI e breakout; `/api/ml/backtest/run-strategy` aceita múltiplas moedas, múltiplos timeframes, parâmetros customizados e período histórico, com execução causal, custos, stop ATR, alvo R/R e time exit.

## 19. Decisão do checkpoint

**PHASE CHECKPOINT**

- Phase: 1 — DATA QUALITY
- Status: IMPLEMENTADA E VALIDADA
- Files created: `app/quality/__init__.py`, `app/quality/data_quality.py`, `tests/test_data_quality.py`, `docs/DATA_QUALITY.md`
- Files modified: `app/market/candle_sync.py`, `app/ml/features.py`, `app/ml/dataset.py`, `README.md`, `docs/CURRENT_SYSTEM_AUDIT.md`
- Database changes: nenhuma
- Tests: quality tests passed; suíte completa registrada na validação final
- Docker: serviços observados em execução; estabilidade do daemon WSL continua como risco externo
- API: health, frontend e endpoints principais já validados anteriormente
- Known issues: Signal, Risk, Walk-forward e Paper Trading ainda não implementados; persistência de status de qualidade fica para fase posterior; dois daemons Docker no WSL precisam de saneamento
- Next phase: Fase 2 — MARKET DATA, após validação deste checkpoint
