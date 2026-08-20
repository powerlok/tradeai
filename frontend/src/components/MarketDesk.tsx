import { LogOut } from 'lucide-react';
import { useState } from 'react';
import type { Signal } from '../api';
import { useMarketData } from '../hooks/useMarketData';
import { MarketControls } from './MarketControls';
import { PriceChart } from './PriceChart';
import { SignalOverview } from './SignalOverview';
import { IndicatorPanel } from './IndicatorPanel';
import { Sidebar } from './Sidebar';
import { ConfirmModal, DashboardSkeleton, NoticeStack, type Notice } from './ui/Feedback';

export function MarketDesk({ token, session, onLogout }: { token: string; session: { sub: string; role: string }; onLogout: () => void }) {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [timeframe, setTimeframe] = useState('1h');
  const market = useMarketData(token, symbol, timeframe);
  const [confirmLogout, setConfirmLogout] = useState(false);
  const updated = market.signal ? `Candle ${new Date(market.signal.timestamp).toLocaleTimeString('pt-BR')} · consulta ${new Date(market.signal.checked_at || Date.now()).toLocaleTimeString('pt-BR')}` : 'Waiting for market data';

  const notices: Notice[] = market.error ? [{ type: 'error', title: 'Market data unavailable', message: market.error }] : [];
  return <div className="app-shell"><Sidebar /><main className="content"><header id="overview" className="topbar"><div><div className="kicker">Market intelligence / live workspace</div><h1>Market desk</h1></div><div className="user-area"><span className="live-dot" /><span>{session.sub} · {session.role}</span><button className="icon-button" title="Sair" onClick={() => setConfirmLogout(true)}><LogOut size={17} /></button></div></header><NoticeStack notices={notices} onDismiss={() => undefined} /><MarketControls symbol={symbol} timeframe={timeframe} loading={market.loading} updated={updated} onSymbol={setSymbol} onTimeframe={setTimeframe} onRefresh={market.refresh} />{market.loading && !market.signal ? <DashboardSkeleton /> : <><SignalOverview signal={market.signal} symbol={symbol} timeframe={timeframe} /><PriceChart symbol={symbol} timeframe={timeframe} data={market.chartData} /><IndicatorPanel signal={market.signal} /></>}</main>{confirmLogout && <ConfirmModal title="Sair do workspace?" message="Sua sessão será encerrada neste navegador." confirmLabel="Sair" onCancel={() => setConfirmLogout(false)} onConfirm={onLogout} />}</div>;
}
