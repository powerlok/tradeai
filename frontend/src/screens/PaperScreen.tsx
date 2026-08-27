import { useEffect, useState } from 'react';
import { ArrowDownToLine, ArrowUpFromLine, CircleDollarSign, RefreshCw, ShieldCheck, Target, X } from 'lucide-react';
import { closePaperPosition, getPaperHistory, getPaperPositions, openPaperPosition, type PaperPosition, type PaperHistory, type PaperRisk } from '../api';
import { NoticeStack, PageFrame, type Notice } from '../components';
import { PriceChart } from '../components/PriceChart';
import { PaperHistorySection } from '../components/PaperHistorySection';
import { useMarketData } from '../hooks/useMarketData';

const symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'SOLUSDT', 'ADAUSDT', 'DOGEUSDT', 'TRXUSDT', 'AVAXUSDT', 'LINKUSDT', 'TONUSDT', 'SHIBUSDT', 'DOTUSDT', 'BCHUSDT', 'LTCUSDT', 'UNIUSDT', 'XLMUSDT', 'NEARUSDT', 'ATOMUSDT', 'APTUSDT'];
const money = (value: number) => value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const date = (value: number) => new Date(value).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });

export function PaperScreen({ token, session, onLogout }: { token: string; session: { sub: string; role: string }; onLogout: () => void }) {
  const [positions, setPositions] = useState<PaperPosition[]>([]);
  const [risk, setRisk] = useState<PaperRisk | null>(null);
  const [symbol, setSymbol] = useState(() => new URLSearchParams(window.location.search).get('symbol') || 'BTCUSDT');
  const [direction, setDirection] = useState(() => new URLSearchParams(window.location.search).get('direction') || 'LONG');
  const [quantity, setQuantity] = useState('0.01');
  const [entryPrice, setEntryPrice] = useState(() => new URLSearchParams(window.location.search).get('entry') || '');
  const [stop, setStop] = useState(() => new URLSearchParams(window.location.search).get('stop') || '');
  const [target, setTarget] = useState(() => new URLSearchParams(window.location.search).get('target') || '');
  const [assessmentId] = useState(() => new URLSearchParams(window.location.search).get('assessment_id') || '');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [timeframe, setTimeframe] = useState('1h');
  const [streamConnected, setStreamConnected] = useState(false);
  const [history, setHistory] = useState<PaperHistory | null>(null);
  const [historyLoading, setHistoryLoading] = useState(true);
  const market = useMarketData(token, symbol, timeframe);
  const marketPrice = market.livePrice?.price ?? market.candles[market.candles.length - 1]?.close ?? null;
  const openExposure = positions.reduce((total, position) => total + position.quantity * position.entry_price, 0);
  const unrealizedPnl = positions.reduce((total, position) => total + (position.unrealized_pnl ?? 0), 0);
  const unrealizedPnlPct = openExposure ? unrealizedPnl / openExposure : 0;

  function useCurrentPrice() {
    if (!marketPrice) return;
    setEntryPrice(marketPrice.toFixed(2));
    setStop((marketPrice * (direction === 'LONG' ? 0.99 : 1.01)).toFixed(2));
    setTarget((marketPrice * (direction === 'LONG' ? 1.02 : 0.98)).toFixed(2));
  }

  async function load(showLoading = true) {
    if (showLoading) setLoading(true);
    try { const [open, closed] = await Promise.all([getPaperPositions(token), getPaperHistory(token, history?.page ?? 1)]); setPositions(open.positions); setRisk(open.risk); setHistory(closed); } catch (error) { setNotice({ type: 'error', title: 'Paper indisponível', message: error instanceof Error ? error.message : 'Não foi possível carregar as posições.' }); } finally { setLoading(false); setHistoryLoading(false); }
  }
  useEffect(() => { void load(); const timer = window.setInterval(() => void load(false), 5000); return () => window.clearInterval(timer); }, [token]);
  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;
    let stopped = false;
    const connect = () => {
      if (stopped) return;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      socket = new WebSocket(`${protocol}//${window.location.host}/api/paper/stream?token=${encodeURIComponent(token)}`);
      socket.onopen = () => setStreamConnected(true);
      socket.onclose = () => { setStreamConnected(false); if (!stopped) reconnectTimer = window.setTimeout(connect, 2000); };
      socket.onerror = () => socket?.close();
      socket.onmessage = (event) => {
        const update = JSON.parse(event.data) as { type?: string; symbol?: string; price?: number; event_time?: number };
        if (update.type !== 'price' || !update.symbol || !update.price) return;
        setPositions((current) => current.map((position) => {
          if (position.symbol !== update.symbol || update.price === undefined) return position;
          const directionMultiplier = position.direction === 'SHORT' ? -1 : 1;
          const unrealizedPnl = position.quantity * (update.price - position.entry_price) * directionMultiplier;
          const entryValue = position.quantity * position.entry_price;
          return { ...position, mark_price: update.price, unrealized_pnl: unrealizedPnl, unrealized_pnl_pct: entryValue ? unrealizedPnl / entryValue : null, price_updated_at: update.event_time ?? null };
        }));
      };
    };
    connect();
    return () => { stopped = true; if (reconnectTimer) window.clearTimeout(reconnectTimer); socket?.close(); };
  }, [token]);

  async function openPosition(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await openPaperPosition(token, { symbol, direction, quantity: Number(quantity), entry_price: Number(entryPrice), stop: Number(stop), target: Number(target), opened_at: Date.now(), decision_snapshot: { assessment_id: assessmentId || null, status: assessmentId ? 'APPROVED' : 'MANUAL_ENTRY', action: 'PAPER_ENTRY', reason_codes: assessmentId ? ['OPPORTUNITY_ASSESSMENT'] : ['MANUAL_ENTRY'], plan: { entry_price: Number(entryPrice), stop: Number(stop), target: Number(target) } } });
      setNotice({ type: 'success', title: 'Posição aberta', message: `${direction} ${symbol} registrada apenas no ambiente paper.` });
      await load(false);
    } catch (error) { setNotice({ type: 'error', title: 'Posição não aberta', message: error instanceof Error ? error.message : 'Revise os valores informados.' }); } finally { setSaving(false); }
  }
  async function closePosition(position: PaperPosition) {
    setSaving(true);
    try { const result = await closePaperPosition(token, position.id, { price: position.mark_price ?? undefined, closed_at: Date.now(), exit_reason: 'MANUAL' }); setNotice({ type: 'success', title: 'Posição encerrada', message: `PnL realizado: ${money(result.pnl ?? 0)}` }); await load(false); } catch (error) { setNotice({ type: 'error', title: 'Posição não encerrada', message: error instanceof Error ? error.message : 'Não foi possível encerrar a posição.' }); } finally { setSaving(false); }
  }
  async function loadHistory(page: number) {
    setHistoryLoading(true);
    try { setHistory(await getPaperHistory(token, page)); } catch (error) { setNotice({ type: 'error', title: 'Histórico indisponível', message: error instanceof Error ? error.message : 'Não foi possível carregar o histórico.' }); } finally { setHistoryLoading(false); }
  }

  return <PageFrame session={session} onLogout={onLogout} eyebrow="Operação / ambiente controlado" title="Paper portfolio" description="Registre posições virtuais, acompanhe risco e encerre operações sem enviar ordens para a exchange.">
    <NoticeStack notices={notice ? [notice] : []} onDismiss={() => setNotice(null)} />
    <div className="paper-toolbar"><div><div className="kicker">Paper only</div><strong>Simulação persistente</strong><span>Sem credenciais de trading e sem execução real.</span></div><div className="paper-toolbar-actions"><span className={`paper-sync ${streamConnected ? 'stream-online' : 'stream-offline'}`}><span className="stream-dot" />{streamConnected ? 'Preços em tempo real' : 'Reconectando preços'}</span><button className="button-secondary" type="button" onClick={() => { void load(); void market.refresh(); }} disabled={loading || market.loading}><RefreshCw size={15} className={loading || market.loading ? 'spin' : ''} /> Atualizar</button></div></div>
    <section className="paper-summary"><div className="paper-summary-card"><span>Posições abertas</span><strong>{positions.length}</strong><small>ordens virtuais ativas</small></div><div className="paper-summary-card"><span>Exposição registrada</span><strong>{money(openExposure)}</strong><small>valor de entrada em USDT</small></div><div className={`paper-summary-card ${unrealizedPnl >= 0 ? 'paper-profit' : 'paper-loss'}`}><span>PnL não realizado</span><strong>{unrealizedPnl >= 0 ? '+' : ''}{money(unrealizedPnl)} USDT</strong><small>{unrealizedPnlPct >= 0 ? '+' : ''}{(unrealizedPnlPct * 100).toFixed(2)}% marcado ao vivo</small></div><div className="paper-summary-card paper-summary-price"><span>Preço selecionado</span><strong>{marketPrice ? money(marketPrice) : '--'}</strong><small>{symbol} · {timeframe}</small></div></section>
    {assessmentId && <section className="paper-audit-banner"><div><div className="card-label">Auditoria da decisão</div><strong>Entrada originada de uma oportunidade aprovada</strong><span>Assessment {assessmentId} será preservado no snapshot do trade Paper.</span></div><code>{assessmentId}</code></section>}
    {risk && <section className={`paper-risk-banner ${risk.approved ? 'risk-ok' : 'risk-blocked'}`}><div><div className="card-label">Risk Engine</div><strong>{risk.approved ? 'Portfolio dentro dos limites' : 'Novas entradas bloqueadas'}</strong><span>{risk.reason_codes.length ? risk.reason_codes.join(' · ') : 'Risco agregado e perda diária monitorados antes de cada entrada.'}</span></div><div className="paper-risk-metrics"><span>Exposição <b>{money(risk.open_exposure)} / {money(risk.max_exposure)}</b></span><span>Risco no stop <b>{money(risk.open_risk)} / {money(risk.max_portfolio_risk)}</b></span><span>PnL hoje <b>{money(risk.realized_pnl_today)} / -{money(risk.max_daily_loss)}</b></span></div></section>}
    <section className="paper-market panel"><div className="paper-market-head"><div><div className="card-label">Mercado ao vivo</div><h2>{symbol} <span>/ {timeframe}</span></h2></div><div className="paper-market-price">{marketPrice ? `${money(marketPrice)} USDT` : 'Carregando preço...'}</div></div><div className="paper-market-controls"><label>Ativo<select value={symbol} onChange={(event) => setSymbol(event.target.value)}>{symbols.map((item) => <option key={item}>{item}</option>)}</select></label><label>Timeframe<select value={timeframe} onChange={(event) => setTimeframe(event.target.value)}><option>15m</option><option>1h</option><option>4h</option><option>1d</option></select></label><span>{market.error || (market.livePrice ? `Atualizado ${new Date(market.livePrice.event_time).toLocaleTimeString('pt-BR')}` : 'Aguardando dados')}</span></div><div className="paper-chart-wrap"><PriceChart symbol={symbol} timeframe={timeframe} data={market.chartData} /></div></section>
    <div className="paper-layout">
      <form className="panel paper-form" onSubmit={openPosition}><div className="panel-heading"><div><div className="card-label">Nova posição</div><h2>Abrir operação virtual</h2></div><ShieldCheck size={20} /></div><div className="direction-toggle" role="group" aria-label="Direção da posição"><button type="button" className={direction === 'LONG' ? 'selected long' : ''} onClick={() => setDirection('LONG')}>LONG <span>Alta</span></button><button type="button" className={direction === 'SHORT' ? 'selected short' : ''} onClick={() => setDirection('SHORT')}>SHORT <span>Queda</span></button></div><div className="paper-fields"><label>Quantidade<input required min="0.000001" step="any" type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label><label>Entrada<input required min="0.000001" step="any" type="number" value={entryPrice} onChange={(event) => setEntryPrice(event.target.value)} placeholder="Preço de entrada" /></label><label>Stop<input required min="0.000001" step="any" type="number" value={stop} onChange={(event) => setStop(event.target.value)} placeholder="Stop" /></label><label>Alvo<input required min="0.000001" step="any" type="number" value={target} onChange={(event) => setTarget(event.target.value)} placeholder="Take profit" /></label></div><div className="paper-form-actions"><button className="button-secondary" type="button" onClick={useCurrentPrice} disabled={!marketPrice}><Target size={15} /> Preencher pelo preço atual</button><button className="button-primary" type="submit" disabled={saving || !entryPrice || !stop || !target}><CircleDollarSign size={16} /> {saving ? 'Registrando...' : 'Abrir posição'}</button></div></form>
      <section className="paper-positions"><div className="paper-section-head"><div><div className="card-label">Livro aberto · marcação em tempo real</div><h2>Posições ativas</h2></div><span>{positions.length} abertas</span></div>{loading ? <div className="empty-state panel">Carregando posições...</div> : positions.length === 0 ? <div className="empty-state panel"><CircleDollarSign size={28} /><h2>Nenhuma posição aberta</h2><p>Abra uma operação virtual para começar a acompanhar o resultado.</p></div> : <div className="paper-list">{positions.map((position) => { const stopTrigger = position.direction === 'SHORT' ? position.stop : position.stop; const targetTrigger = position.target; return <article className="panel paper-position" key={position.id}><div className="paper-position-head"><div><strong>{position.symbol}</strong><span className={position.direction === 'SHORT' ? 'negative' : 'positive'}>{position.direction} · {position.quantity}</span></div><div className="paper-live-result"><strong className={(position.unrealized_pnl ?? 0) >= 0 ? 'positive' : 'negative'}>{position.unrealized_pnl === null ? '--' : `${position.unrealized_pnl >= 0 ? '+' : ''}${money(position.unrealized_pnl)} USDT`}</strong><span>{position.mark_price ? `Mark ${money(position.mark_price)}` : 'Sem cotação'}</span></div></div><div className="paper-metrics"><div><small>Entrada</small><b>{money(position.entry_price)}</b></div><div><small>Preço atual</small><b>{position.mark_price ? money(position.mark_price) : '--'}</b></div><div><small>Saída automática</small><b>{position.direction === 'SHORT' ? `Stop ${money(stopTrigger)}` : `Stop ${money(stopTrigger)}`}</b><em>ou alvo {money(targetTrigger)}</em></div></div><div className="paper-close"><button className="button-secondary paper-close-market" type="button" disabled={saving || position.mark_price === null} onClick={() => void closePosition(position)}><X size={15} /> Fechar a mercado <span>{position.mark_price ? money(position.mark_price) : 'sem preço'}</span></button></div></article>; })}</div>}</section>
    </div>
    <div className="paper-note"><ArrowUpFromLine size={16} /><span>LONG usa alta como resultado positivo; SHORT usa queda como resultado positivo.</span><ArrowDownToLine size={16} /></div>
    <PaperHistorySection history={history} historyLoading={historyLoading} money={money} date={date} onPage={(page) => void loadHistory(page)} />
  </PageFrame>;
}