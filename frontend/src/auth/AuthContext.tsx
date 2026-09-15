import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { AuthUser, Project, UserRole } from '../types';
import { api } from '../services/api';
import {
  clearAuth,
  getStoredUser,
  setStoredUser,
  setToken,
} from '../services/authStore';

interface AuthContextValue {
  user: AuthUser | null;
  projects: Project[];
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isAdmin: boolean;
  canWrite: boolean;
  hasRole: (roles: UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const bootstrap = async () => {
      const stored = getStoredUser();
      if (!stored) {
        setLoading(false);
        return;
      }
      try {
        const restored = await api.restoreSession();
        if (cancelled) return;
        if (restored) {
          setUser(restored);
          const me = await api.me();
          if (!cancelled) setProjects(me.projects);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const onExpired = () => {
      setUser(null);
      setProjects([]);
    };
    window.addEventListener('auth:session-expired', onExpired);
    return () => window.removeEventListener('auth:session-expired', onExpired);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const result = await api.login(username, password);
    setToken(result.access_token);
    setStoredUser(result.user);
    setUser(result.user);
    try {
      const me = await api.me();
      setProjects(me.projects);
    } catch {
      setProjects([]);
    }
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
    setProjects([]);
  }, []);

  const hasRole = useCallback(
    (roles: UserRole[]) => (user ? roles.includes(user.role) : false),
    [user]
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      projects,
      loading,
      login,
      logout,
      isAdmin: hasRole(['administrator']),
      canWrite: hasRole(['administrator', 'member']),
      hasRole,
    }),
    [user, projects, loading, login, logout, hasRole]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}