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

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { ...init?.headers, Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) {
    localStorage.removeItem('trading_access_token');
    window.location.reload();
  }
  const body = await response.json();
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
  const [signalData, candleData] = await Promise.all([
    request<{ signals: Signal[] }>(`/api/signals/latest?symbol=${symbol}&timeframe=${timeframe}`, token, { signal: abortSignal }),
    request<{ candles: Candle[] }>(`/api/ml/candles/${symbol}?timeframe=${timeframe}&limit=120`, token, { signal: abortSignal }),
  ]);
  return { signal: signalData.signals[0], candles: candleData.candles };
}

export function getRegistry(token: string) { return request<{ models: ModelVersion[] }>('/api/ml/models/registry', token); }
export function runBacktest(token: string, payload: Record<string, string | number>) { return request<BacktestResult>('/api/ml/backtest/run', token, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); }
