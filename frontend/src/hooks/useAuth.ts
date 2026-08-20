import { useState } from 'react';
import type { FormEvent } from 'react';
import { login } from '../api';
import { parseToken } from '../lib/format';

const TOKEN_KEY = 'trading_access_token';

export function useAuth() {
  const [token, setToken] = useState(localStorage.getItem(TOKEN_KEY) || '');
  const session = token ? parseToken(token) : null;
  const loggedIn = Boolean(session?.exp * 1000 > Date.now());

  async function signIn(event: FormEvent, username: string, password: string, onError: (message: string) => void) {
    event.preventDefault();
    onError('');
    try {
      const result = await login(username.trim(), password);
      localStorage.setItem(TOKEN_KEY, result.access_token);
      setToken(result.access_token);
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Credenciais inválidas');
    }
  }

  function signOut() {
    localStorage.removeItem(TOKEN_KEY);
    setToken('');
  }

  return { token, session, loggedIn, signIn, signOut };
}
