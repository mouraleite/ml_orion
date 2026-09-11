import {
  PublicClientApplication,
  type AuthenticationResult,
  type Configuration,
  type SilentRequest,
} from "@azure/msal-browser";

const clientId = (process.env.NEXT_PUBLIC_AZURE_CLIENT_ID || "").trim();
const tenantId = (process.env.NEXT_PUBLIC_AZURE_TENANT_ID || "").trim();
const redirectUri =
  (process.env.NEXT_PUBLIC_AZURE_REDIRECT_URI || "").trim() ||
  (typeof window !== "undefined" ? `${window.location.origin}/login` : "http://localhost:3000/login");

const SSO_PENDING_KEY = "ml_orion_ms_sso_pending";

export function isMicrosoftAuthConfigured(): boolean {
  return Boolean(clientId && tenantId);
}

let pca: PublicClientApplication | null = null;
let initPromise: Promise<PublicClientApplication> | null = null;
/** handleRedirectPromise só uma vez por carga da página. */
let redirectPromise: Promise<AuthenticationResult | null> | null = null;
let redirectConsumePromise: Promise<string | null> | null = null;

function buildConfig(): Configuration {
  return {
    auth: {
      clientId,
      authority: `https://login.microsoftonline.com/${tenantId}`,
      redirectUri,
      postLogoutRedirectUri: redirectUri,
      navigateToLoginRequestUrl: false,
    },
    cache: {
      cacheLocation: "sessionStorage",
      storeAuthStateInCookie: false,
    },
  };
}

export async function getMsalInstance(): Promise<PublicClientApplication> {
  if (!isMicrosoftAuthConfigured()) {
    throw new Error("Microsoft Entra não configurado no frontend.");
  }
  if (pca) return pca;
  if (!initPromise) {
    initPromise = (async () => {
      const instance = new PublicClientApplication(buildConfig());
      await instance.initialize();
      redirectPromise = instance.handleRedirectPromise();
      await redirectPromise;
      pca = instance;
      return instance;
    })();
  }
  return initPromise;
}

const loginRequest = {
  scopes: ["openid", "profile", "email"],
  prompt: "select_account" as const,
};

function clearOauthHash(): void {
  if (typeof window === "undefined") return;
  if (window.location.hash || window.location.search.includes("code=")) {
    window.history.replaceState({}, document.title, window.location.pathname);
  }
}

function redirectErrorFromUrl(): string | null {
  if (typeof window === "undefined") return null;
  const raw = `${window.location.hash || ""}${window.location.search || ""}`;
  const err = raw.match(/[?#&]error=([^&]+)/i)?.[1];
  if (!err) return null;
  const desc = raw.match(/[?#&]error_description=([^&]+)/i)?.[1];
  const decoded = desc ? decodeURIComponent(desc.replace(/\+/g, " ")) : decodeURIComponent(err);
  return `Microsoft: ${decoded}`;
}

function isSsoPending(): boolean {
  return typeof sessionStorage !== "undefined" && sessionStorage.getItem(SSO_PENDING_KEY) === "1";
}

export function isMicrosoftSsoPending(): boolean {
  return isSsoPending();
}

/** Limpa sessão MSAL local (Sair do ERP). Não desloga o usuário do Office/Microsoft. */
export async function clearMicrosoftSession(): Promise<void> {
  if (typeof sessionStorage !== "undefined") {
    sessionStorage.removeItem(SSO_PENDING_KEY);
  }
  redirectConsumePromise = null;
  if (!isMicrosoftAuthConfigured()) return;
  try {
    const instance = await getMsalInstance();
    await instance.clearCache();
  } catch {
    /* ignore — logout do ERP não deve falhar por MSAL */
  }
}

/** Se o usuário voltou do login Microsoft, devolve o id_token; senão null. */
export async function consumeMicrosoftRedirectIdToken(): Promise<string | null> {
  if (!redirectConsumePromise) {
    redirectConsumePromise = (async () => {
      const pending = isSsoPending();
      const urlError = redirectErrorFromUrl();
      const instance = await getMsalInstance();
      const result = await redirectPromise;

      if (urlError) {
        sessionStorage.removeItem(SSO_PENDING_KEY);
        clearOauthHash();
        throw new Error(urlError);
      }

      // Sem redirect SSO em andamento: não reaproveitar conta em cache (evita reentrar após Sair).
      if (!pending && !result) {
        clearOauthHash();
        return null;
      }

      let idToken = result?.idToken?.trim() || "";

      if (!idToken && pending) {
        const account = result?.account || instance.getAllAccounts()[0];
        if (account) {
          try {
            const silentReq: SilentRequest = {
              ...loginRequest,
              account,
              forceRefresh: false,
            };
            const silent = await instance.acquireTokenSilent(silentReq);
            idToken = silent.idToken?.trim() || "";
          } catch {
            /* segue para erro/pendente */
          }
        }
      }

      clearOauthHash();

      if (idToken) {
        sessionStorage.removeItem(SSO_PENDING_KEY);
        return idToken;
      }

      if (pending) {
        sessionStorage.removeItem(SSO_PENDING_KEY);
        throw new Error(
          "Microsoft autenticou, mas o navegador não devolveu o id_token. Feche abas extras do login e tente de novo.",
        );
      }

      return null;
    })();
  }
  return redirectConsumePromise;
}

/** Redireciona a janela inteira para a tela de login da Microsoft. */
export async function loginWithMicrosoftRedirect(): Promise<void> {
  const instance = await getMsalInstance();
  sessionStorage.setItem(SSO_PENDING_KEY, "1");
  redirectConsumePromise = null;
  await instance.loginRedirect(loginRequest);
}
