- News Intelligence determinístico enriquece RSS com ativos, evento, sentimento, impacto e confiança; qualquer provider configurado pode validar contexto em `/api/signals/validate-context`.
- `GET /api/news/history` consulta o arquivo persistente de notícias enriquecidas, separado da atualização RSS atual.
- Backtest V2 opcional (`engine_version=v2`) simula long/short com stop ATR, take profit, time exit, MAE/MFE, expectancy, profit factor e resultados por regime.
- O treinamento registra `test_brier` e `test_ece`; o retrainer considera calibração junto com AUC antes de promover um modelo.
- O retrainer também registra estabilidade por regime no candidato e exige `RETRAIN_MIN_REGIME_ACCURACY` quando há pelo menos cinco amostras de um regime.
# Trade AI

Sistema de coleta de mercado, análise técnica e sinais de machine learning, executado integralmente em Docker.

## Estado atual

- Backend FastAPI com autenticação JWT e roles `admin` e `user`.
- PostgreSQL para candles, trades, order book e usuários.
- Redis disponível na rede interna do Compose.
- MCP de inteligência de mercado em serviço separado (`trading_mcp_market`).
- Collector Binance em REST para candles reais.
- Candles dos 20 pares USDT configurados no Market Desk, nos timeframes `1d`, `4h`, `1h`, `15m` e `5m`.
- Dashboard web com indicadores, sinais e gráfico OHLC atualizado automaticamente.
- Feature Engine com SMA, EMA, RSI, MACD, Bollinger Bands e ATR.
- Data Quality Engine que rejeita candles inválidos antes da persistência e do uso em ML.
- Dataset Builder com divisão temporal para treino e teste.
- Modelos Logistic Regression, Random Forest e XGBoost.
- Retreinamento automático em serviço Docker separado, com versões candidatas e aprovação por métrica.
- Modo atual: análise e paper trading. Nenhuma ordem real é enviada.
- Página de notícias cripto em `/news`, com destaque, filtros por fonte e atualização manual.
- O chat usa tool calling MCP e resposta em streaming.
- O provider de IA é configurável entre Ollama local e Groq por `AI_PROVIDER`.
- O sistema possui central global de notificações, com eventos de resposta do chat e suporte futuro a mudanças de tendência.
- Núcleo quantitativo incremental com Feature Engine 2.0, regime, risco, ranking de oportunidades, Dataset V2, walk-forward, paper trading virtual, enriquecimento determinístico de notícias e contrato estruturado de validação LLM.

## Execução

Pré-requisitos: WSL2 com Ubuntu, systemd habilitado e Docker Engine nativo instalado na distribuição.

Subir todos os serviços:

```bash
docker compose up -d --build
```

Verificar o estado:

```bash
docker compose ps
```

Verificar saúde da API:

```bash
curl http://localhost:8001/api/health
```

Parar os serviços:

```bash
docker compose down
```

Backend, collector e Redis usam `restart: unless-stopped`. O backend roda sem `--reload` para evitar reinicializações causadas pelo volume de desenvolvimento.

## URLs

- Frontend React: http://localhost:4173
- Dashboard React: http://localhost:4173/dashboard
- Notícias cripto: http://localhost:4173/news
- Strategy Lab: http://localhost:4173/strategy
- Model Registry: http://localhost:4173/models
- API: http://localhost:8001
- Ollama: http://localhost:11434
- MCP: http://localhost:9000/mcp

Provider de IA:

```env
AI_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:latest
# Para usar Groq, configure também GROQ_API_KEY e troque para:
# AI_PROVIDER=groq
# GROQ_MODEL=llama-3.3-70b-versatile
# GROQ_BASE_URL=https://api.groq.com
# GROQ_TEMPERATURE=1
# GROQ_MAX_COMPLETION_TOKENS=2048
# GROQ_TOP_P=1
# GROQ_REASONING_EFFORT=medium
```

O chat, tool calling MCP e streaming usam o mesmo contrato para os dois providers. Groq é opcional; sem chave, Ollama continua sendo usado.

Após autenticar, o frontend React permite selecionar símbolo e timeframe. O gráfico mostra candles reais persistidos pelo collector e é atualizado a cada 60 segundos.

## Principais endpoints

Todos os endpoints abaixo, exceto health e login, exigem `Authorization: Bearer <JWT>`.

| Método | Endpoint | Função |
| --- | --- | --- |
| GET | `/api/health` | Health check |
| POST | `/api/auth/login` | Login e emissão de JWT |
| GET | `/api/signals/latest?symbol=BTCUSDT&timeframe=1h` | Sinal mais recente |
| GET | `/api/ml/features/{symbol}?timeframe=1h` | Indicadores técnicos |
| GET | `/api/ml/candles/{symbol}?timeframe=1h&limit=120` | Histórico OHLCV para o gráfico |
| POST | `/api/ml/dataset/create` | Criar dataset temporal |
| POST | `/api/ml/models/train` | Treinar um modelo |
| POST | `/api/ml/models/predict` | Fazer previsão com modelo salvo |
| GET | `/api/ml/models/info` | Informações dos modelos |
| GET | `/api/ml/models/registry` | Listar versões candidatas e ativas |
| POST | `/api/ml/models/registry/{version}/approve` | Aprovar versão, somente admin |
| POST | `/api/ml/backtest/run` | Executar backtest paper com custos e risco |
| POST | `/api/chat/message` | Pesquisa de mercado e resposta NDJSON em streaming |
| GET | `/api/notifications` | Listar notificações do usuário autenticado |
| DELETE | `/api/notifications/{id}` | Remover uma notificação do usuário |
| GET | `/api/news?limit=24` | Listar notícias gerais das fontes RSS |
| GET | `/api/market/multi-timeframe?symbol=BTCUSDT` | Resumo de 1d, 4h, 1h, 15m e 5m com regime |
| GET | `/api/opportunities?symbols=BTCUSDT,ETHUSDT,SOLUSDT&timeframe=1h` | Ranking de oportunidades com modelo disponível |
| GET | `/api/ml/walk-forward/windows?length=500&train_size=300&validation_size=100&test_size=50` | Janelas temporais para validação walk-forward |
| GET | `/api/paper/positions` | Posições paper abertas |
| POST | `/api/paper/positions` | Abrir posição exclusivamente virtual |
| POST | `/api/paper/positions/{trade_id}/close` | Encerrar posição virtual |

## MCP de inteligência de mercado

O serviço `trading_mcp_market` expõe Streamable HTTP em `http://localhost:9000/mcp` e fornece:

- `get_market_overview`: CoinGecko para preço, market cap, volume e variação.
- `get_multi_timeframe_analysis`: Binance para preço, order book, spread e `15m`, `1h`, `4h`, `1d`.
- `get_market_news`: RSS filtrado por ativo de CoinDesk, Cointelegraph e Decrypt.
- `research_assets`: pesquisa combinada por linguagem natural.

O chat anuncia as ferramentas ao Ollama, chama o MCP quando necessário e mantém fallback para pesquisa direta. O MCP não precisa de PostgreSQL nem de uma segunda instância do Ollama; compartilha apenas o Redis para cache.

Teste rápido:

```bash
curl -X POST http://localhost:9000/mcp -H 'Accept: application/json, text/event-stream' -H 'Content-Type: application/json' -H 'MCP-Protocol-Version: 2025-06-18' -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Coleta de dados

O serviço `trading_market_collector` executa `app.market.candle_sync` e consulta a API pública da Binance a cada 60 segundos. A persistência é idempotente por `symbol`, `timeframe` e `open_time`. A lista padrão possui 20 pares USDT e pode ser alterada por `MARKET_SYMBOLS`.

O chat usa Binance para dados intraday, CoinGecko para visão ampla e feeds RSS públicos para notícias. CoinGecko fica em cache por 60 segundos; notícias ficam em cache por 300 segundos. Cada notícia mantém fonte, data e URL.

## Notificações

O backend grava notificações no Redis por usuário, mantendo no máximo 50 itens recentes. A conclusão de uma resposta do chat cria um evento `chat_response`. O frontend consulta `/api/notifications` a cada 5 segundos e mostra um toast, contador no sino e histórico recolhível. O tipo `trend_change` já está previsto para um futuro monitor de tendência; ele não é emitido até haver uma regra confirmada para evitar falsos alertas.

Símbolos padrão atuais: `BTCUSDT`, `ETHUSDT`, `BNBUSDT`, `XRPUSDT`, `SOLUSDT`, `ADAUSDT`, `DOGEUSDT`, `TRXUSDT`, `AVAXUSDT`, `LINKUSDT`, `TONUSDT`, `SHIBUSDT`, `DOTUSDT`, `BCHUSDT`, `LTCUSDT`, `UNIUSDT`, `XLMUSDT`, `NEARUSDT`, `ATOMUSDT`, `APTUSDT`.

Timeframes atuais: `1d`, `4h`, `1h`, `15m` e `5m`. O collector aceita `MARKET_TIMEFRAMES` para configuração explícita; `1m` não é habilitado por padrão.

Trades, atualizações de order book e `bookTicker` WebSocket registram `event_time` e `received_time`. A camada de normalização em `app/market/normalizer.py` padroniza símbolos, timestamps, preços, quantidades e lado antes da persistência. Para atualizar um banco existente, aplique `migrations/014_market_data_timing_book_ticker.sql` antes de reiniciar o collector.

Ver logs do collector:

```bash
docker logs --since 5m trading_market_collector
```

Consultar candles no PostgreSQL:

```bash
docker exec trading_postgres psql -U trader -d trading -c "SELECT symbol, timeframe, count(*) FROM candles GROUP BY symbol, timeframe ORDER BY symbol, timeframe;"
```

## Machine learning

O pipeline atual é:

1. Candles reais são persistidos no PostgreSQL.
2. Features técnicas são convertidas para valores relativos ao preço.
3. O dataset usa divisão temporal, sem embaralhar o futuro para o treino.
4. O modelo é avaliado no holdout temporal.
5. O artefato é salvo em `/app/models/`.
6. O endpoint de sinais carrega o modelo compatível com símbolo e timeframe.

O modelo padrão do dashboard é Logistic Regression. Random Forest e XGBoost continuam disponíveis para comparação via API.

Um sinal com confiança entre 40% e 60% é exibido como `WATCH`, evitando tratar incerteza como compra ou venda.

O serviço `trading_model_retrainer` executa o retreinamento a cada 6 horas. Cada treino cria uma versão imutável em `/app/models/versions/` e registra métricas no `registry.json`.

O worker promove automaticamente a primeira versão que atingir `RETRAIN_MIN_TEST_AUC` e versões posteriores somente quando superarem a métrica do modelo ativo. Candidatos que não passam no gate permanecem pendentes para aprovação administrativa.

O endpoint manual `/api/ml/models/train` cria candidato por padrão. Para promover diretamente um treino manual, envie `"approve": true` no corpo da requisição; essa opção deve ser restrita a uso administrativo.

## Backtester

O endpoint `POST /api/ml/backtest/run` executa uma simulação causal usando o modelo ativo apenas no holdout temporal não usado no ajuste do modelo. A decisão é tomada no fechamento do candle atual e executada na abertura do próximo candle.

Parâmetros principais:

- `initial_cash`: capital inicial.
- `fee_bps`: taxa por mudança de posição em basis points.
- `slippage_bps`: slippage por mudança de posição em basis points.
- `confidence_threshold`: confiança mínima para BUY ou SELL; entre os limites, o sinal fica `WATCH`.

O resultado inclui retorno líquido, buy-and-hold, excesso de retorno, Sharpe anualizado, drawdown máximo, win rate, quantidade de trades, taxas, slippage, equity curve e o modo de avaliação (`temporal_holdout`). O backtester não envia ordens para a Binance.

## Segurança

- Não versionar `.env` nem credenciais.
- Usar JWT Bearer para endpoints protegidos.
- Manter `TRADING_MODE=PAPER` e `LIVE_TRADING_ENABLED=false` durante desenvolvimento.
- Trocar credenciais que tenham sido expostas.
- Se a senha administrativa do `.env` for alterada, execute `docker compose exec backend python scripts/sync_admin_password.py` para atualizar o hash do usuário existente.

## Estrutura relevante

- `app/main.py` — aplicação FastAPI e roteamento.
- `app/auth.py` — validação JWT e autorização por role.
- `app/market/candle_sync.py` — sincronização de candles Binance.
- `app/db/models.py` — modelos PostgreSQL.
- `app/ml/features.py` — indicadores e features normalizadas.
- `app/quality/data_quality.py` — estados `VALID`, `WARNING` e `INVALID` para qualidade de candles.
- `app/ml/dataset.py` — dataset e divisão temporal.
- `app/ml/models.py` — treinamento, avaliação, previsão e persistência.
- `app/ml/registry.py` — registry, versionamento e aprovação de modelos.
- `app/ml/retrain_service.py` — retreinamento automático e gate de promoção.
- `app/api/signals.py` — geração do sinal atual.
- `frontend/src/` — aplicação React/Vite principal.
- `frontend/src/screens/DashboardScreen.tsx` — tela principal do dashboard.
- `frontend/src/screens/StrategyScreen.tsx` — backtest com métricas de risco.
- `frontend/src/screens/ModelsScreen.tsx` — versões e status do registry.
- `frontend/src/components/` — telas e componentes visuais reutilizáveis.
- `frontend/src/hooks/` — autenticação e carregamento/polling de mercado.
- `frontend/src/lib/` — formatadores e utilitários puros.
- `frontend/src/api.ts` — contrato de acesso à API.
- `frontend/Dockerfile` — imagem do frontend.
- `docker-compose.yml` — infraestrutura completa.
- `docs/ARCHITECTURE.md` — arquitetura detalhada.
- `docs/DATA_QUALITY.md` — regras e integração da Fase 1.

## Limitações atuais

- Não há execução de ordens reais.
- Não há backtester completo.
- O retreinamento automático usa um gate conservador e não substitui modelos ativos com candidatos piores.
- O dashboard é polling HTTP, não WebSocket.
- O frontend React roda no serviço `trading_frontend` na porta publicada `4173`.
- Notícias dependem da disponibilidade dos feeds RSS públicos; a página `/news` solicita notícias gerais e pode retornar zero itens temporariamente.
- Binance é a referência intraday; CoinGecko e RSS são fontes complementares.
- Scrollbar, skeletons, toasts, modais de confirmação e estados vazios são componentes compartilhados.
- As métricas ainda precisam ser acompanhadas em uma janela maior de dados reais.
