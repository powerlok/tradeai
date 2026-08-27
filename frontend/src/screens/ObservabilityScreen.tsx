import { useEffect, useState } from 'react';
import { Activity, AlertTriangle, CheckCircle2, Clock3, RefreshCw, Server, WifiOff } from 'lucide-react';
import { getHealth, getObservabilityEvents, type HealthStatus, type ObservabilityEvent } from '../api';
import { DashboardSkeleton, NoticeStack, PageFrame, type Notice } from '../components';

function formatTime(value: number) {
  return new Date(value * 1000).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function statusClass(status: number) {
  if (status >= 500) return 'log-status log-danger';
  if (status >= 400) return 'log-status log-warn';
  return 'log-status log-ok';
}

const flowNodes = [
  { id: 'gateway', label: 'Entrada', detail: 'HTTP / proxy', match: ['/api/'] },
  { id: 'auth', label: 'Auth', detail: 'JWT / RBAC', match: ['/api/auth'] },
  { id: 'market', label: 'Mercado', detail: 'Binance / MCP', match: ['/api/market', '/api/opportunities', '/api/news'] },
  { id: 'ai', label: 'IA', detail: 'Ollama / Groq', match: ['/api/chat', 'model_error'] },
  { id: 'risk', label: 'Risk / Paper', detail: 'decisão e execução', match: ['/api/paper', '/api/operational'] },
  { id: 'dashboard', label: 'Dashboard', detail: 'telemetria', match: ['/api/observability'] },
];

function nodeActivity(node: typeof flowNodes[number], events: ObservabilityEvent[]) {
  return events.some((event) => node.match.some((term) => event.event === term || event.path?.startsWith(term)));
}

export function ObservabilityScreen({ token, session, onLogout }: { token: string; session: { sub: string; role: string }; onLogout: () => void }) {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [events, setEvents] = useState<ObservabilityEvent[]>([]);
  const [filter, setFilter] = useState<'all' | 'errors' | 'slow'>('all');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [notices, setNotices] = useState<Notice[]>([]);

  async function load(showSpinner = false) {
    if (showSpinner) setRefreshing(true);
    try {
      const [nextHealth, nextEvents] = await Promise.all([getHealth(token), getObservabilityEvents(token, 150)]);
      setHealth(nextHealth);
      setEvents(nextEvents.events);
      setLastUpdated(new Date());
    } catch (error) {
      setNotices([{ type: 'error', title: 'Observabilidade indisponível', message: error instanceof Error ? error.message : 'Não foi possível carregar a observabilidade.' }]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(timer);
  }, [token]);

  const visibleEvents = events.filter((event) => filter === 'errors' ? event.event === 'model_error' || (event.status_code ?? 200) >= 400 : filter === 'slow' ? (event.duration_ms ?? 0) >= 500 : true);
  const errorCount = events.filter((event) => event.event === 'model_error' || (event.status_code ?? 200) >= 400).length;
  const slowCount = events.filter((event) => (event.duration_ms ?? 0) >= 500).length;
  const operational = health?.operational_state;
  const activeNode = visibleEvents[0] ? flowNodes.find((node) => nodeActivity(node, [visibleEvents[0]]))?.id : undefined;

  return <PageFrame session={session} onLogout={onLogout} eyebrow="Operations / live telemetry" title="Observability" description="Acompanhe a saúde do stack e o caminho real das requisições enquanto a aplicação trabalha.">
    <NoticeStack notices={notices} onDismiss={(index) => setNotices((current) => current.filter((_, itemIndex) => itemIndex !== index))} />
    {loading ? <DashboardSkeleton /> : <>
      <section className="flow-panel" aria-label="Fluxo operacional em tempo real">
        <div className="flow-panel-head"><div><span className="card-label">Live trace</span><h2>Fluxo ponta a ponta</h2></div><span className="flow-live"><i /> atualizado em tempo real</span></div>
        <div className="flow-map">{flowNodes.map((node, index) => <div className="flow-step" key={node.id}><button type="button" className={`flow-node ${activeNode === node.id ? 'flow-active' : ''}`} onClick={() => setFilter(node.id === 'ai' ? 'errors' : 'all')} title={`Filtrar atividade de ${node.label}`}><span className="flow-node-dot" /><strong>{node.label}</strong><small>{node.detail}</small></button>{index < flowNodes.length - 1 && <div className="flow-connector"><span className="flow-packet packet-one" /><span className="flow-packet packet-two" /></div>}</div>)}</div>
      </section>
      <div className="observability-toolbar"><div><span className="updated">Atualização automática a cada 5s{lastUpdated ? ` · ${lastUpdated.toLocaleTimeString('pt-BR')}` : ''}</span></div><button className="button-secondary" onClick={() => void load(true)} disabled={refreshing}><RefreshCw size={15} className={refreshing ? 'spin' : ''} /> Atualizar</button></div>
      <section className="observability-grid">
        <article className="obs-card obs-primary"><div className="obs-card-head"><span className="card-label">API</span><Server size={18} /></div><strong>{health?.status === 'ok' ? 'Operacional' : 'Indisponível'}</strong><span>backend · health endpoint</span></article>
        <article className={`obs-card ${operational?.state === 'KILL_SWITCH' ? 'obs-danger' : 'obs-primary'}`}><div className="obs-card-head"><span className="card-label">Modo</span><Activity size={18} /></div><strong>{operational?.state ?? 'unknown'}</strong><span>{operational?.entry_enabled ? 'entradas habilitadas' : 'entradas bloqueadas'}</span></article>
        <article className={`obs-card ${health?.ai_connected ? 'obs-primary' : 'obs-warn'}`}><div className="obs-card-head"><span className="card-label">AI provider</span>{health?.ai_connected ? <CheckCircle2 size={18} /> : <WifiOff size={18} />}</div><strong>{health?.ai_connected ? 'Conectado' : 'Offline'}</strong><span>{health?.ai_provider} · {health?.ai_model}</span></article>
        <article className={`obs-card ${errorCount ? 'obs-danger' : 'obs-primary'}`}><div className="obs-card-head"><span className="card-label">Janela atual</span><AlertTriangle size={18} /></div><strong>{errorCount} falhas</strong><span>{slowCount} requisições lentas</span></article>
      </section>
      <section className="page-panel observability-panel"><div className="observability-panel-head"><div><span className="card-label">Request stream</span><h2>Eventos recentes</h2></div><div className="segmented"><button className={filter === 'all' ? 'selected' : ''} onClick={() => setFilter('all')}>Todos {events.length}</button><button className={filter === 'errors' ? 'selected' : ''} onClick={() => setFilter('errors')}>Falhas {errorCount}</button><button className={filter === 'slow' ? 'selected' : ''} onClick={() => setFilter('slow')}>Lentos {slowCount}</button></div></div><div className="observability-table"><div className="log-row log-head"><span>Hora</span><span>Evento / rota</span><span>Status</span><span>Latência</span><span>Correlation ID</span></div>{visibleEvents.length === 0 ? <div className="empty-state"><Clock3 size={22} /><p>Nenhum evento nesta janela.</p></div> : visibleEvents.map((event, index) => <div className="log-row" key={`${event.correlation_id}-${index}`}><span className="log-time">{formatTime(event.timestamp)}</span><span className="log-route">{event.event === 'model_error' ? <><b className="log-error-label">MODEL ERROR</b> {event.message} {event.provider ? `(${event.provider})` : ''}{event.error ? ` · ${event.error}` : ''}</> : <><b>{event.method}</b> {event.path}</>}</span><span className={statusClass(event.status_code ?? (event.event === 'model_error' ? 500 : 200))}>{event.event === 'model_error' ? 'ERR' : event.status_code}</span><span className="log-time">{event.duration_ms != null ? `${event.duration_ms} ms` : 'n/a'}</span><code>{event.correlation_id}</code></div>)}</div></section>
      {!health?.ai_connected && health?.ai_error && <div className="observability-note"><AlertTriangle size={16} /><span>Provider de IA reportado pelo health: {health.ai_error}. A API está viva, mas o chat pode não gerar resposta.</span></div>}
    </>}
  </PageFrame>;
}
