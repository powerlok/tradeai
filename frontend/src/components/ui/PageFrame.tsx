import type { ReactNode } from 'react';
import { Sidebar } from '../Sidebar';
import { LogOut } from 'lucide-react';
import { NotificationCenter } from '../NotificationCenter';

export function PageFrame({ session, onLogout, eyebrow, title, description, children }: { session: { sub: string; role: string }; onLogout: () => void; eyebrow: string; title: string; description?: string; children: ReactNode }) {
  return <div className="app-shell"><Sidebar /><main className="content"><header className="topbar"><div><div className="kicker">{eyebrow}</div><h1>{title}</h1>{description && <p className="page-description">{description}</p>}</div><div className="user-area"><span className="live-dot" /><span>{session.sub} · {session.role}</span><NotificationCenter token={localStorage.getItem('trading_access_token') || ''} /><button className="icon-button" title="Sair" onClick={onLogout}><LogOut size={17} /></button></div></header>{children}</main></div>;
}
