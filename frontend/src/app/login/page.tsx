"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { AppLoadingScreen } from "@/components/shared/BudgetLoadingState";
import {
  consumeMicrosoftRedirectIdToken,
  isMicrosoftAuthConfigured,
  loginWithMicrosoftRedirect,
} from "@/lib/msal";

function microsoftErrorMessage(err: unknown): string {
  const ax = err as {
    response?: { data?: { detail?: string } };
    message?: string;
    errorMessage?: string;
  };
  const detail = ax.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (ax.message || ax.errorMessage) {
    return ax.message || ax.errorMessage || "Falha no login Microsoft.";
  }
  return "Não foi possível entrar com Microsoft.";
}

/** Evita dois POSTs /auth/microsoft no Strict Mode. */
let microsoftSsoExchange: Promise<"ok" | "skip" | "error"> | null = null;

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [msLoading, setMsLoading] = useState(false);
  const [msConfigured, setMsConfigured] = useState(false);
  const { login, loading, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [loading, isAuthenticated, router]);

  useEffect(() => {
    const frontOk = isMicrosoftAuthConfigured();
    setMsConfigured(frontOk);
    if (!frontOk) return;
    api
      .get<{ configured: boolean }>("/auth/microsoft/status")
      .then((r) => setMsConfigured(Boolean(r.data?.configured) && frontOk))
      .catch(() => setMsConfigured(frontOk));
  }, []);

  // Volta da Microsoft (redirect): troca id_token pelo JWT do ERP.
  useEffect(() => {
    if (!isMicrosoftAuthConfigured()) return;
    let alive = true;

    if (!microsoftSsoExchange) {
      microsoftSsoExchange = (async () => {
        const idToken = await consumeMicrosoftRedirectIdToken();
        if (!idToken) return "skip";
        const { data } = await api.post("/auth/microsoft", { id_token: idToken });
        await login(data.access_token);
        return "ok";
      })().catch((err: unknown) => {
        // Propaga para o efeito atual poder mostrar o erro.
        throw err;
      });
    }

    (async () => {
      try {
        if (alive) setMsLoading(true);
        const result = await microsoftSsoExchange;
        if (result === "skip") {
          microsoftSsoExchange = null;
        }
      } catch (err: unknown) {
        microsoftSsoExchange = null;
        if (alive) setError(microsoftErrorMessage(err));
      } finally {
        if (alive) setMsLoading(false);
      }
    })();

    return () => {
      alive = false;
    };
  }, [login]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      // Desenvolvimento: fluxo que funcionava antes (não exige usuário no banco).
      if (process.env.NODE_ENV !== "production") {
        await login("dummy-token-for-dev");
        return;
      }
      const body = new URLSearchParams();
      body.append("username", email.trim());
      body.append("password", password);
      const { data } = await api.post("/login/access-token", body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      await login(data.access_token);
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: string } }; message?: string };
      if (!ax.response) {
        setError(
          "Não foi possível conectar ao servidor. Verifique se o backend está rodando (porta 8000)."
        );
      } else {
        const detail = ax.response.data?.detail;
        setError(typeof detail === "string" ? detail : "E-mail ou senha incorretos.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleMicrosoft = async () => {
    setError("");
    if (!isMicrosoftAuthConfigured()) {
      setError(
        "Login Microsoft ainda sem Client ID / Tenant no frontend (.env.local)."
      );
      return;
    }
    setMsLoading(true);
    try {
      await loginWithMicrosoftRedirect();
      // A página sai para login.microsoftonline.com; se voltar sem navegar, cai no catch.
    } catch (err: unknown) {
      setError(microsoftErrorMessage(err));
      setMsLoading(false);
    }
  };

  if (loading) {
    return <AppLoadingScreen />;
  }

  return (
    <div className="min-h-screen flex w-full overflow-hidden bg-[#fdfdfd] font-sans">
      
      {/* Lado Esquerdo - Imagem com Overlay Escuro */}
      <div className="hidden md:flex flex-[1.2] relative overflow-hidden items-end">
        <img 
          src="/Fundo.jpg" 
          alt="Empreendimento Moura Leite" 
          className="absolute inset-0 w-full h-full object-cover object-center"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = 'none';
            (e.target as HTMLImageElement).parentElement!.style.background = 'linear-gradient(135deg, #1a2332, #0f171e)';
          }}
        />
        
        {/* Overlay Escuro com Gradiente */}
        <div className="absolute inset-0 z-10" style={{
          background: 'linear-gradient(180deg, rgba(15, 23, 30, 0.1) 0%, rgba(15, 23, 30, 0.5) 70%, rgba(15, 23, 30, 0.85) 100%)'
        }}></div>

        {/* Textos sobre a Imagem */}
        <div className="relative z-20 p-10 text-white w-full">
          <h2 className="text-3xl font-extrabold mb-2" style={{ textShadow: '0 2px 8px rgba(0,0,0,0.3)' }}>
            Moura Leite
          </h2>
          <p className="text-sm opacity-85 max-w-sm leading-relaxed" style={{ textShadow: '0 1px 4px rgba(0,0,0,0.3)' }}>
            Plataforma Corporativa de Gestão, Viabilidades e Consolidação Financeira
          </p>
        </div>
      </div>

      {/* Lado Direito - Formulário */}
      <div className="flex-[0.8] relative flex items-center justify-center p-6 md:p-10 bg-[#fdfdfd]">
        
        {/* Divisor Decorativo */}
        <div className="hidden md:block absolute left-0 top-[10%] bottom-[10%] w-[1px]" style={{
          background: 'linear-gradient(180deg, transparent, rgba(245, 136, 58, 0.3), transparent)'
        }}></div>

        {/* Card do Formulário (Efeito Glass) */}
        <div className="relative z-10 w-full max-w-[420px] p-10 md:p-12 rounded-xl" style={{
          background: 'rgba(255, 255, 255, 0.04)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)'
        }}>
          
          <div className="flex flex-col items-center mb-8 gap-3 w-full">
            <img 
              src="/logo-ml-orion.png" 
              alt="Logo ML Órion" 
              className="w-full h-auto object-contain max-w-[280px]"
            />
          </div>

          <div className="flex flex-col gap-4">
            {error && (
              <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100 text-center">
                {error}
              </div>
            )}

            <button
              type="button"
              className="w-full h-12 bg-white text-slate-700 border border-slate-300 rounded-md font-semibold hover:bg-slate-50 transition-transform hover:scale-[1.02] flex items-center justify-center gap-3 disabled:opacity-60"
              onClick={() => void handleMicrosoft()}
              disabled={msLoading || isLoading}
            >
              <img src="https://learn.microsoft.com/en-us/entra/identity-platform/media/howto-add-branding-in-apps/ms-symbollockup_mssymbol_19.svg" alt="Microsoft" className="w-5" />
              {msLoading ? "Abrindo Microsoft…" : "Entrar com Microsoft"}
            </button>
            {!msConfigured && (
              <p className="text-xs text-center text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
                Configure AZURE_* no backend e NEXT_PUBLIC_AZURE_* no frontend para ativar o SSO.
              </p>
            )}

            {/* Divisor OU */}
            <div className="flex items-center text-center my-1 text-slate-400 text-sm">
              <hr className="flex-1 border-t border-slate-300" />
              <span className="px-3 font-medium">OU</span>
              <hr className="flex-1 border-t border-slate-300" />
            </div>

            <form onSubmit={handleLogin} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-semibold text-slate-600" htmlFor="email">
                  E-mail
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="seu@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-11 bg-black/5 border-black/10 focus-visible:ring-[#F5883A]/20 focus-visible:border-[#F5883A] transition-all"
                  required
                />
              </div>
              
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-semibold text-slate-600" htmlFor="password">
                  Senha
                </label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-11 bg-black/5 border-black/10 focus-visible:ring-[#F5883A]/20 focus-visible:border-[#F5883A] transition-all"
                  required
                />
              </div>

              <Button
                type="submit"
                className="w-full mt-2 h-12 text-white font-bold text-base transition-all hover:-translate-y-0.5"
                style={{
                  background: 'linear-gradient(135deg, #F5883A, #F9C094)',
                  border: 'none',
                  boxShadow: '0 4px 15px rgba(245, 136, 58, 0.3)'
                }}
                disabled={isLoading || msLoading}
              >
                {isLoading ? "Entrando..." : "Entrar com e-mail"}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
