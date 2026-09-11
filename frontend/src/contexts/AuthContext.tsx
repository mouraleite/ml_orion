"use client";
import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { setAuthSession, clearAuthSession, syncAuthSessionFromStorage } from '@/lib/auth-session';
import { clearMicrosoftSession, isMicrosoftAuthConfigured } from '@/lib/msal';
import type { UserCapabilities } from '@/lib/roles';

interface DepartamentoSimples {
  id: number;
  nome: string;
  is_residual?: boolean;
  diretoria_id?: number | null;
}

interface DiretoriaSimples {
  id: number;
  nome: string;
  departamento_ids?: number[];
}

interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  effective_role?: string;
  capabilities?: UserCapabilities;
  departamentos: DepartamentoSimples[];
  diretorias?: DiretoriaSimples[];
  departamento_id: number;
  pode_ver_todos_departamentos?: boolean;
  pode_consolidacao_mldu_orcamento?: boolean;
  pode_consolidacao_mldu_forecast?: boolean;
  perfil?: any;
  write_modules?: Record<string, boolean>;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  activeDepartamentoId: number;
  setActiveDepartamentoId: (id: number) => void;
  login: (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

const DEV_DUMMY_TOKEN = "dummy-token-for-dev";

function isDevDummyAuthAllowed() {
  return process.env.NODE_ENV !== "production";
}

/** Fallback local quando o backend não responde (dev). Mantém cookie do middleware. */
function devFallbackUser(): User {
  return {
    id: 9999,
    email: "admin@mouraleite.com.br",
    full_name: "Administrador (dev)",
    role: "ADMIN",
    effective_role: "Administrador",
    capabilities: { admin: true, diretor: true, gestor: true, analista: true },
    departamentos: [{ id: 1, nome: "Engenharia" }],
    diretorias: [],
    departamento_id: 1,
    pode_ver_todos_departamentos: true,
    pode_consolidacao_mldu_orcamento: true,
    pode_consolidacao_mldu_forecast: true,
    write_modules: {
      "Rentabilidade de Produtos": true,
      "Modelagem Financeira": true,
      Orçamento: true,
      Forecast: true,
      Consolidação: true,
      "Governança e Índices": true,
      Apoio: true,
      Segurança: true,
    },
  };
}

async function resolveUserFromToken(token: string): Promise<User> {
  if (token === DEV_DUMMY_TOKEN && isDevDummyAuthAllowed()) {
    try {
      return await fetchUserFromApi();
    } catch {
      return devFallbackUser();
    }
  }
  return fetchUserFromApi();
}

function persistDepartamentoId(id: number | null) {
  if (typeof window === "undefined") return;
  if (id == null) localStorage.removeItem("departamento_id");
  else localStorage.setItem("departamento_id", String(id));
}

function resolveActiveDepartamentoId(
  departamentos: DepartamentoSimples[],
  podeVerTodos?: boolean,
  diretorias: DiretoriaSimples[] = [],
): number {
  if (departamentos.length === 0) {
    return 1;
  }
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("departamento_id");
    if (stored != null && stored !== "") {
      const parsed = Number(stored);
      if (parsed === 0 && podeVerTodos) {
        return 0;
      }
      if (parsed < 0 && diretorias.some((d) => d.id === -parsed)) {
        return parsed;
      }
      if (departamentos.some((d) => d.id === parsed)) {
        return parsed;
      }
    }
  }
  return departamentos[0].id;
}

async function fetchUserFromApi(): Promise<User> {
  const { data } = await api.get("/users/me");
  return buildUser(data);
}

function buildUser(data: any): User {
  const departamentos: DepartamentoSimples[] = data.departamentos ?? [];
  const diretorias: DiretoriaSimples[] = data.diretorias ?? [];
  const departamento_id = resolveActiveDepartamentoId(
    departamentos,
    Boolean(data.pode_ver_todos_departamentos),
    diretorias,
  );
  return {
    id: data.id,
    email: data.email,
    full_name: data.full_name,
    role: data.role,
    effective_role: data.effective_role ?? data.role,
    capabilities: data.capabilities,
    departamentos,
    diretorias,
    departamento_id,
    pode_ver_todos_departamentos: Boolean(data.pode_ver_todos_departamentos),
    pode_consolidacao_mldu_orcamento: Boolean(data.pode_consolidacao_mldu_orcamento),
    pode_consolidacao_mldu_forecast: Boolean(data.pode_consolidacao_mldu_forecast),
    perfil: data.perfil,
    write_modules: data.write_modules || {},
  };
}

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [activeDepartamentoId, setActiveDepartamentoIdState] = useState(1);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const setActiveDepartamentoId = useCallback((id: number) => {
    persistDepartamentoId(id);
    setActiveDepartamentoIdState(id);
    setUser((prev) => (prev ? { ...prev, departamento_id: id } : prev));
  }, []);

  useEffect(() => {
    const loadUser = async () => {
      const token = localStorage.getItem("access_token");
      if (!token) {
        clearAuthSession();
        setLoading(false);
        return;
      }

      if (token === DEV_DUMMY_TOKEN && !isDevDummyAuthAllowed()) {
        localStorage.removeItem("access_token");
        persistDepartamentoId(null);
        clearAuthSession();
        setUser(null);
        setLoading(false);
        return;
      }

      try {
        const loaded = await resolveUserFromToken(token);
        persistDepartamentoId(loaded.departamento_id);
        setAuthSession();
        setUser(loaded);
        setActiveDepartamentoIdState(loaded.departamento_id);
      } catch (error) {
        localStorage.removeItem("access_token");
        clearAuthSession();
        setUser(null);
      }
      setLoading(false);
    };
    loadUser();
  }, [setActiveDepartamentoId]);

  const login = async (token: string): Promise<void> => {
    localStorage.setItem("access_token", token);
    if (token === DEV_DUMMY_TOKEN && !isDevDummyAuthAllowed()) {
      localStorage.removeItem("access_token");
      persistDepartamentoId(null);
      clearAuthSession();
      setUser(null);
      throw new Error("Atalho de desenvolvimento desativado neste ambiente.");
    }
    try {
      const loaded = await resolveUserFromToken(token);
      persistDepartamentoId(loaded.departamento_id);
      setAuthSession();
      setUser(loaded);
      setActiveDepartamentoIdState(loaded.departamento_id);
      router.push("/dashboard");
    } catch (error) {
      console.error("Erro ao buscar dados do usuário após login", error);
      localStorage.removeItem("access_token");
      persistDepartamentoId(null);
      clearAuthSession();
      setUser(null);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    persistDepartamentoId(null);
    clearAuthSession();
    setUser(null);
    void (async () => {
      if (isMicrosoftAuthConfigured()) {
        await clearMicrosoftSession();
      }
      router.push('/login');
    })();
  };

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      loading,
      activeDepartamentoId,
      setActiveDepartamentoId,
      login,
      logout,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
