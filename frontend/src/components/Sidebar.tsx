import { useState } from 'react';
import { Activity, BarChart3, FlaskConical, PanelLeftClose, PanelLeftOpen, ShieldCheck, History } from 'lucide-react';

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('trade_sidebar_collapsed') === 'true');
  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem('trade_sidebar_collapsed', String(next));
  };

  function navigate(event: React.MouseEvent<HTMLAnchorElement>) {
    const href = event.currentTarget.getAttribute('href');
    if (!href || !href.startsWith('/')) return;
    event.preventDefault();
    window.history.pushState({}, '', href);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }

  return <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
    <div className="sidebar-head"><div className="brand"><span className="brand-mark"><Activity size={19} /></span><span className="sidebar-text">trade<span className="brand-accent">ai</span></span></div><button className="collapse-button" onClick={toggle} title={collapsed ? 'Expandir menu' : 'Recolher menu'} aria-label={collapsed ? 'Expandir menu' : 'Recolher menu'}>{collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}</button></div>
    <div className="nav-label sidebar-text">Workspace</div>
    <a className="nav-item active" href="/dashboard" onClick={navigate}><BarChart3 size={17} /><span className="sidebar-text">Market desk</span></a>
    <div className="nav-label sidebar-text">Research</div>
    <a className={`nav-item ${window.location.pathname === '/strategy' ? 'active' : ''}`} href="/strategy" onClick={navigate}><FlaskConical size={17} /><span className="sidebar-text">Strategy lab</span></a>
    <a className={`nav-item ${window.location.pathname === '/models' ? 'active' : ''}`} href="/models" onClick={navigate}><History size={17} /><span className="sidebar-text">Model registry</span></a>
    <div className="sidebar-footer"><ShieldCheck size={16} /><span className="sidebar-text">paper mode active</span></div>
  </aside>;
}
