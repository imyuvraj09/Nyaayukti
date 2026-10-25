import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getCurrentUser, loginAccount, logoutAccount, registerAccount } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    setLoading(true);
    const result = await getCurrentUser();
    setUser(result.success ? result.user : null);
    setLoading(false);
    return result.success ? result.user : null;
  }, []);

  useEffect(() => {
    void getCurrentUser().then((result) => {
      setUser(result.success ? result.user : null);
      setLoading(false);
    });

    const handleExpired = () => {
      setUser(null);
      setLoading(false);
    };
    const handleStorage = (event) => {
      if (event.key === 'nyaayukti_auth_change') refreshUser();
    };

    window.addEventListener('nyaayukti-auth-expired', handleExpired);
    window.addEventListener('storage', handleStorage);
    return () => {
      window.removeEventListener('nyaayukti-auth-expired', handleExpired);
      window.removeEventListener('storage', handleStorage);
    };
  }, [refreshUser]);

  const signIn = useCallback(async (credentials) => {
    const result = await loginAccount(credentials);
    if (result.success) {
      setUser(result.user);
      try {
        localStorage.setItem('nyaayukti_auth_change', String(Date.now()));
      } catch {}
    }
    return result;
  }, []);

  const register = useCallback(async (details) => {
    const result = await registerAccount(details);
    if (result.success) {
      setUser(result.user);
      try {
        localStorage.setItem('nyaayukti_auth_change', String(Date.now()));
      } catch {}
    }
    return result;
  }, []);

  const signOut = useCallback(async () => {
    const result = await logoutAccount();
    if (!result.success) return result;
    try {
      localStorage.setItem('nyaayukti_auth_change', String(Date.now()));
    } catch {}
    setUser(null);
    try {
      localStorage.removeItem('nyaayukti_active_session_id');
    } catch {}
    return result;
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: !!user,
      signIn,
      register,
      signOut,
      refreshUser,
    }),
    [user, loading, signIn, register, signOut, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// oxlint-disable-next-line react/only-export-components -- shared auth module, no module-local mutable state
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
