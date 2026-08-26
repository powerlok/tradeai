import { useEffect, useMemo, useState } from 'react';
import { ArrowUpRight, Clock3, Newspaper, RefreshCw } from 'lucide-react';
import { getNews, type NewsItem } from '../api';
import { DashboardSkeleton, NoticeStack, PageFrame, type Notice } from '../components';

function formatPublishedAt(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || 'Data não informada';
  return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(date).replace('.', '');
}

function sourceClass(source: string) {
  return source.toLowerCase().replace(/\s+/g, '-');
}

export function NewsScreen({ token, session, onLogout }: { token: string; session: { sub: string; role: string }; onLogout: () => void }) {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [sourceFilter, setSourceFilter] = useState('Todas');
  const [notice, setNotice] = useState<Notice | null>(null);

  async function load(manual = false) {
    if (manual) setRefreshing(true); else setLoading(true);
    try {
      setNews((await getNews(token)).news);
      setNotice(null);
    } catch (error) {
      setNotice({ type: 'error', title: 'Notícias indisponíveis', message: error instanceof Error ? error.message : 'Não foi possível atualizar as fontes agora.' });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => { void load(); }, [token]);

  const sources = useMemo(() => ['Todas', ...Array.from(new Set(news.map((item) => item.source)))], [news]);
  const filteredNews = sourceFilter === 'Todas' ? news : news.filter((item) => item.source === sourceFilter);
  const lead = filteredNews[0];
  const remaining = filteredNews.slice(1);

  return <PageFrame session={session} onLogout={onLogout} eyebrow="Pesquisa / boletim ao vivo" title="Notícias cripto" description="As últimas manchetes do mercado cripto, reunidas de fontes públicas e organizadas para leitura rápida.">
    <NoticeStack notices={notice ? [notice] : []} onDismiss={() => setNotice(null)} />
    <div className="news-toolbar">
      <div className="news-source-tabs" role="tablist" aria-label="Filtrar por fonte">
        {sources.map((source) => <button key={source} type="button" className={sourceFilter === source ? 'selected' : ''} onClick={() => setSourceFilter(source)}>{source}</button>)}
      </div>
      <button className="button-secondary news-refresh" type="button" onClick={() => void load(true)} disabled={loading || refreshing}><RefreshCw size={15} className={refreshing ? 'spin' : ''} /> {refreshing ? 'Atualizando' : 'Atualizar'}</button>
    </div>
    {loading ? <DashboardSkeleton /> : !lead ? <div className="empty-state panel"><Newspaper size={28} /><h2>Nenhuma notícia disponível</h2><p>As fontes RSS não retornaram manchetes neste momento. Tente atualizar em instantes.</p></div> : <>
      <section className="news-lead panel">
        <div className="news-lead-copy"><div className="news-meta"><span className={`news-source ${sourceClass(lead.source)}`}>{lead.source}</span><span><Clock3 size={13} /> {formatPublishedAt(lead.published_at)}</span></div><h2>{lead.title}</h2><p>Manchete em destaque no radar cripto. Leia a matéria completa na fonte original.</p><a className="news-link" href={lead.url} target="_blank" rel="noreferrer">Ler matéria <ArrowUpRight size={16} /></a></div>
        <div className="news-lead-mark"><Newspaper size={34} /><span>LIVE<br />BRIEF</span></div>
      </section>
      <div className="news-section-heading"><div><div className="kicker">Últimas notícias</div><h2>O que está movimentando o mercado</h2></div><span>{filteredNews.length} manchetes</span></div>
      <section className="news-grid">{remaining.map((item) => <article className="news-card panel" key={`${item.source}-${item.url}`}><div className="news-meta"><span className={`news-source ${sourceClass(item.source)}`}>{item.source}</span><span><Clock3 size={13} /> {formatPublishedAt(item.published_at)}</span></div><h3>{item.title}</h3><a className="news-link" href={item.url} target="_blank" rel="noreferrer">Abrir fonte <ArrowUpRight size={15} /></a></article>)}</section>
    </>}
    <div className="news-footnote"><Newspaper size={14} /> Fontes públicas: CoinDesk, Cointelegraph e Decrypt · atualização sob demanda · títulos conforme a fonte original</div>
  </PageFrame>;
}