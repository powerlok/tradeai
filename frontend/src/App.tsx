import { useEffect, useState } from 'react';
import { LoginScreen, MarketChat } from './components';
import { useAuth } from './hooks/useAuth';
import { DashboardScreen } from './screens/DashboardScreen';
import { ModelsScreen } from './screens/ModelsScreen';
import { StrategyScreen } from './screens/StrategyScreen';

export default function App() {
  const auth = useAuth();
  const [loginError, setLoginError] = useState('');
  const [chatOpen, setChatOpen] = useState(false);
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const handlePopState = () => setPath(window.location.pathname);
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  if (!auth.loggedIn) {
    return <LoginScreen error={loginError} onSubmit={(event, username, password) => auth.signIn(event, username, password, setLoginError)} />;
  }

  const globalChatContext = {
    symbol: 'AUTO',
    timeframe: '1h',
    signal: null,
    lastPrice: null,
    spread: null,
    marketState: 'o ativo será identificado pela pergunta do usuário',
  };

  const screen = path === '/strategy'
    ? <StrategyScreen token={auth.token} session={auth.session!} onLogout={auth.signOut} />
    : path === '/models'
      ? <ModelsScreen token={auth.token} session={auth.session!} onLogout={auth.signOut} />
      : <DashboardScreen token={auth.token} session={auth.session!} onLogout={auth.signOut} />;

  if (!['/', '/dashboard', '/dashboard/', '/strategy', '/models'].includes(path)) {
    window.history.replaceState({}, '', '/dashboard');
    setPath('/dashboard');
  }

  return (
    <>
      {screen}
      <MarketChat
        token={auth.token}
        symbol={globalChatContext.symbol}
        timeframe={globalChatContext.timeframe}
        signal={globalChatContext.signal}
        lastPrice={globalChatContext.lastPrice}
        spread={globalChatContext.spread}
        marketState={globalChatContext.marketState}
        open={chatOpen}
        onToggle={() => setChatOpen((current) => !current)}
      />
    </>
  );
}
