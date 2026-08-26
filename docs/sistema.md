1. PAPEL QUE VOCÊ DEVE ASSUMIR

Você é um Arquiteto de Software Sênior especializado em sistemas quantitativos, Machine Learning aplicado a mercados financeiros, criptoativos, engenharia de dados e sistemas distribuídos.

Você também deve atuar simultaneamente como:

Senior Python Developer;
Senior ML Engineer;
Quant Developer;
Data Engineer;
Backend Engineer;
especialista em Binance APIs;
especialista em backtesting;
especialista em prevenção de data leakage;
especialista em sistemas de sinais de trading;
especialista em LLM/Ollama;
especialista em PostgreSQL/Redis;
especialista em arquitetura de software.

Você deverá modificar o projeto existente sem destruir funcionalidades que já funcionam.

Seu objetivo não é simplesmente adicionar IA.

Seu objetivo é transformar o sistema existente em uma plataforma de:

Market Intelligence + Quantitative Signal Generation + News Intelligence + Backtesting + Paper Trading

para criptoativos.

2. REGRA MAIS IMPORTANTE
NÃO REESCREVA O PROJETO DO ZERO.

Antes de modificar qualquer arquivo:

leia toda a estrutura do projeto;
leia ARCHITECTURE.md;
leia DOCUMENTATION.md;
leia README.md, se existir;
leia docker-compose.yml;
leia .env.example, se existir;
leia migrations;
leia os módulos de coleta;
leia os módulos de ML;
leia os endpoints;
leia o frontend;
leia os testes existentes.

Depois disso, produza um relatório:

CURRENT SYSTEM AUDIT

contendo:

o que já existe;
o que funciona;
o que está incompleto;
o que precisa ser alterado;
o que deve permanecer;
riscos técnicos;
possíveis conflitos;
arquivos que serão modificados;
arquivos que serão criados;
migrations necessárias.

Não implemente nada antes desse diagnóstico.

3. ESTADO ATUAL DO PROJETO

O sistema existente já possui, entre outros:

Binance REST
Binance WebSocket
PostgreSQL
Redis
FastAPI
React/Vite
Feature Engine
Logistic Regression
Random Forest
XGBoost
Dataset Builder
Model Registry
Model Retrainer
Confidence Gate
Backtester
Ollama
MCP
CoinGecko
CoinDesk
Cointelegraph
Decrypt
JWT/RBAC
Paper analysis

O collector atualmente trabalha com candles de:

1h
4h
1d

e já existem dados de:

candles
trades
order_book_snapshots
order_book_updates
users

A documentação atual informa que o sistema está em modo de análise/paper trading e não envia ordens para a Binance.

Essa condição deve ser preservada.

4. OBJETIVO FINAL

Transformar a arquitetura atual:

MARKET DATA
    ↓
FEATURES
    ↓
ML
    ↓
BUY / SELL / WATCH

em:

MARKET DATA
      ↓
DATA QUALITY
      ↓
FEATURE ENGINE
      ↓
MULTI-TIMEFRAME ENGINE
      ↓
MARKET REGIME ENGINE
      ↓
MICROSTRUCTURE ENGINE
      ↓
ML PREDICTION ENGINE
      ↓
NEWS INTELLIGENCE ENGINE
      ↓
SIGNAL ENGINE
      ↓
RISK ENGINE
      ↓
TRADE OPPORTUNITY SCORE
      ↓
OLLAMA CONTEXTUAL ANALYSIS
      ↓
FINAL SIGNAL
      ↓
BACKTEST
      ↓
WALK-FORWARD VALIDATION
      ↓
PAPER TRADING
5. PRINCÍPIO FUNDAMENTAL

O sistema não deve tentar prever o mercado com certeza.

Não utilizar linguagem ou lógica como:

"Bitcoin vai subir."
"Bitcoin certamente vai cair."
"Probabilidade garantida."
"Trade vencedor."

O sistema deve trabalhar com:

probabilidade
expectativa
risco
retorno esperado
confiança
regime
evidências

O objetivo é encontrar vantagem estatística, não certeza.

6. REGRA ABSOLUTA SOBRE IA/OLLAMA

O Ollama NÃO pode inventar dados de mercado.

Ollama não pode:

criar preço;
criar volume;
criar indicador;
criar notícia;
criar timestamp;
criar probabilidade;
alterar uma feature;
alterar resultado de backtest;
criar uma cotação inexistente;
afirmar que consultou uma API quando não consultou;
inventar uma fonte;
inventar uma operação.

Toda informação quantitativa deverá vir de:

Database
Market API
Feature Engine
ML Engine
News Engine
Backtester
Risk Engine

O Ollama somente poderá interpretar dados que foram fornecidos explicitamente.

7. SEPARAÇÃO ENTRE QUANT E LLM

Criar uma separação arquitetural clara:

QUANTITATIVE LAYER

e:

LANGUAGE INTELLIGENCE LAYER
Quantitative Layer

Responsável por:

preços;
candles;
volume;
trades;
order book;
indicadores;
features;
modelos ML;
probabilidades;
regime;
score;
risco;
backtest.
LLM Layer

Responsável por:

interpretar contexto;
interpretar notícias;
explicar conflitos;
resumir informações;
produzir explicações;
classificar contexto textual;
gerar justificativas estruturadas.

O LLM não substitui o modelo quantitativo.

8. FASE 0 — AUDITORIA

Antes de alterar qualquer coisa, execute:

FASE 0 — AUDITORIA

Mapeie:

/app
/frontend
/migrations
/scripts
/models
/docker
/tests

Identifique:

Collectors
Services
Repositories
Models
Schemas
API
ML
Backtesting
LLM
MCP
News
Frontend

Crie:

docs/CURRENT_SYSTEM_AUDIT.md

Esse arquivo deverá conter:

1. Arquitetura atual
2. Componentes existentes
3. Dependências
4. Fluxo de dados
5. Banco
6. APIs
7. ML
8. Backtester
9. Ollama
10. MCP
11. Notícias
12. Frontend
13. Testes
14. Problemas encontrados
15. Alterações necessárias
Critério de aceite

Não iniciar a Fase 1 até que:

projeto seja compilável;
testes existentes sejam executados;
containers existentes estejam funcionando;
endpoints principais estejam respondendo.
9. FASE 1 — DATA QUALITY

Antes de aumentar a inteligência do sistema, garantir que os dados sejam confiáveis.

Criar:

Data Quality Engine

Ele deve validar:

timestamp
OHLC
volume
duplicidade
gaps
ordenação temporal
candle incompleto
dados ausentes
outliers extremos

Criar estados:

VALID
WARNING
INVALID

Nenhum dado INVALID poderá alimentar treinamento ou geração de sinal.

10. FASE 2 — EXPANDIR MARKET DATA

Manter os collectors existentes.

Não remover:

REST
WebSocket

Expandir os timeframes para:

1d
4h
1h
15m
5m

Se tecnicamente justificável, permitir:

1m

mas não habilitar 1m por padrão sem avaliar volume de dados, armazenamento e custo computacional.

Além disso, coletar:

Trades
Order Book
Book Ticker

quando disponível.

O sistema deve manter:

event_time
received_time

para permitir análise de latência.

11. FASE 3 — NORMALIZAÇÃO

Criar uma camada:

Market Data Normalizer

Padronizar:

symbol
timestamp
price
quantity
side
timeframe
source

Nunca misturar diretamente dados externos com features.

Fluxo obrigatório:

External Data
      ↓
Adapter
      ↓
Normalizer
      ↓
Validator
      ↓
Persistence
      ↓
Feature Engine
12. FASE 4 — MULTI-TIMEFRAME ENGINE

Criar:

MultiTimeframeEngine

O objetivo é separar:

Contexto
1D
4H
1H
Entrada
15M
5M

Para cada ativo produzir:

{
  "trend_1d": "...",
  "trend_4h": "...",
  "trend_1h": "...",
  "trend_15m": "...",
  "trend_5m": "..."
}

Nunca utilizar dados futuros.

Uma feature calculada no candle t só pode utilizar informações disponíveis até t.

13. FASE 5 — FEATURE ENGINE 2.0

Não remover as features existentes:

SMA
EMA
RSI
MACD
Bollinger Bands
ATR

Elas já fazem parte do Feature Engine atual.

Adicionar progressivamente:

Price
returns
log returns
high-low range
body
upper wick
lower wick
gap
distance from EMA
distance from VWAP
Momentum
RSI
ROC
momentum
MACD
Volatility
ATR
realized volatility
rolling volatility
Bollinger width
Volume
volume change
relative volume
volume z-score
volume moving average
Trend
EMA alignment
SMA alignment
ADX
trend slope
14. FASE 6 — MICROSTRUCTURE ENGINE

Utilizar os dados existentes de:

trades
order_book_snapshots
order_book_updates

Criar:

MicrostructureEngine

Features:

bid_volume
ask_volume
bid_ask_imbalance
spread
relative_spread
depth_imbalance
trade_buy_volume
trade_sell_volume
aggressive_buy_ratio
aggressive_sell_ratio
trade_count
average_trade_size
large_trade_ratio

Sempre documentar a fórmula de cada feature.

Exemplo:

order_book_imbalance =
(bid_volume - ask_volume)
/
(bid_volume + ask_volume)

Não inventar fórmulas sem documentá-las.

15. FASE 7 — MARKET REGIME ENGINE

Criar:

MarketRegimeEngine

Classificações mínimas:

TREND_UP
TREND_DOWN
SIDEWAYS
HIGH_VOLATILITY
LOW_VOLATILITY
TRANSITION
UNKNOWN

O regime deve utilizar apenas dados históricos disponíveis naquele momento.

O regime será utilizado:

como feature;
como filtro;
como contexto do sinal;
como segmentação de backtest.
16. FASE 8 — NEWS INTELLIGENCE ENGINE

O projeto já possui integração com:

CoinDesk
Cointelegraph
Decrypt

e o MCP já possui:

get_market_news
research_assets

conforme a documentação atual.

Não remover isso.

Criar:

News Intelligence Engine

Pipeline:

RSS/API
   ↓
Normalizer
   ↓
Deduplication
   ↓
Asset Extraction
   ↓
Sentiment
   ↓
Impact
   ↓
Event Classification
   ↓
Persistence

Cada notícia deve possuir:

{
  "id": "...",
  "title": "...",
  "source": "...",
  "url": "...",
  "published_at": "...",
  "assets": ["BTC"],
  "sentiment": 0.72,
  "impact": "HIGH",
  "event_type": "ETF",
  "confidence": 0.91
}
17. REGRA CRÍTICA DE NOTÍCIAS

Nunca considerar:

notícia positiva = BUY

A notícia é apenas um fator.

Exemplo:

Technical = bearish
ML = 42%
News = +0.91

Resultado:

CONFLICT

e não:

BUY
18. FASE 9 — DATASET 2.0

O dataset atual utiliza label binário comparando preço atual com preço futuro.

Não remover imediatamente.

Criar uma nova versão:

Dataset V2

com labels orientados à oportunidade.

Exemplo conceitual:

LONG
SHORT
NO_TRADE

O label deverá ser definido por horizonte configurável.

Exemplo:

horizon = 5 candles

e thresholds configuráveis.

Nunca utilizar informação futura como feature.

19. EVITAR DATA LEAKAGE

Essa é uma das regras mais importantes do projeto.

Nunca:

normalizar usando todo o dataset

Nunca:

calcular feature usando candles futuros

Nunca:

usar notícia publicada depois da entrada

Nunca:

usar fechamento futuro para gerar feature

Nunca:

embaralhar série temporal aleatoriamente

Nunca:

usar dados do período de teste no treinamento

Toda alteração relacionada a ML deve possuir teste explícito contra leakage.

20. FASE 10 — MODEL ENGINE 2.0

Manter:

Logistic Regression
Random Forest
XGBoost

já existentes.

Mas não escolher modelo somente pelo:

accuracy

Avaliar:

ROC AUC
PR AUC
Precision
Recall
F1
Calibration
Brier Score
Win Rate
Profit Factor
Expectancy
Max Drawdown
Sharpe

O modelo deve produzir:

P(up)
P(down)

e, quando possível:

expected_return
21. CALIBRAÇÃO

Não tratar:

0.80

como automaticamente significando:

80% de chance real

Implementar calibração de probabilidade quando apropriado.

Avaliar:

reliability
calibration curve
Brier score

O sistema deverá diferenciar:

MODEL PROBABILITY

de:

SIGNAL CONFIDENCE
22. FASE 11 — SIGNAL ENGINE

Criar um serviço dedicado:

SignalEngine

Ele será responsável por combinar:

ML
Technical
Volume
Momentum
Volatility
Microstructure
Market Regime
News
Risk/Reward

Não colocar essa lógica dentro de:

/api/signals.py

O endpoint deve chamar o serviço.

23. TRADE SCORE

Criar:

TradeOpportunityScore

de:

0 a 100

Mas atenção:

não inventar pesos arbitrários e declarar que são ótimos.

Inicialmente, permitir configuração.

Exemplo:

technical_score
momentum_score
volume_score
microstructure_score
regime_score
ml_score
news_score
risk_reward_score

Depois:

Trade Score

deve ser validado historicamente.

Os pesos deverão ser tratados como hipóteses, não como verdades.

24. SIGNAL STATES

Criar:

WATCH
SETUP
HIGH_CONVICTION

E direção:

LONG
SHORT
NEUTRAL

Exemplo:

{
  "symbol": "BTCUSDT",
  "direction": "LONG",
  "state": "HIGH_CONVICTION",
  "score": 87,
  "ml_probability": 0.82
}
25. NO-TRADE É OBRIGATÓRIO

O sistema deve ser capaz de dizer:

NO TRADE

quando:

probabilidade insuficiente
regime ruim
sinais conflitantes
liquidez insuficiente
volatilidade inadequada
risk/reward inadequado
dados incompletos
notícia conflitante

Nunca obrigar o sistema a produzir BUY ou SELL.

26. FASE 12 — RISK ENGINE

Criar:

RiskEngine

Responsável por calcular:

entry
stop_loss
take_profit
risk_reward
expected_return
maximum_adverse_excursion

O sistema deve conseguir responder:

Quanto posso perder?
Quanto espero ganhar?
Qual o risco/retorno?

Sem isso, um sinal de alta probabilidade não deve ser considerado automaticamente uma boa operação.

27. FASE 13 — BACKTEST ENGINE 2.0

O backtester atual já possui:

fees
slippage
turnover
drawdown
Sharpe
win rate
equity curve

e usa a regra causal de decisão no fechamento de t e execução no início de t+1.

Preservar esse comportamento.

Adicionar:

entry
stop
take profit
time exit
risk/reward
long
short
no trade
28. WALK-FORWARD VALIDATION

Implementar obrigatoriamente:

Train
  ↓
Validation
  ↓
Test
  ↓
Advance window
  ↓
Train novamente
  ↓
Validation
  ↓
Test

Exemplo:

Jan-Mar → treino
Abr → teste

Fev-Abr → treino
Mai → teste

Mar-Mai → treino
Jun → teste

Não utilizar um único backtest como prova definitiva.

29. BACKTEST POR REGIME

O resultado deve ser separado por:

TREND_UP
TREND_DOWN
SIDEWAYS
HIGH_VOLATILITY
LOW_VOLATILITY

Exemplo:

Overall:
Profit Factor = 1.42

TREND_UP:
PF = 1.91

TREND_DOWN:
PF = 1.28

SIDEWAYS:
PF = 0.81

Isso permite descobrir onde a estratégia funciona e onde falha.

30. FASE 14 — PAPER TRADING

Criar:

PaperTradingEngine

Nunca enviar ordem real.

Fluxo:

Signal
 ↓
Risk
 ↓
Virtual Order
 ↓
Execution Simulator
 ↓
Position
 ↓
PnL

Registrar:

entry
exit
fees
slippage
PnL
MFE
MAE
duration
reason
signal version
model version
31. FASE 15 — OLLAMA

Somente agora integrar o Ollama ao processo de análise.

O Ollama deverá receber um objeto estruturado semelhante a:

{
  "symbol": "BTCUSDT",
  "market": {},
  "technical": {},
  "microstructure": {},
  "regime": {},
  "ml": {},
  "news": {},
  "risk": {},
  "signal": {}
}

O modelo deverá retornar JSON estruturado.

Exemplo:

{
  "decision": "APPROVE",
  "context_score": 84,
  "risk_flags": [],
  "conflicts": [],
  "reason_codes": [
    "TREND_ALIGNMENT",
    "ML_CONFIRMATION",
    "VOLUME_CONFIRMATION"
  ],
  "explanation": "..."
}
32. OLLAMA NÃO PODE ALTERAR O SCORE QUANTITATIVO

O score calculado pelo:

SignalEngine

é soberano.

Ollama pode:

APPROVE
REJECT
FLAG_CONFLICT
EXPLAIN

Mas não pode:

inventar score
alterar preço
alterar probabilidade
alterar resultado de backtest
33. CONSTRAINED OUTPUT

Toda resposta do Ollama deve passar por validação Pydantic.

Se retornar:

JSON inválido

ou:

campo ausente

ou:

valor fora do domínio

a resposta deve ser rejeitada.

Nunca tentar "adivinhar" o que o LLM quis dizer.

34. FALLBACK

Se Ollama estiver indisponível:

SignalEngine continua funcionando.

O sistema deve retornar:

LLM_CONTEXT = UNAVAILABLE

e não:

BUY

automaticamente.

35. FASE 16 — OPPORTUNITY SCANNER

Criar um serviço:

OpportunityScanner

que analise múltiplos ativos.

Exemplo:

BTCUSDT
ETHUSDT
SOLUSDT
XRPUSDT
ADAUSDT
...

e produza:

TOP OPPORTUNITIES

Exemplo:

1. BTCUSDT LONG       88
2. ETHUSDT LONG       84
3. SOLUSDT SHORT      79
4. XRPUSDT WATCH      65
36. RANKING

O ranking deve considerar:

Trade Score
Risk/Reward
ML probability
Regime
Data quality
Liquidity
News confidence

Não simplesmente:

maior probabilidade = melhor trade
37. FASE 17 — DASHBOARD

Adicionar uma tela:

/opportunities

Com:

Symbol
Direction
Score
State
ML Probability
Regime
Trend
Momentum
Volume
Order Flow
News
Risk/Reward
Entry
Stop
Target

Adicionar filtros:

LONG
SHORT
HIGH CONVICTION
SETUP
REGIME
TIMEFRAME
38. DETALHE DA OPORTUNIDADE

Ao clicar:

BTCUSDT

mostrar:

Market Context
Multi-Timeframe
Technical
Microstructure
ML
News
Risk
Signal
Ollama Analysis
Backtest
39. EXPLICAÇÃO DO SINAL

A interface deve mostrar:

WHY THIS SIGNAL?

Exemplo:

LONG — Score 87

+ Trend alignment
+ Momentum positive
+ Volume confirmation
+ Order flow positive
+ ML probability 82%
+ Positive news

Risk:
- Elevated volatility

Essa explicação deve ser construída com dados reais do sistema.

40. FASE 18 — VERSIONAMENTO

Cada sinal deve registrar:

signal_id
symbol
timestamp
timeframe
feature_version
model_version
strategy_version
news_version
signal_score
risk_parameters

Isso é obrigatório.

Precisamos conseguir responder:

"Por que o sistema gerou esse sinal ontem às 14:32?"

41. AUDITORIA

Criar:

Signal Audit Trail

Nunca apagar sinais históricos.

Guardar:

input
features
prediction
news
score
risk
LLM result
final decision
42. FASE 19 — MODEL REGISTRY

Preservar o registry atual.

O sistema já possui:

Candidate
Approved
Pending
Superseded

e aprovação de modelos.

Expandir para registrar:

feature_version
dataset_version
training_period
validation_period
test_period
hyperparameters
metrics
git_commit
model_hash
43. NÃO PROMOVER MODELO SOMENTE POR AUC

Um modelo não pode ser promovido simplesmente porque:

AUC > modelo anterior

Também exigir avaliação de:

Profit Factor
Expectancy
Drawdown
Sharpe
Calibration

e estabilidade por regime.

44. TESTES OBRIGATÓRIOS

Toda implementação deve possuir testes.

Unit tests
FeatureEngine
RegimeEngine
MicrostructureEngine
NewsEngine
SignalEngine
RiskEngine
Integration tests
Binance → DB
DB → Features
Features → ML
News → News Engine
Signal → API
ML tests
No leakage
Temporal split
Feature consistency
Model loading
Probability calibration
Backtest tests
fees
slippage
entry timing
exit timing
stop
take profit
45. TESTE DE DATA LEAKAGE

Criar testes explícitos.

Exemplo conceitual:

Dado o candle T

alterar qualquer dado posterior a T

não pode alterar:

features(T)
prediction(T)
signal(T)

Se alterar:

FAIL
46. TESTE DE DETERMINISMO

Dado:

same market data
same model
same configuration

o:

SignalEngine

deve produzir o mesmo resultado.

O LLM não pode ser utilizado para cálculos determinísticos.

47. OBSERVABILIDADE

Manter as métricas existentes.

Adicionar métricas:

signals_generated
signals_long
signals_short
signals_watch
signals_no_trade
high_conviction_signals
paper_trades
model_predictions
llm_failures
news_events
data_quality_failures
48. LOGGING

Cada sinal deve gerar log estruturado.

Exemplo:

{
  "event": "signal_generated",
  "symbol": "BTCUSDT",
  "direction": "LONG",
  "score": 87,
  "model_probability": 0.82,
  "regime": "TREND_UP"
}

Nunca registrar:

API keys
JWT secrets
passwords
private credentials
49. CONFIGURAÇÃO

Tudo que puder variar deverá estar configurável.

Exemplo:

SIGNAL_SCORE_THRESHOLD=80
SETUP_SCORE_THRESHOLD=60
ML_MIN_PROBABILITY=0.60
MAX_SPREAD_BPS=...
BACKTEST_FEE_BPS=...
BACKTEST_SLIPPAGE_BPS=...
NEWS_MAX_AGE_MINUTES=...

Não colocar esses valores espalhados pelo código.

50. NÃO FAZER

É proibido:

reescrever o projeto inteiro
remover funcionalidades existentes sem justificativa
adicionar dependências sem necessidade
inventar dados
inventar métricas
inventar resultados de backtest
usar LLM para substituir cálculos matemáticos
usar dados futuros
fazer lookahead
usar random split em séries temporais
criar execução real
adicionar API keys diretamente no código
considerar 80% de probabilidade como 80% de win rate sem validação
51. EXECUÇÃO OBRIGATORIAMENTE INCREMENTAL

Você NÃO deve implementar todas as fases de uma vez.

Executar:

FASE 0
↓
VALIDAR
↓
FASE 1
↓
VALIDAR
↓
FASE 2
↓
VALIDAR
...

Após cada fase:

executar testes;
corrigir erros;
verificar banco;
verificar API;
verificar Docker;
atualizar documentação;
informar arquivos alterados;
informar resultado;
somente então avançar.
52. CHECKPOINT OBRIGATÓRIO

Ao terminar cada fase, produzir:

PHASE CHECKPOINT

Phase:
Status:

Files created:
Files modified:

Database changes:

Tests:
Passed:
Failed:

Docker:
Status:

API:
Status:

Known issues:

Next phase:
53. NÃO AVANCE SE EXISTIR ERRO

Se:

test failed

ou:

migration failed

ou:

Docker failed

ou:

API failed

ou:

data leakage detected

não avançar.

Corrigir primeiro.

54. MIGRATIONS

Qualquer alteração de banco deve criar migration.

Nunca alterar manualmente o banco de produção/desenvolvimento sem migration versionada.

Toda migration precisa possuir:

upgrade
downgrade

quando tecnicamente possível.

55. COMPATIBILIDADE

Não quebrar:

/api/auth
/api/signals/latest
/api/ml/*
/api/news
/api/chat

sem criar compatibilidade ou atualizar explicitamente todos os consumidores.

O frontend existente deve continuar funcionando durante a evolução.

56. DOCUMENTAÇÃO

Atualizar:

ARCHITECTURE.md
DOCUMENTATION.md
README.md

Criar:

docs/
    CURRENT_SYSTEM_AUDIT.md
    SIGNAL_ENGINE.md
    FEATURE_CATALOG.md
    ML_PIPELINE.md
    NEWS_INTELLIGENCE.md
    BACKTESTING.md
    WALK_FORWARD.md
    PAPER_TRADING.md
    OLLAMA_GUARDRAILS.md
    DATA_QUALITY.md
57. FEATURE CATALOG

Criar documentação para cada feature:

Feature:
Descrição:
Fórmula:
Timeframe:
Fonte:
Lookback:
Pode usar futuro? NÃO
Usada no modelo:
Usada no score:
Teste:

Exemplo:

Feature:
RSI14

Fonte:
OHLC

Lookback:
14 candles

Future data:
NO

Normalization:
0..1
58. SIGNAL CONTRACT

Criar um contrato único.

Exemplo:

{
  "signal_id": "...",
  "symbol": "BTCUSDT",
  "timestamp": "...",
  "timeframe": "15m",
  "direction": "LONG",
  "state": "HIGH_CONVICTION",
  "score": 87,
  "ml_probability": 0.82,
  "regime": "TREND_UP",
  "entry": 100000,
  "stop_loss": 98500,
  "take_profit": 103500,
  "risk_reward": 2.33,
  "news_score": 0.74,
  "data_quality": "VALID",
  "model_version": "...",
  "strategy_version": "...",
  "llm_status": "APPROVED"
}

Os valores acima são somente exemplo de contrato, não resultados reais.

59. SEGURANÇA

Nesta fase:

LIVE_TRADING_ENABLED=false

obrigatoriamente.

Não criar endpoint que envie ordem real.

Não solicitar API Key de trading se não for necessária.

O sistema deve continuar sendo:

ANALYSIS
+
BACKTEST
+
PAPER TRADING
60. CRITÉRIO FINAL DE CONCLUSÃO

O projeto somente será considerado concluído quando:

Data
REST funcionando
WebSocket funcionando
Data quality funcionando
Candles funcionando
Trades funcionando
Order book funcionando
Features
Technical
Momentum
Volume
Volatility
Microstructure
Multi-timeframe
Regime
News
ML
Training
Validation
Testing
Calibration
Registry
No leakage
Walk-forward
Signal
LONG
SHORT
WATCH
NO TRADE
Score
Risk
Reward
LLM
Structured output
Validated output
No hallucinated market data
Fallback
Audit
Backtesting
Fees
Slippage
Stops
Targets
Long
Short
No Trade
Walk-forward
Regime analysis
Paper Trading
Virtual positions
PnL
Fees
Slippage
Risk
Audit
Frontend
Dashboard
Opportunities
Signal detail
News
Model status
Backtest
Paper trading
Segurança
No live orders
No exposed credentials
JWT/RBAC preserved
61. ORDEM EXATA DE EXECUÇÃO

Você deverá executar exatamente nesta ordem:

0. AUDIT
        ↓
1. DATA QUALITY
        ↓
2. MARKET DATA
        ↓
3. NORMALIZATION
        ↓
4. MULTI-TIMEFRAME
        ↓
5. FEATURE ENGINE
        ↓
6. MICROSTRUCTURE
        ↓
7. MARKET REGIME
        ↓
8. NEWS INTELLIGENCE
        ↓
9. DATASET V2
        ↓
10. ML ENGINE V2
        ↓
11. SIGNAL ENGINE
        ↓
12. RISK ENGINE
        ↓
13. BACKTEST V2
        ↓
14. WALK-FORWARD
        ↓
15. PAPER TRADING
        ↓
16. OLLAMA
        ↓
17. OPPORTUNITY SCANNER
        ↓
18. FRONTEND
        ↓
19. OBSERVABILITY
        ↓
20. FINAL VALIDATION

Não alterar essa ordem sem justificar tecnicamente a alteração.

62. FORMATO DA RESPOSTA DA IA DURANTE O DESENVOLVIMENTO

Sempre responder:

FASE ATUAL:
OBJETIVO:

ANÁLISE:

ARQUIVOS A ALTERAR:

ARQUIVOS A CRIAR:

ALTERAÇÕES:

BANCO:

TESTES:

RESULTADO:

PROBLEMAS:

CHECKPOINT:

PRÓXIMA FASE:

Nunca simplesmente responder:

"feito"

sem mostrar o que foi feito e como foi validado.

63. REGRA PARA AGENTE DE IA

Se você for um agente de IA trabalhando diretamente no repositório:

primeiro inspecione;
não presuma;
não invente arquivos;
não invente classes;
não invente APIs;
não remova código sem verificar dependências;
procure referências antes de alterar interfaces;
execute testes antes e depois;
faça alterações pequenas;
valide cada etapa;
documente cada alteração;
pare diante de erros;
nunca habilite trading real.

Se encontrar algo diferente desta especificação no código atual:

não corrija silenciosamente.

Informe:

EXPECTED
vs
ACTUAL

e proponha a alteração.

64. PRIMEIRA TAREFA

Não implemente nenhuma funcionalidade ainda.

Sua primeira tarefa é exclusivamente:

FASE 0 — AUDITORIA

Leia o repositório inteiro e produza:

docs/CURRENT_SYSTEM_AUDIT.md

Depois apresente:

1. Arquitetura encontrada
2. Componentes encontrados
3. Banco encontrado
4. APIs encontradas
5. ML encontrado
6. Backtester encontrado
7. Ollama encontrado
8. MCP encontrado
9. Notícias encontradas
10. Frontend encontrado
11. Testes encontrados
12. Problemas encontrados
13. Gaps em relação à arquitetura alvo
14. Plano de alterações
15. Riscos

Não escreva código da Fase 1 ainda.

Aguarde validação da auditoria.

65. REGRA FINAL

O objetivo deste projeto não é construir uma IA que "acerte trades".

O objetivo é construir um sistema quantitativo auditável que procure vantagem estatística no mercado e consiga provar, através de dados históricos e paper trading, quando essa vantagem existe e quando não existe.

Nunca afirmar que uma estratégia possui alta taxa de acerto sem evidência estatística.

FIM DO PROMPT
Como eu recomendo usar esse prompt

Tem uma coisa importante aqui: não entregue esse prompt para a IA e mande "faça tudo".

Mesmo com o prompt acima, um agente de código pode tentar modificar 50 arquivos de uma vez e criar uma arquitetura difícil de validar.

Faça assim:

Etapa 1 — coloque o prompt inteiro

A IA deverá executar somente a Fase 0.

Ela deve primeiro analisar o seu repositório atual.

Isso é particularmente importante porque sua documentação mostra que há algumas versões/estados diferentes do sistema: por exemplo, o DOCUMENTATION.md registra WebSocket, trades, snapshots e notícias, enquanto o ARCHITECTURE.md descreve o fluxo atual de ML e os sinais.

Etapa 2 — valide a auditoria

Você me manda o resultado da IA.

Eu posso revisar:

CURRENT
vs
TARGET

e verificar se ela entendeu corretamente o projeto.

Etapa 3 — só então liberar a Fase 1

Depois:

Execute somente a Fase 1.
Não avance para a Fase 2.

Quando terminar:

Execute somente a Fase 2.

E assim por diante.

Uma melhoria que eu recomendo fortemente

Como você pretende usar IA como desenvolvedora, eu acrescentaria ao repositório um arquivo:

AGENTS.md

ou, dependendo do agente:

CLAUDE.md
.cursor/rules/
.github/copilot-instructions.md

com as regras arquiteturais permanentes.

Assim, a IA não depende apenas do prompt que você passou uma vez.

Ela encontra no próprio projeto regras como:

NO LIVE TRADING
NO DATA LEAKAGE
NO FUTURE DATA
NO LLM GENERATED MARKET DATA
NO RANDOM TIME SERIES SPLIT
NO UNDOCUMENTED FEATURES
NO SILENT ARCHITECTURAL CHANGES
TEST BEFORE AND AFTER
DOCUMENT EVERY MIGRATION

Isso é especialmente importante para o seu projeto porque o sistema já possui uma arquitetura relativamente madura — PostgreSQL, Redis, collectors, ML, registry, retrainer, backtester e Ollama — e seria um desperdício deixar um agente simplesmente substituir tudo por uma implementação genérica.

Eu faria esse AGENTS.md como a próxima peça do projeto, junto com um docs/ROADMAP.md, transformando tudo isso em um contrato permanente para qualquer desenvolvedor ou agente de IA que trabalhar no Trade AI.

No seu projeto atual já existe um frontend React/Vite com dashboard, autenticação, chat, página de sinais, ML e notícias. Portanto, eu faria a evolução dele sem reescrever tudo.

O frontend alvo deveria ficar aproximadamente assim
                    TRADE AI
                       │
        ┌──────────────┼──────────────┐
        │              │              │
     MERCADO       OPORTUNIDADES    NOTÍCIAS
        │              │              │
        └──────────────┼──────────────┘
                       │
                 DASHBOARD
                       │
       ┌───────────────┼────────────────┐
       │               │                │
   Market View     Signal Detail    Portfolio
       │               │                │
       │          ┌────┼─────┐          │
       │          │    │     │          │
       │        ML   News   Risk         │
       │          │    │     │          │
       │          └────┼─────┘          │
       │               │                │
       └───────────────┼────────────────┘
                       │
                 BACKTESTING
                       │
                 PAPER TRADING
                       │
                  MODEL LAB
Eu acrescentaria uma FASE específica de Frontend

No prompt anterior, substitua a FASE 18 por esta especificação:

FASE 18 — FRONTEND 2.0

O frontend existente deve ser evoluído, não reescrito.

Tecnologia atual:

React
TypeScript
Vite

Preservar a arquitetura existente sempre que possível.

Antes de alterar o frontend:

identificar todas as rotas existentes;
identificar todos os componentes;
identificar hooks;
identificar services/API clients;
identificar stores/state management;
identificar componentes reutilizáveis;
identificar gráficos;
identificar autenticação;
identificar páginas existentes;
identificar endpoints consumidos.

Criar:

docs/FRONTEND_ARCHITECTURE.md
18.1 DASHBOARD PRINCIPAL

Criar/evoluir:

/dashboard

O dashboard deve apresentar:

Market Overview
BTC
ETH
SOL
Market Trend
Market Regime
Market Volatility
Top Opportunities
#   Asset    Direction   Score   Probability   R/R
1   BTC      LONG        88      82%           2.4
2   ETH      LONG        84      79%           2.1
3   SOL      SHORT       81      76%           2.7
Market Regime

Mostrar:

TREND UP
TREND DOWN
SIDEWAYS
HIGH VOLATILITY
LOW VOLATILITY
News

Mostrar as notícias relevantes que impactam os ativos monitorados.

18.2 OPPORTUNITIES

Criar:

/opportunities

Essa será uma das telas principais do sistema.

Tabela:

Asset
Direction
State
Score
ML Probability
Regime
Trend
Momentum
Volume
Order Flow
News
Risk/Reward
Updated

Filtros:

LONG
SHORT
WATCH
SETUP
HIGH CONVICTION
NO TRADE

Filtros adicionais:

Asset
Score
Probability
Regime
Timeframe
News Impact

Ordenação:

Score DESC
Probability DESC
Risk/Reward DESC
18.3 DETALHE DO ATIVO

Criar:

/assets/:symbol

Exemplo:

/assets/BTCUSDT

Mostrar:

BTCUSDT
Price Chart

Exibir:

Candles
Volume
EMA
SMA
Bollinger Bands

Permitir:

5m
15m
1h
4h
1d
18.4 MULTI-TIMEFRAME

Mostrar:

TIMEFRAME      TREND       MOMENTUM       SIGNAL

1D             🟢          🟢             BULLISH
4H             🟢          🟢             BULLISH
1H             🟢          🟡             BULLISH
15M            🟡          🟢             SETUP
5M             🟢          🟢             ENTRY

Isso permite que o usuário entenda o contexto antes de olhar o sinal final.

18.5 SIGNAL DETAIL

Ao selecionar uma oportunidade:

Signal Detail

mostrar:

Direction
Score
State
ML Probability
Market Regime
Entry
Stop Loss
Take Profit
Risk/Reward

Depois:

Technical
RSI
MACD
EMA
ATR
ADX
Volume
Microstructure
Bid/Ask Imbalance
Spread
Depth
Buy Pressure
Sell Pressure
Large Trades
News
Sentiment
Impact
Event
Sources
Published At
18.6 EXPLICAÇÃO DO SINAL

Criar uma seção:

Why this signal?

Exemplo:

LONG — HIGH CONVICTION

Score: 87

Positive factors:
✓ Higher timeframe trend
✓ Momentum confirmation
✓ Volume confirmation
✓ Positive order flow
✓ ML probability 82%

Risk factors:
⚠ High volatility

News:
✓ Positive

Risk/Reward:
2.4

Essa explicação deve ser baseada nos dados reais.

18.7 IA / OLLAMA

Criar:

AI Analysis

A tela deve separar claramente:

Quantitative Analysis
ML Probability
Signal Score
Risk
Market Regime
AI Contextual Analysis
Ollama

Mostrar:

AI Assessment:
APPROVE

Context:
...

Risk Flags:
...

Conflicts:
...

Adicionar uma indicação clara:

Quantitative Engine

versus:

AI Context Engine

para que o usuário nunca confunda uma explicação do LLM com um cálculo quantitativo.

18.8 NOTÍCIAS

Criar:

/news

Mostrar:

Título
Fonte
Data
Ativos relacionados
Sentiment
Impact
Event Type

Filtros:

BTC
ETH
SOL
...

e:

Positive
Neutral
Negative
High Impact
Medium Impact
Low Impact
18.9 NEWS → ASSET

Ao clicar em uma notícia:

News Detail

mostrar:

Title
Source
Published At
URL
Assets
Sentiment
Impact
Event Type
AI Summary

E:

Related Signals

para mostrar se aquela notícia está impactando algum sinal.

18.10 BACKTESTING

Criar:

/backtesting

Permitir selecionar:

Asset
Strategy
Model
Timeframe
Start Date
End Date

Mostrar:

Total Trades
Win Rate
Profit Factor
Expectancy
Net PnL
Max Drawdown
Sharpe
Fees
Slippage

Gráficos:

Equity Curve
Drawdown
Trade Distribution
PnL by Month
PnL by Regime
18.11 WALK-FORWARD

Criar visualização:

Walk Forward Validation

Mostrar:

Training Period
Validation Period
Testing Period

e os resultados de cada janela.

Exemplo:

Window 1
Train: Jan-Mar
Test: Apr
PF: 1.72

Window 2
Train: Feb-Apr
Test: May
PF: 1.41

Window 3
Train: Mar-May
Test: Jun
PF: 1.58
18.12 PAPER TRADING

Criar:

/paper-trading

Mostrar:

Virtual Balance
Equity
Open Positions
Closed Positions
PnL
Win Rate
Drawdown

Tabela:

Asset
Direction
Entry
Current
Stop
Target
PnL
Duration
Status
18.13 MODEL LAB

Criar:

/models

Mostrar:

Model
Version
Status
Training Date
Features
Training Period
Validation
Test
AUC
F1
Profit Factor
Expectancy
Drawdown
Sharpe

Status:

CANDIDATE
PENDING
APPROVED
ACTIVE
SUPERSEDED

O backend já possui conceito de registry/model approval; o frontend deve expor isso visualmente.

18.14 DATA QUALITY

Criar:

/data-quality

Mostrar:

Source
Symbol
Timeframe
Last Update
Status
Gaps
Duplicates
Invalid Records
Latency

Estados:

VALID
WARNING
INVALID
18.15 SISTEMA DE ALERTAS

Criar:

/alerts

Permitir configurar:

Score >= 80
Probability >= 75%
LONG
SHORT
High Impact News
Regime Change

Exemplo:

Alert me when:

BTCUSDT
AND
Score >= 85
AND
LONG
AND
ML Probability >= 80%
18.16 TEMPO REAL

O frontend deve utilizar WebSocket/SSE quando apropriado.

Não fazer:

setInterval(() => fetch(...), 1000)

para tudo.

Dados de alta frequência devem possuir estratégia específica de atualização.

Separar:

Real-time data
Near-real-time data
Historical data
18.17 UX

O frontend deve ser desenvolvido pensando em:

Desktop first
Responsive
Dark theme
High information density
Low visual noise

Priorizar leitura rápida.

O usuário deve conseguir identificar:

QUAL É A MELHOR OPORTUNIDADE?
POR QUE?
QUAL O RISCO?
QUAL A PROBABILIDADE?
QUAL O REGIME?
O QUE ESTÁ ACONTECENDO NAS NOTÍCIAS?

em poucos segundos.

18.18 NÃO USAR CORES COMO ÚNICA INFORMAÇÃO

Não depender somente de:

verde
vermelho

Adicionar:

LONG
SHORT
WATCH
NO TRADE

e ícones/textos acessíveis.

18.19 API CONTRACT

O frontend não deve calcular:

Trade Score
ML Probability
Risk
Regime

Esses valores devem vir do backend.

Frontend é responsável por:

display
filter
sort
interaction
visualization

Backend é responsável por:

business logic
ML
signal
risk
18.20 FRONTEND TESTS

Adicionar:

unit tests
component tests
API integration tests

Testar principalmente:

Signal rendering
Opportunity ranking
Charts
Filters
Authentication
Paper trading
Backtest
Model status
News
18.21 FRONTEND CRITÉRIO DE ACEITE

O frontend somente estará concluído quando o usuário conseguir:

1. Abrir o dashboard
2. Ver o mercado
3. Ver as melhores oportunidades
4. Filtrar LONG/SHORT
5. Abrir um ativo
6. Ver candles
7. Ver múltiplos timeframes
8. Entender o sinal
9. Ver ML
10. Ver notícias
11. Ver risco
12. Ver análise do Ollama
13. Executar backtest
14. Ver walk-forward
15. Acompanhar paper trading
16. Consultar modelos
17. Consultar qualidade dos dados
18. Configurar alertas
E eu mudaria a ordem final do projeto

Em vez de terminar com apenas:

Backend
↓
Ollama
↓
Frontend

eu trataria como dois fluxos paralelos:

                    BACKEND
                       │
        ┌──────────────┴──────────────┐
        │                             │
 QUANTITATIVE ENGINE             AI ENGINE
        │                             │
        └──────────────┬──────────────┘
                       │
                  API CONTRACT
                       │
                       ▼
                    FRONTEND
                       │
        ┌──────────────┼───────────────┐
        │              │               │
    Dashboard    Opportunities     Asset Detail
        │              │               │
        ├──────────────┼───────────────┤
        │              │               │
      News         Backtesting    Paper Trading
        │              │               │
        └──────────────┼───────────────┘
                       │
                  Model Lab

Então sim: o frontend faz parte do projeto desde o começo. A diferença é que eu não deixaria o desenvolvedor "embelezar o dashboard" enquanto o backend ainda está mudando. Primeiro definimos os contratos de dados, e cada nova capacidade do backend já nasce com sua representação no frontend.

Isso evita um problema muito comum: terminar com um backend sofisticado de sinais, ML e backtesting e depois descobrir que o frontend não consegue explicar por que o sistema recomendou aquele trade.