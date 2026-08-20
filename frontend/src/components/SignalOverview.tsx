import { Activity, ArrowDownRight, ArrowUpRight, Wifi } from 'lucide-react';
import type { Signal } from '../api';
import { formatPrice } from '../lib/format';

export function SignalOverview({ signal, symbol, timeframe }: { signal: Signal | null; symbol: string; timeframe: string }) {
  const signalClass = signal?.signal.toLowerCase() || 'watch';
  return <section className="overview-grid"><div className={`signal-card ${signalClass}`}><div className="card-label">Model signal <span className="model-pill">{signal?.model_type || 'logistic'}</span></div><div className="signal-row"><span className="signal-word">{signal?.signal || 'WATCH'}</span>{signal?.signal === 'BUY' ? <ArrowUpRight size={34} /> : signal?.signal === 'SELL' ? <ArrowDownRight size={34} /> : <Activity size={30} />}</div><div className="signal-detail">{signal?.model_available ? `${((signal.probability || 0) * 100).toFixed(1)}% model confidence` : 'Model not trained for this market yet'}</div></div><div className="price-card"><div className="card-label">Last price</div><strong>{signal ? `${formatPrice(signal.price)} USDT` : '--'}</strong><span className="muted">{symbol} · {timeframe}</span></div><div className="price-card"><div className="card-label">Market state</div><strong className="state"><Wifi size={17} /> Connected</strong><span className="muted">Binance public market data</span></div></section>;
}
