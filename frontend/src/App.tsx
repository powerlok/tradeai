import { useState } from 'react';
import { LoginScreen } from './components';
import { useAuth } from './hooks/useAuth';
import { DashboardScreen } from './screens/DashboardScreen';
import { ModelsScreen } from './screens/ModelsScreen';
import { StrategyScreen } from './screens/StrategyScreen';

export default function App() {
  const auth = useAuth();
  const [loginError, setLoginError] = useState('');

  if (!auth.loggedIn) {
    return <LoginScreen error={loginError} onSubmit={(event, username, password) => auth.signIn(event, username, password, setLoginError)} />;
  }

  const path = window.location.pathname;
  if (path === '/strategy') return <StrategyScreen token={auth.token} session={auth.session!} onLogout={auth.signOut} />;
  if (path === '/models') return <ModelsScreen token={auth.token} session={auth.session!} onLogout={auth.signOut} />;
  if (!['/', '/dashboard', '/dashboard/'].includes(path)) window.history.replaceState({}, '', '/dashboard');
  return <DashboardScreen token={auth.token} session={auth.session!} onLogout={auth.signOut} />;
}
