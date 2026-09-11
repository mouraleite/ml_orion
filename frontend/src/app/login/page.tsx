"use client";
import { useState, useEffect, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { AppLoadingScreen } from "@/components/shared/BudgetLoadingState";
import {
  consumeMicrosoftRedirectIdToken,
  isMicrosoftAuthConfigured,
  isMicrosoftSsoPending,
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

const MS_ICON =
  "https://learn.microsoft.com/en-us/entra/identity-platform/media/howto-add-branding-in-apps/ms-symbollockup_mssymbol_19.svg";

function BrandStack() {
  // Arquivos recortados do lockup oficial — proporção natural (sem esticar).
  return (
    <div className="flex flex-col items-center w-full max-w-full gap-4">
      <img
        src="/logo-moura-login.png"
        alt="Moura Leite"
        className="block h-auto w-auto max-w-[150px] sm:max-w-[170px] object-contain"
      />
      <img
        src="/logo-orion-login.png"
        alt="ML Órion"
        className="block h-auto w-full max-w-[340px] sm:max-w-[380px] object-contain"
      />
    </div>
  );
}

function LoginBackdrop() {
  // Fundo institucional (creme + linhas topográficas), sem logo.
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      <div
        className="absolute inset-0 bg-[#FBF7F0]"
        style={{
          backgroundImage: "url('/login-bg-moura.jpg')",
          backgroundSize: "cover",
          backgroundPosition: "center top",
          backgroundRepeat: "no-repeat",
        }}
      />
      {/* Suaviza bordas em telas altas sem apagar as linhas */}
      <div className="absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-[#FBF7F0] to-transparent" />
    </div>
  );
}

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

  useEffect(() => {
    if (!isMicrosoftAuthConfigured()) return;
    let alive = true;

    const pending = isMicrosoftSsoPending();
    const hasOauthReturn =
      typeof window !== "undefined" &&
      (window.location.hash.includes("code") ||
        window.location.hash.includes("id_token") ||
        window.location.search.includes("code="));

    if (!pending && !hasOauthReturn) {
      microsoftSsoExchange = null;
      return;
    }

    if (!microsoftSsoExchange) {
      microsoftSsoExchange = (async () => {
        const idToken = await consumeMicrosoftRedirectIdToken();
        if (!idToken) return "skip";
        const { data } = await api.post<{ access_token: string }>("/auth/microsoft", {
          id_token: idToken,
        });
        if (!data?.access_token) {
          throw new Error("API não devolveu access_token do ERP.");
        }
        await login(data.access_token);
        return "ok";
      })();
    }

    (async () => {
      try {
        if (alive) {
          setError("");
          setMsLoading(true);
        }
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

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
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
          "Não foi possível conectar ao servidor. Verifique se o backend está rodando (porta 8000).",
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
      setError("Login Microsoft ainda sem Client ID / Tenant no frontend (.env.local).");
      return;
    }
    setMsLoading(true);
    try {
      await loginWithMicrosoftRedirect();
    } catch (err: unknown) {
      setError(microsoftErrorMessage(err));
      setMsLoading(false);
    }
  };

  if (loading) {
    return <AppLoadingScreen />;
  }

  return (
    <div className="min-h-screen flex w-full items-center justify-center p-4 sm:p-6 font-sans bg-[#FBF7F0] relative overflow-x-hidden overflow-y-auto">
      <LoginBackdrop />
      <div className="relative z-10 w-full max-w-[440px] box-border rounded-2xl bg-white border border-slate-200/80 p-7 sm:p-10 shadow-[0_20px_50px_rgba(37,87,66,0.12)]">
        <div className="mb-7">
          <BrandStack />
        </div>

        <div className="flex flex-col gap-4">
          {error && (
            <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100 text-center">
              {error}
            </div>
          )}

          <button
            type="button"
            className="w-full h-12 bg-white text-[#1F2937] border border-slate-300 rounded-md font-semibold hover:bg-slate-50 transition-transform hover:scale-[1.01] flex items-center justify-center gap-3 disabled:opacity-60"
            onClick={() => void handleMicrosoft()}
            disabled={msLoading || isLoading}
          >
            <img src={MS_ICON} alt="" className="w-5" />
            {msLoading ? "Abrindo Microsoft…" : "Entrar com Microsoft"}
          </button>
          {!msConfigured && (
            <p className="text-xs text-center text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
              Configure AZURE_* no backend e NEXT_PUBLIC_AZURE_* no frontend para ativar o SSO.
            </p>
          )}

          <div className="flex items-center text-center my-1 text-[#91A89C] text-sm">
            <hr className="flex-1 border-t border-slate-200" />
            <span className="px-3 font-medium">OU</span>
            <hr className="flex-1 border-t border-slate-200" />
          </div>

          <form onSubmit={handleLogin} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-semibold text-[#255742]" htmlFor="email">
                E-mail
              </label>
              <Input
                id="email"
                type="email"
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-11 bg-white border-slate-200 focus-visible:ring-[#F5883A]/20 focus-visible:border-[#F5883A] transition-all"
                required
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-semibold text-[#255742]" htmlFor="password">
                Senha
              </label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-11 bg-white border-slate-200 focus-visible:ring-[#F5883A]/20 focus-visible:border-[#F5883A] transition-all"
                required
              />
            </div>

            <Button
              type="submit"
              className="w-full mt-2 h-12 text-white font-bold text-base transition-all hover:-translate-y-0.5"
              style={{
                background: "linear-gradient(135deg, #F5883A, #F9C094)",
                border: "none",
                boxShadow: "0 4px 15px rgba(245, 136, 58, 0.28)",
              }}
              disabled={isLoading || msLoading}
            >
              {isLoading ? "Entrando..." : "Entrar com e-mail"}
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-[#91A89C]">
          Acesso restrito aos colaboradores Moura Leite
        </p>
      </div>
    </div>
  );
}
