import { useEffect, useState } from 'react';
import { Activity, ArrowLeft, RefreshCw } from 'lucide-react';
import { getPaperTradeEvents, type PaperTradeEvent } from '../api';
import { NoticeStack, PageFrame, type Notice } from '../components';

const date = (value: number) => new Date(value).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'medium' });

export function PaperAuditScreen({ token, session, onLogout }: { token: string; session: { sub: string; role: string }; onLogout: () => void }) {
  const tradeId = Number(new URLSearchParams(window.location.search).get('trade_id'));
  const [events, setEvents] = useState<PaperTradeEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<Notice | null>(null);

  useEffect(() => {
    if (!tradeId) { setNotice({ type: 'info', title: 'Trade não selecionado', message: 'Informe trade_id na tela de auditoria.' }); setLoading(false); return; }
    getPaperTradeEvents(token, tradeId).then((response) => setEvents(response.events)).catch((error) => setNotice({ type: 'error', title: 'Auditoria indisponível', message: error instanceof Error ? error.message : 'Não foi possível carregar os eventos.' })).finally(() => setLoading(false));
  }, [token, tradeId]);

  return <PageFrame session={session} onLogout={onLogout} eyebrow="Operação / trilha auditável" title={`Auditoria do trade #${tradeId || '--'}`} description="Sequência imutável de eventos registrada pelo Paper Trading.">
    <NoticeStack notices={notice ? [notice] : []} onDismiss={() => setNotice(null)} />
    <div className="page-actions"><a className="button-secondary" href="/paper"><ArrowLeft size={15} /> Voltar ao Paper</a><span className="registry-summary"><Activity size={15} /> {events.length} eventos</span></div>
    {loading ? <div className="empty-state"><RefreshCw className="spin" size={25} /><p>Carregando trilha de eventos...</p></div> : !events.length ? <div className="empty-state panel"><Activity size={28} /><h2>Nenhum evento registrado</h2><p>Este trade ainda não possui uma trilha disponível.</p></div> : <section className="paper-event-timeline page-panel">{events.map((event) => <article className="paper-event" key={event.id}><span className="paper-event-dot" /><div><strong>{event.event_type}</strong><small>{date(event.event_time)} · {event.payload.exit_reason ? String(event.payload.exit_reason) : 'evento de abertura'}</small><code>{JSON.stringify(event.payload)}</code></div></article>)}</section>}
  </PageFrame>;
}