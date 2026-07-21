import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";

import { api } from "@/api/client";
import type { Me, UserSummary } from "@/types";

interface AuthContextValue {
  me: Me | null;
  users: UserSummary[];
  loading: boolean;
  loginAs: (userId: string) => Promise<void>;
  logout: () => Promise<void>;
  can: (permission: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const m = await api.get<Me>("/auth/me");
      setMe(m);
    } catch {
      setMe(null);
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const list = await api.get<UserSummary[]>("/auth/users");
        setUsers(list);
      } catch {
        /* ignore */
      }
      await refresh();
      setLoading(false);
    })();
  }, [refresh]);

  const loginAs = useCallback(async (userId: string) => {
    const m = await api.post<Me>("/auth/login", { user_id: userId });
    setMe(m);
  }, []);

  const logout = useCallback(async () => {
    await api.post("/auth/logout");
    setMe(null);
  }, []);

  const can = useCallback(
    (permission: string) => !!me?.permissions.includes(permission),
    [me],
  );

  return (
    <AuthContext.Provider
      value={{ me, users, loading, loginAs, logout, can }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
