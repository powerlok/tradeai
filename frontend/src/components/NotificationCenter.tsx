import { AlertTriangle, Bell, CheckCircle2, Info, Trash2, TrendingUp, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { clearNotifications, deleteNotification, getNotifications, type AppNotification } from '../api';

function iconFor(type: AppNotification['type']) {
  return type === 'trend_change' ? <TrendingUp size={15} /> : type === 'opportunity_alert' ? <AlertTriangle size={15} /> : type === 'chat_response' ? <CheckCircle2 size={15} /> : <Info size={15} />;
}

export function NotificationCenter({ token }: { token: string }) {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [open, setOpen] = useState(false);
  const [toast, setToast] = useState<AppNotification | null>(null);
  const knownIds = useRef(new Set<string>());
  const initialized = useRef(false);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const result = await getNotifications(token);
        if (!active) return;
        const incoming = result.notifications;
        const newNotification = initialized.current ? incoming.find((item) => !knownIds.current.has(item.id)) : null;
        incoming.forEach((item) => knownIds.current.add(item.id));
        setNotifications(incoming);
        if (newNotification) {
          setToast(newNotification);
          window.setTimeout(() => setToast((current) => current?.id === newNotification.id ? null : current), 6000);
        }
        initialized.current = true;
      } catch {
        // Notification delivery is optional and must not affect the application shell.
      }
    }
    load();
    const interval = window.setInterval(load, 5000);
    return () => { active = false; window.clearInterval(interval); };
  }, [token]);

  async function dismiss(id: string) {
    setNotifications((current) => current.filter((item) => item.id !== id));
    setToast((current) => current?.id === id ? null : current);
    try { await deleteNotification(token, id); } catch { /* Keep the local dismissal if the server is temporarily unavailable. */ }
  }

  async function clearAll() {
    setNotifications([]);
    setToast(null);
    try { await clearNotifications(token); } catch { /* Keep the local clear if the server is temporarily unavailable. */ }
  }

  return (
    <>
      <div className="notification-center">
        <button type="button" className="notification-bell" onClick={() => setOpen((current) => !current)} aria-label="Abrir notificações" title="Notificações">
          <Bell size={17} />
          {notifications.length > 0 && <span className="notification-count">{notifications.length > 9 ? '9+' : notifications.length}</span>}
        </button>
        {open && <div className="notification-popover" role="dialog" aria-label="Notificações">
          <div className="notification-popover-head"><div><span className="chat-kicker">Activity feed</span><strong>Notificações</strong></div><div className="notification-popover-actions">{notifications.length > 0 && <button type="button" className="notification-close" onClick={() => void clearAll()} aria-label="Limpar todas as notificações" title="Limpar todas"><Trash2 size={15} /></button>}<button type="button" className="notification-close" onClick={() => setOpen(false)} aria-label="Fechar notificações"><X size={15} /></button></div></div>
          <div className="notification-list">
            {notifications.length === 0 ? <div className="notification-empty">Nenhuma notificação nova.</div> : notifications.map((item) => <article className={`notification-item ${item.type}`} key={item.id}><span className="notification-item-icon">{iconFor(item.type)}</span><div><strong>{item.title}</strong><p>{item.message}</p><time>{new Date(item.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</time></div><button type="button" className="notification-dismiss" onClick={() => dismiss(item.id)} aria-label={`Remover ${item.title}`}><X size={13} /></button></article>)}
          </div>
        </div>}
      </div>
      {toast && <div className={`notification-toast ${toast.type}`} role="status"><span className="notification-item-icon">{iconFor(toast.type)}</span><div><strong>{toast.title}</strong><p>{toast.message}</p>{toast.metadata && typeof toast.metadata.viability_summary === 'string' && <p className="notification-viability">{String(toast.metadata.viability_summary)}</p>}</div><button type="button" className="notification-dismiss" onClick={() => setToast(null)} aria-label="Fechar notificação"><X size={14} /></button></div>}
    </>
  );
}
