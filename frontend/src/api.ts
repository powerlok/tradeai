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
export type BacktestResult = { symbol: string; timeframe: string; model_type: string; total_return: number; buy_hold_return: number; sharpe_ratio: number; max_drawdown: number; win_rate: number; total_trades: number; total_fees: number; total_slippage: number; final_equity: number; bars: number; evaluation_mode: string; out_of_sample: boolean };
export type LivePrice = { symbol: string; price: number; qty: number; event_time: number; source: string };
export type OrderBookSummary = { best_bid: number | null; best_ask: number | null; spread: number | null; mid_price: number | null; bid_qty: number; ask_qty: number };
export type AppNotification = { id: string; type: 'chat_response' | 'trend_change' | 'system'; title: string; message: string; metadata: Record<string, unknown>; created_at: number };

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
export function getNotifications(token: string) { return request<{ notifications: AppNotification[] }>('/api/notifications', token); }
export function deleteNotification(token: string, id: string) { return request<void>(`/api/notifications/${id}`, token, { method: 'DELETE' }); }
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
  const response = await fetch('/api/chat/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
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
