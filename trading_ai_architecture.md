# Trading AI — Arquitetura de Referência (Resumo)

Versão: 1.0
Escopo: PoC/primeira versão _crypto_ usando Binance, PostgreSQL, Redis, Ollama local, XGBoost/LightGBM, FastAPI e React.

## Princípios-chave
- LLM (Ollama) é validador contextual; não executa ordens nem gera preços.
- Separação clara: Market Data → Normalização → Features → ML → Signals → LLM Validator → Risk → Execution.
- Nunca sobrescrever dados brutos; persistir RAW → NORMALIZED → FEATURES → PREDICTION → SIGNAL → TRADE.
- Temperature do LLM: `0` para produção de validações.
- Structured output obrigatório do LLM (JSON/JSON Schema) e validação com Pydantic.

## Defaults/configuração
- Market: Crypto (BTCUSDT, ETHUSDT, SOLUSDT)
- Timeframes: 1m, 5m, 15m, 1h
- BrokerAdapter inicial: Binance (adapter abstrato)
- DB: PostgreSQL (schemas: market_data, features, ml, trading, system)
- Cache: Redis (latest price, latest signal, locks)
- ML: XGBoost / LightGBM (primeira versão)
- LLM: Ollama local `http://localhost:11434/api` (via adapter)
- Backend: Python + FastAPI
- Frontend: React + TypeScript
- Orquestração: Docker Compose
- Ambientes: PAPER (default), TESTNET, LIVE (habilitar com `LIVE_TRADING_ENABLED=true` + validação)

## Containers básicos Docker Compose
- postgres
- redis
- market-data (collector + sync tasks)
- feature-engine
- ml-engine
- signal-engine
- ollama
- backend (FastAPI)
- frontend (React)

## Contratos principais (resumo)
- MarketDataProvider: `get_candles()`, `get_trades()`, `get_order_book()`, `subscribe_trades()`, `subscribe_order_book()`
- MLModel: `train()`, `predict()`, `evaluate()`, `save()`, `load()`
- LLMProvider: `validate_signal()` → retorna `decision`, `confidence`, `risk_level`, `reason_codes`
- BrokerAdapter: `get_account()`, `get_balance()`, `get_position()`, `create_order()`, `cancel_order()`, `get_order()`
- ExecutionEngine: `execute()`, `cancel()`, `reconcile()`

## Regras operacionais importantes
- Evitar data leakage: features no tempo T só usam dados ≤ T.
- LLM não pode inventar dados; qualquer discrepância → `INCONCLUSIVE`/REJECT.
- Validar e versionar: modelos, prompts, features, targets.
- Idempotência: usar `signal_id` / `client_order_id` / `idempotency_key`.
- Kill switch global: desabilita execução em falhas críticas.

## Métricas e observabilidade
- Logs estruturados com `correlation_id` e `signal_id`.
- Métricas: market_data_latency, websocket_reconnections, ml_latency, ollama_latency, signals_generated, trades_executed, PnL, drawdown.
- Auditoria: armazenar LLM input/output, model_version, feature_version, market snapshot.

## Critérios mínimos antes de LIVE (checklist resumido)
- Collector estável e histórico suficiente
- Sem data leakage
- Backtest reproduzível + walk-forward
- Paper trading e Testnet realizados
- Risk Engine e Kill switch testados
- Idempotência e reconciliação validados
- Secrets e API keys protegidos

## Próximos passos (rápido)
1. Criar repositório e estrutura de pastas.
2. Implementar contracts/interfaces e configuração Docker Compose.
3. Implementar MarketData Adapter (Binance REST + WebSocket) e persistência RAW.
4. Feature Engine determinístico e testes anti-leakage.
5. Dataset builder + backtest básico.
6. Primeiro modelo XGBoost + prediction API.
7. Signal Engine + ranking + OllamaProvider (schema + validação).
8. Risk Engine + Paper Trading.

## Observações para reutilização
- Este arquivo é fonte única resumida para decisões arquiteturais iniciais.
- Atualize com: `model_registry`, `prompt_version`, `feature_version` e mudanças aprovadas (Architecture Change Request).
- Localização em memória: /memories/repo/trading_ai_architecture.md (persistente no workspace).

---

Tags: architecture, trading, binance, ollama, ml, docker, postgres, redis
