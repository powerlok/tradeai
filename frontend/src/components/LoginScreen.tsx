import { useState } from 'react';
import type { FormEvent } from 'react';
import { Activity, ArrowUpRight, ShieldCheck } from 'lucide-react';

export function LoginScreen({ onSubmit, error }: { onSubmit: (event: FormEvent, username: string, password: string) => void; error: string }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  return <div className="login-shell"><div className="login-art"><div className="art-grid" /><div className="art-copy"><div className="brand"><span className="brand-mark"><Activity size={19} /></span><span>trade<span className="brand-accent">ai</span></span></div><h1>A sharper view<br />of the market.</h1><p>Signal intelligence for deliberate decisions.</p></div><div className="ticker"><span>BTCUSDT</span><strong>live market data</strong><span>●</span></div></div><div className="login-pane"><div className="login-box"><div className="kicker">Secure workspace</div><h2>Welcome back</h2><p className="login-subtitle">Sign in to your market desk.</p><form onSubmit={(event) => onSubmit(event, username, password)}><label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" autoFocus /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" /></label>{error && <div className="error-text">{error}</div>}<button className="login-submit" type="submit">Enter workspace <ArrowUpRight size={17} /></button></form><div className="login-footer"><ShieldCheck size={14} /> JWT protected · paper mode</div></div></div></div>;
}
