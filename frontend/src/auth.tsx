import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { api, errorMessage, session, type User } from './api';

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}
const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const logout = useCallback(() => {
    session.clear();
    setUser(null);
    setError('');
  }, []);

  const refresh = useCallback(async () => {
    const token = session.get();
    if (!token) { setUser(null); setLoading(false); return; }
    setError('');
    try {
      const current = await api.me();
      if (session.get() === token) setUser(current);
    } catch (err) {
      if (session.get() === token) setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const expired = () => { logout(); setError('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.'); };
    const focus = () => { void refresh(); };
    window.addEventListener('microshop:unauthorized', expired);
    window.addEventListener('focus', focus);
    void refresh();
    return () => {
      window.removeEventListener('microshop:unauthorized', expired);
      window.removeEventListener('focus', focus);
    };
  }, [refresh, logout]);

  const login = async (email: string, password: string) => {
    const result = await api.login(email, password);
    session.set(result.access_token);
    try {
      const current = await api.me();
      setUser(current);
      setError('');
    } catch (err) {
      logout();
      throw err;
    }
  };

  return <AuthContext.Provider value={{ user, loading, error, refresh, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('AuthProvider is required');
  return context;
}
