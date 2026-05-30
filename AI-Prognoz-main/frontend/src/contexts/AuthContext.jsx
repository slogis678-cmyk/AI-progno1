import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { api, tokenStore } from '@/lib/api';

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined); // undefined = loading
  const [error, setError] = useState(null);

  const fetchMe = useCallback(async () => {
    const t = tokenStore.get();
    if (!t) {
      setUser(null);
      return;
    }
    try {
      const { data } = await api.get('/auth/me');
      setUser(data);
    } catch {
      tokenStore.clear();
      setUser(null);
    }
  }, []);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  const login = async (email, password) => {
    setError(null);
    const { data } = await api.post('/auth/login', { email, password });
    tokenStore.set(data.token);
    setUser(data.user);
    return data.user;
  };

  const register = async (email, password, full_name) => {
    setError(null);
    const { data } = await api.post('/auth/register', { email, password, full_name });
    tokenStore.set(data.token);
    setUser(data.user);
    return data.user;
  };

  const logout = () => {
    tokenStore.clear();
    setUser(null);
    window.location.href = '/login';
  };

  const updatePreferredModel = async (preferred_model) => {
    const { data } = await api.patch('/auth/preferences', { preferred_model });
    setUser(data);
    return data;
  };

  return (
    <AuthCtx.Provider value={{ user, error, login, register, logout, updatePreferredModel, refresh: fetchMe }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
