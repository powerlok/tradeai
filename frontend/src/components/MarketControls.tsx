import { RefreshCw } from 'lucide-react';

export const symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'];
export const timeframes = [{ value: '1h', label: '1 hora' }, { value: '4h', label: '4 horas' }, { value: '1d', label: '1 dia' }];

export function MarketControls({ symbol, timeframe, loading, updated, onSymbol, onTimeframe, onRefresh }: { symbol: string; timeframe: string; loading: boolean; updated: string; onSymbol: (value: string) => void; onTimeframe: (value: string) => void; onRefresh: () => void }) {
  return (
    <section className="controls panel-controls">
      <div className="controls-main">
        <div className="control-group">
          <label>Instrument</label>
          <div className="segmented">
            {symbols.map((item) => (
              <button type="button" key={item} className={symbol === item ? 'selected' : ''} onClick={() => onSymbol(item)}>
                {item}
              </button>
            ))}
          </div>
        </div>

        <div className="control-group">
          <label>Interval</label>
          <div className="segmented">
            {timeframes.map((item) => (
              <button type="button" key={item.value} className={timeframe === item.value ? 'selected' : ''} onClick={() => onTimeframe(item.value)}>
                {item.value}
              </button>
            ))}
          </div>
        </div>

        <button type="button" className="refresh-button" onClick={onRefresh} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          {loading ? 'Syncing' : 'Refresh'}
        </button>
      </div>

      <span className="updated">{updated}</span>
    </section>
  );
}
