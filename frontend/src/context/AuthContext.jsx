import { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/axios';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('user');
    const tokens = localStorage.getItem('tokens');
    if (stored && tokens) {
      setUser(JSON.parse(stored));
      // Verify token is still valid
      api.get('/auth/me/')
        .then(res => {
          setUser(res.data);
          localStorage.setItem('user', JSON.stringify(res.data));
        })
        .catch(() => {
          logout();
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (username, password) => {
    const res = await api.post('/auth/login/', { username, password });
    localStorage.setItem('tokens', JSON.stringify(res.data));
    const meRes = await api.get('/auth/me/');
    setUser(meRes.data);
    localStorage.setItem('user', JSON.stringify(meRes.data));
    return meRes.data;
  };

  const register = async (data) => {
    const res = await api.post('/auth/register/', data);
    return res.data;
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('tokens');
    localStorage.removeItem('user');
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
