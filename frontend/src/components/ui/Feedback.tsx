import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { useEffect } from 'react';

export type Notice = { type: 'error' | 'success' | 'info'; title: string; message: string };

export function NoticeStack({ notices, onDismiss }: { notices: Notice[]; onDismiss: (index: number) => void }) {
  return <div className="notice-stack" aria-live="polite">{notices.map((notice, index) => <div className={`notice ${notice.type}`} key={`${notice.title}-${index}`}><span className="notice-icon">{notice.type === 'error' ? <AlertTriangle size={17} /> : notice.type === 'success' ? <CheckCircle2 size={17} /> : <Info size={17} />}</span><div><strong>{notice.title}</strong><p>{notice.message}</p></div><button className="notice-close" onClick={() => onDismiss(index)} aria-label="Fechar aviso"><X size={15} /></button></div>)}</div>;
}

export function useAutoDismiss(notice: Notice | null, onDismiss: () => void) {
  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(onDismiss, 5000);
    return () => window.clearTimeout(timeout);
  }, [notice, onDismiss]);
}

export function Skeleton({ className = '' }: { className?: string }) { return <div className={`skeleton ${className}`} aria-hidden="true" />; }
export function DashboardSkeleton() { return <div className="skeleton-page"><div className="skeleton-row"><Skeleton className="skeleton-title" /><Skeleton className="skeleton-meta" /></div><div className="skeleton-cards"><Skeleton /><Skeleton /><Skeleton /></div><Skeleton className="skeleton-chart" /><div className="skeleton-cards"><Skeleton /><Skeleton /><Skeleton /></div></div>; }

export function ConfirmModal({ title, message, confirmLabel = 'Confirmar', onConfirm, onCancel }: { title: string; message: string; confirmLabel?: string; onConfirm: () => void; onCancel: () => void }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onCancel()}><div className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div className="modal-kicker">Confirmação necessária</div><h2 id="modal-title">{title}</h2><p>{message}</p><div className="modal-actions"><button className="button-secondary" onClick={onCancel}>Cancelar</button><button className="button-primary" onClick={onConfirm}>{confirmLabel}</button></div></div></div>;
}
