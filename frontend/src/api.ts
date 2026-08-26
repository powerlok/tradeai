export type Signal = {
  symbol: string;
  timeframe: string;
  model_type: string;
  signal: 'BUY' | 'SELL' | 'WATCH';
  probability: number | null;
  price: number;
  timestamp: number;
  checked_at?: number;
  model_available: boolean;
  indicators: Record<string, number | null>;
};

export type Candle = {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type ModelVersion = { version: string; symbol: string; timeframe: string; model_type: string; status: string; active: boolean; created_at: string; metrics: Record<string, number | null> };
export type BacktestResult = { symbol?: string; timeframe?: string; model_type?: string; total_return: number; buy_hold_return?: number; sharpe_ratio?: number; max_drawdown?: number; win_rate: number; total_trades: number; total_fees?: number; total_slippage?: number; final_equity: number; bars?: number; evaluation_mode?: string; out_of_sample?: boolean; profit_factor?: number; expectancy?: number; average_mae?: number; average_mfe?: number; exit_reasons?: Record<string, number>; mode?: string };
export type StrategyCatalogItem = { id: string; name: string; parameters: Record<string, number> };
export type StrategyBacktestResult = { strategy_type: string; results: (BacktestResult & { symbol: string; timeframe: string; strategy_params: Record<string, number>; fee_bps: number; slippage_bps: number })[] };
export type WalkForwardWindow = { window: number; train_start: number; train_end: number; validation_start: number; validation_end: number; test_start: number; test_end: number; test_bars: number; result: BacktestResult };
export type WalkForwardResult = { mode: string; symbol: string; timeframe: string; strategy_type: string; strategy_params: Record<string, number>; window_count: number; total_trades: number; win_rate: number; total_pnl: number; average_return: number; worst_return: number; profitable_windows: number; train_bars: number; validation_bars: number; test_bars: number; quality_gate: { passed: boolean; checks: Record<string, boolean>; floor: Record<string, number> }; windows: WalkForwardWindow[] };
export type LivePrice = { symbol: string; price: number; qty: number; event_time: number; source: string };
export type OrderBookSummary = { best_bid: number | null; best_ask: number | null; spread: number | null; mid_price: number | null; bid_qty: number; ask_qty: number };
export type AppNotification = { id: string; type: 'chat_response' | 'trend_change' | 'opportunity_alert' | 'system'; title: string; message: string; metadata: Record<string, unknown>; created_at: number };
export type NewsItem = { source: string; title: string; published_at: string; url: string };
export type Opportunity = { assessment_id: string; status: 'APPROVED' | 'OBSERVE' | 'BLOCKED'; action: 'PAPER_ENTRY' | 'WATCH' | 'NO_ACTION'; reason_codes: string[]; symbol: string; timeframe: string; direction: 'BUY' | 'SELL'; state: string; score: number; probability: number; risk_reward: number; trade_type: 'LONG' | 'SHORT'; entry_price: number; stop_loss: number; take_profit: number; risk_per_unit: number; exit_rule: string; fee_bps: number; slippage_bps: number; round_trip_cost_pct: number; gross_target_pct: number; net_target_pct: number; net_stop_pct: number; cost_viable: boolean; directional_probability: number; break_even_probability: number; expected_value_pct: number; safety_buffer_pct: number; required_move_pct: number; opportunity_quality: 'FORTE' | 'MODERADA' | 'FRACA' };
export type MultiTimeframe = { symbol: string; timeframes: { timeframe: string; close: number; timestamp: number; return_pct: number; trend: string }[]; regime: { name?: string; regime?: string; volatility: number; trend_strength: number; confidence: number } };
export type PaperPosition = { id: number; symbol: string; direction: string; quantity: number; entry_price: number; exit_price: number | null; stop: number; target: number; status: string; opened_at: number; closed_at: number | null; exit_reason?: string | null; pnl: number | null; fees: number; decision_snapshot?: Record<string, unknown> | null; mark_price: number | null; unrealized_pnl: number | null; unrealized_pnl_pct: number | null; price_updated_at: number | null };
export type PaperRisk = { approved: boolean; reason_codes: string[]; initial_equity: number; open_exposure: number; proposed_exposure: number; open_risk: number; proposed_risk: number; realized_pnl_today: number; max_trade_risk: number; max_portfolio_risk: number; max_exposure: number; max_daily_loss: number };
export type OperationalState = { state: 'PAPER' | 'TESTNET' | 'LIVE_DISABLED' | 'KILL_SWITCH'; available_states: string[]; entry_enabled: boolean };
export type PaperHistory = { trades: PaperPosition[]; page: number; page_size: number; total: number; pages: number; summary: { realized_pnl: number; winning_trades: number; losing_trades: number } };
export type PaperTradeEvent = { id: number; paper_trade_id: number; symbol: string; event_type: string; event_time: number; payload: Record<string, unknown> };

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { ...init?.headers, Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) {
    localStorage.removeItem('trading_access_token');
    window.location.reload();
  }
  const rawBody = await response.text();
  let body: { detail?: string } & T;
  try {
    body = JSON.parse(rawBody) as { detail?: string } & T;
  } catch {
    throw new Error(response.ok ? 'A API retornou uma resposta inválida.' : `Erro da API (${response.status}).`);
  }
  if (!response.ok) throw new Error(body.detail || 'Não foi possível consultar a API');
  return body as T;
}

export function login(username: string, password: string) {
  return request<{ access_token: string }>('/api/auth/login', '', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
}

export async function getMarket(token: string, symbol: string, timeframe: string, abortSignal?: AbortSignal) {
  const [signalData, candleData, livePriceData, orderBookData] = await Promise.all([
    request<{ signals: Signal[] }>(`/api/signals/latest?symbol=${symbol}&timeframe=${timeframe}`, token, { signal: abortSignal }),
    request<{ candles: Candle[] }>(`/api/ml/candles/${symbol}?timeframe=${timeframe}&limit=120`, token, { signal: abortSignal }),
    request<{ prices: LivePrice[] }>(`/api/market/prices?symbols=${symbol}`, token, { signal: abortSignal }).catch(() => ({ prices: [] })),
    request<{ summary: OrderBookSummary }>(`/api/market/orderbook?symbol=${symbol}`, token, { signal: abortSignal }).catch(() => ({ summary: { best_bid: null, best_ask: null, spread: null, mid_price: null, bid_qty: 0, ask_qty: 0 } })),
  ]);
  const livePrice = livePriceData.prices[0];
  return {
    signal: signalData.signals[0],
    candles: candleData.candles,
    livePrice: livePrice ?? null,
    orderBook: orderBookData.summary,
  };
}

export function getRegistry(token: string) { return request<{ models: ModelVersion[] }>('/api/ml/models/registry', token); }
export function runBacktest(token: string, payload: Record<string, string | number>) { return request<BacktestResult>('/api/ml/backtest/run', token, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); }
export function getStrategyCatalog(token: string) { return request<{ strategies: StrategyCatalogItem[] }>('/api/ml/backtest/strategies', token); }
export function runStrategyBacktest(token: string, payload: { symbols: string[]; timeframes: string[]; strategy_type: string; strategy_params: Record<string, number>; initial_cash: number; fee_bps: number; slippage_bps: number; stop_atr_multiple: number; target_risk_reward: number; max_holding_bars: number; start_time?: number; end_time?: number }) { return request<StrategyBacktestResult>('/api/ml/backtest/run-strategy', token, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); }
export function runStrategyWalkForward(token: string, payload: { symbols: string[]; timeframes: string[]; strategy_type: string; strategy_params: Record<string, number>; initial_cash: number; fee_bps: number; slippage_bps: number; stop_atr_multiple: number; target_risk_reward: number; max_holding_bars: number; train_bars: number; validation_bars: number; test_bars: number; max_windows: number }) { return request<{ strategy_type: string; results: WalkForwardResult[] }>('/api/ml/backtest/run-walk-forward', token, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); }
export function getNotifications(token: string) { return request<{ notifications: AppNotification[] }>('/api/notifications', token); }
export function getNews(token: string, limit = 24) { return request<{ news: NewsItem[]; source: string; limit: number }>(`/api/news?limit=${limit}`, token); }
export function getOpportunities(token: string, feeBps = 10, slippageBps = 5, minimumNetTargetPct = 0) { return request<{ opportunities: Opportunity[]; timeframe: string; fee_bps: number; slippage_bps: number; minimum_net_target_pct: number }>(`/api/opportunities?fee_bps=${feeBps}&slippage_bps=${slippageBps}&minimum_net_target_pct=${minimumNetTargetPct}`, token); }
export function getOpportunity(token: string, symbol: string, timeframe: string) { return request<{ opportunities: Opportunity[] }>(`/api/opportunities?symbols=${symbol}&timeframe=${timeframe}`, token); }
export function getOperationalState(token: string) { return request<OperationalState>('/api/operational-state', token); }
export function getMultiTimeframe(token: string, symbol: string) { return request<MultiTimeframe>(`/api/market/multi-timeframe?symbol=${symbol}`, token); }
export function getPaperPositions(token: string) { return request<{ positions: PaperPosition[]; risk: PaperRisk }>('/api/paper/positions', token); }
export function getPaperHistory(token: string, page = 1, pageSize = 10) { return request<PaperHistory>(`/api/paper/history?page=${page}&page_size=${pageSize}`, token); }
export function getPaperTradeEvents(token: string, tradeId: number) { return request<{ trade_id: number; events: PaperTradeEvent[] }>(`/api/paper/positions/${tradeId}/events`, token); }
export function openPaperPosition(token: string, payload: { symbol: string; direction: string; quantity: number; entry_price: number; stop: number; target: number; opened_at: number; decision_snapshot?: Record<string, unknown> }) { return request<{ status: string; trade: PaperPosition }>('/api/paper/positions', token, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); }
export function closePaperPosition(token: string, tradeId: number, payload: { price?: number; closed_at: number; exit_reason?: string }) { return request<{ status: string; trade_id: number; pnl: number | null; exit_price?: number | null; idempotent?: boolean }>(`/api/paper/positions/${tradeId}/close`, token, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); }
export function deleteNotification(token: string, id: string) { return request<void>(`/api/notifications/${id}`, token, { method: 'DELETE' }); }
export function clearNotifications(token: string) { return request<void>('/api/notifications', token, { method: 'DELETE' }); }
export function sendMarketChat(token: string, payload: { message: string; symbol: string; timeframe: string; signal?: string | null; last_price?: number | null; spread?: number | null; market_state?: string | null }) {
  return request<{ answer: string; context: Record<string, unknown> }>('/api/chat/message', token, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function streamMarketChat(
  token: string,
  payload: Parameters<typeof sendMarketChat>[1],
  onEvent: (event: { type: string; message?: string; content?: string; answer?: string; context?: Record<string, unknown> }) => void,
) {
  let response: Response;
  try {
    response = await fetch('/api/chat/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    if (!(error instanceof TypeError)) throw error;
    await new Promise((resolve) => window.setTimeout(resolve, 1200));
    try {
      response = await fetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      });
    } catch {
      throw new Error('O backend está temporariamente indisponível. Tente novamente em alguns segundos.');
    }
  }
  if (response.status === 401) {
    localStorage.removeItem('trading_access_token');
    window.location.reload();
  }
  if (!response.ok || !response.body) {
    const rawBody = await response.text();
    let message = `Erro da API (${response.status}).`;
    try {
      message = (JSON.parse(rawBody) as { detail?: string }).detail || message;
    } catch {
      // Keep the status-based message for non-JSON proxy errors.
    }
    throw new Error(message);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (line.trim()) onEvent(JSON.parse(line));
    }
    if (done) break;
  }
  if (buffer.trim()) onEvent(JSON.parse(buffer));
}
