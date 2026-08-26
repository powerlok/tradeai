import { LogOut } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getOpportunity, type Opportunity, type Signal } from '../api';
import { useMarketData } from '../hooks/useMarketData';
import { MarketControls } from './MarketControls';
import { PriceChart } from './PriceChart';
import { SignalOverview } from './SignalOverview';
import { IndicatorPanel } from './IndicatorPanel';
import { Sidebar } from './Sidebar';
import { NotificationCenter } from './NotificationCenter';
import { ConfirmModal, DashboardSkeleton, NoticeStack, type Notice } from './ui/Feedback';

export function MarketDesk({ token, session, onLogout }: { token: string; session: { sub: string; role: string }; onLogout: () => void }) {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [timeframe, setTimeframe] = useState('1h');
  const market = useMarketData(token, symbol, timeframe);
  const [assessment, setAssessment] = useState<Opportunity | null>(null);
  const [assessmentLoading, setAssessmentLoading] = useState(false);
  const [confirmLogout, setConfirmLogout] = useState(false);
  const livePriceLabel = market.livePrice ? `Live ${new Date(market.livePrice.event_time).toLocaleTimeString('pt-BR')} · ${market.livePrice.price.toFixed(2)} USDT` : 'Waiting for live market data';
  const updated = market.livePrice ? `Execução em tempo real · ${new Date(market.livePrice.event_time).toLocaleTimeString('pt-BR')}` : market.signal ? `Candle ${new Date(market.signal.timestamp).toLocaleTimeString('pt-BR')} · consulta ${new Date(market.signal.checked_at || Date.now()).toLocaleTimeString('pt-BR')}` : livePriceLabel;

  const notices: Notice[] = market.error ? [{ type: 'error', title: 'Market data unavailable', message: market.error }] : [];
  useEffect(() => {
    let active = true;
    setAssessmentLoading(true);
    getOpportunity(token, symbol, timeframe)
      .then((response) => { if (active) setAssessment(response.opportunities[0] ?? null); })
      .catch(() => { if (active) setAssessment(null); })
      .finally(() => { if (active) setAssessmentLoading(false); });
    return () => { active = false; };
  }, [token, symbol, timeframe]);
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="content">
        <header id="overview" className="topbar">
          <div>
            <div className="kicker">Market intelligence / live workspace</div>
            <h1>Market desk</h1>
          </div>
          <div className="user-area">
            <span className="live-dot" />
            <span>{session.sub} · {session.role}</span>
            <NotificationCenter token={token} />
            <button className="icon-button" title="Sair" onClick={() => setConfirmLogout(true)}><LogOut size={17} /></button>
          </div>
        </header>

        <NoticeStack notices={notices} onDismiss={() => undefined} />
        <MarketControls symbol={symbol} timeframe={timeframe} loading={market.loading} updated={updated} onSymbol={setSymbol} onTimeframe={setTimeframe} onRefresh={market.refresh} />

        <section className={`decision-summary ${assessment?.status === 'APPROVED' ? 'decision-approved' : 'decision-observe'}`} aria-live="polite">
          <div><div className="card-label">Decision Gate</div><strong>{assessmentLoading ? 'Avaliando setup...' : assessment?.status === 'APPROVED' ? 'Elegível para Paper' : 'Observar / sem entrada'}</strong><span>{assessment?.reason_codes.join(' · ') ?? 'Nenhum plano econômico aprovado para este ativo e timeframe.'}</span></div>
          <div className="decision-metrics"><div><small>Ação</small><b>{assessment?.action ?? 'NO_ACTION'}</b></div><div><small>Alvo líquido</small><b>{assessment ? `${(assessment.net_target_pct * 100).toFixed(2)}%` : '--'}</b></div><div><small>Risco por unidade</small><b>{assessment ? `${assessment.risk_per_unit.toFixed(4)} USDT` : '--'}</b></div></div>
          {assessment?.action === 'PAPER_ENTRY' && <a className="button-primary" href={`/paper?symbol=${assessment.symbol}&direction=${assessment.trade_type}&entry=${assessment.entry_price}&stop=${assessment.stop_loss}&target=${assessment.take_profit}&assessment_id=${assessment.assessment_id}`}>Abrir no Paper</a>}
        </section>

        {market.loading && !market.signal ? (
          <DashboardSkeleton />
        ) : (
          <>
            <SignalOverview signal={market.signal} symbol={symbol} timeframe={timeframe} livePrice={market.livePrice} orderBook={market.orderBook} />
            <PriceChart symbol={symbol} timeframe={timeframe} data={market.chartData} />
            <IndicatorPanel signal={market.signal} />
          </>
        )}
      </main>

      {confirmLogout && <ConfirmModal title="Sair do workspace?" message="Sua sessão será encerrada neste navegador." confirmLabel="Sair" onCancel={() => setConfirmLogout(false)} onConfirm={onLogout} />}
    </div>
  );
}
