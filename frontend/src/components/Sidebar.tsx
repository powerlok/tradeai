import { useState } from 'react';
import { Activity, BarChart3, CandlestickChart, FlaskConical, PanelLeftClose, PanelLeftOpen, ShieldCheck, History } from 'lucide-react';

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('trade_sidebar_collapsed') === 'true');
  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem('trade_sidebar_collapsed', String(next));
  };

  return <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
    <div className="sidebar-head"><div className="brand"><span className="brand-mark"><Activity size={19} /></span><span className="sidebar-text">trade<span className="brand-accent">ai</span></span></div><button className="collapse-button" onClick={toggle} title={collapsed ? 'Expandir menu' : 'Recolher menu'} aria-label={collapsed ? 'Expandir menu' : 'Recolher menu'}>{collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}</button></div>
    <div className="nav-label sidebar-text">Workspace</div>
    <a className="nav-item active" href="/dashboard"><BarChart3 size={17} /><span className="sidebar-text">Market desk</span></a>
    <a className="nav-item" href="/dashboard#price-action"><CandlestickChart size={17} /><span className="sidebar-text">Price action</span></a>
    <a className="nav-item" href="/dashboard#indicators"><Activity size={17} /><span className="sidebar-text">Indicators</span></a>
    <div className="nav-label sidebar-text">Research</div>
    <a className={`nav-item ${window.location.pathname === '/strategy' ? 'active' : ''}`} href="/strategy"><FlaskConical size={17} /><span className="sidebar-text">Strategy lab</span></a>
    <a className={`nav-item ${window.location.pathname === '/models' ? 'active' : ''}`} href="/models"><History size={17} /><span className="sidebar-text">Model registry</span></a>
    <div className="sidebar-footer"><ShieldCheck size={16} /><span className="sidebar-text">paper mode active</span></div>
  </aside>;
}
