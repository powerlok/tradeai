import { CircleDollarSign } from 'lucide-react';
import type { PaperHistory } from '../api';

type Props = {
  history: PaperHistory | null;
  historyLoading: boolean;
  money: (value: number) => string;
  date: (value: number) => string;
  onPage: (page: number) => void;
};

export function PaperHistorySection({ history, historyLoading, money, date, onPage }: Props) {
  return <section className="paper-history">
    <div className="paper-section-head"><div><div className="card-label">Performance realizada</div><h2>Histórico de trades</h2></div><span>{history?.total ?? 0} encerrados</span></div>
    <div className="paper-history-summary"><div><small>PnL realizado</small><strong className={(history?.summary.realized_pnl ?? 0) >= 0 ? 'positive' : 'negative'}>{(history?.summary.realized_pnl ?? 0) >= 0 ? '+' : ''}{money(history?.summary.realized_pnl ?? 0)} USDT</strong></div><div><small>Trades vencedores</small><strong>{history?.summary.winning_trades ?? 0}</strong></div><div><small>Trades perdedores</small><strong>{history?.summary.losing_trades ?? 0}</strong></div></div>
    {historyLoading ? <div className="empty-state panel">Carregando histórico...</div> : !history?.trades.length ? <div className="empty-state panel"><CircleDollarSign size={26} /><h2>Nenhum trade encerrado</h2><p>Os resultados realizados aparecerão aqui após o fechamento das posições.</p></div> : <><div className="paper-history-table"><div className="paper-history-row paper-history-header"><span>Trade</span><span>Entrada / saída</span><span>Resultado</span><span>Encerramento</span><span>Ações</span></div>{history.trades.map((trade) => <div className="paper-history-row" key={trade.id}><span><strong>{trade.symbol}</strong><small>{trade.direction} · {trade.quantity}</small></span><span><strong>{money(trade.entry_price)}</strong><small>{trade.exit_price ? `saída ${money(trade.exit_price)}` : '--'}</small></span><span className={((trade.pnl ?? 0) >= 0) ? 'positive' : 'negative'}>{(trade.pnl ?? 0) >= 0 ? '+' : ''}{money(trade.pnl ?? 0)} USDT</span><span>{trade.closed_at ? date(trade.closed_at) : '--'}</span><a className="paper-audit-link" href={`/paper/audit?trade_id=${trade.id}`}>Ver auditoria</a></div>)}</div><div className="paper-pagination"><button className="button-secondary" type="button" disabled={history.page <= 1 || historyLoading} onClick={() => onPage(history.page - 1)}>Anterior</button><span>Página {history.page} de {history.pages}</span><button className="button-secondary" type="button" disabled={history.page >= history.pages || historyLoading} onClick={() => onPage(history.page + 1)}>Próxima</button></div></>}
  </section>;
}
