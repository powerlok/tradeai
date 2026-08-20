import { ShieldCheck } from 'lucide-react';
import type { Signal } from '../api';
import { formatMetric } from '../lib/format';

export function IndicatorPanel({ signal }: { signal: Signal | null }) {
  const indicators = signal?.indicators || {};
  const metrics: [string, number | null | undefined][] = [['RSI 14', indicators.rsi_14], ['MACD', indicators.macd], ['ATR 14', indicators.atr_14], ['SMA 20', indicators.sma_20], ['EMA 12', indicators.ema_12], ['Bollinger mid', indicators.bb_middle]];
  return <section id="indicators" className="bottom-grid"><div className="panel"><div className="panel-heading"><div><div className="card-label">Technical read</div><h2>Indicators</h2></div></div><div className="metric-grid">{metrics.map(([label, value]) => <div className="metric" key={label}><span>{label}</span><strong>{formatMetric(value)}</strong></div>)}</div></div><div className="panel note-panel"><div className="card-label">System note</div><h2>Analysis only</h2><p>This workspace reads real market candles and model signals. No exchange orders are submitted.</p><div className="paper-badge"><ShieldCheck size={16} /> PAPER TRADING</div></div></section>;
}
