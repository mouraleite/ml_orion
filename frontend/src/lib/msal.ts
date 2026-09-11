import {
  PublicClientApplication,
  type AuthenticationResult,
  type Configuration,
} from "@azure/msal-browser";

const clientId = (process.env.NEXT_PUBLIC_AZURE_CLIENT_ID || "").trim();
const tenantId = (process.env.NEXT_PUBLIC_AZURE_TENANT_ID || "").trim();
const redirectUri =
  (process.env.NEXT_PUBLIC_AZURE_REDIRECT_URI || "").trim() ||
  (typeof window !== "undefined" ? `${window.location.origin}/login` : "http://localhost:3000/login");

export function isMicrosoftAuthConfigured(): boolean {
  return Boolean(clientId && tenantId);
}

let pca: PublicClientApplication | null = null;
let initPromise: Promise<PublicClientApplication> | null = null;
/** handleRedirectPromise só uma vez por carga da página. */
let redirectPromise: Promise<AuthenticationResult | null> | null = null;

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
  // Força a UI da Microsoft (escolha de conta), em vez de SSO silencioso.
  prompt: "select_account" as const,
};

function hasMicrosoftRedirectResponse(): boolean {
  if (typeof window === "undefined") return false;
  const hash = window.location.hash || "";
  const search = window.location.search || "";
  return (
    /[#&?]code=/i.test(hash) ||
    /[#&?]code=/i.test(search) ||
    /[#&?]error=/i.test(hash) ||
    /[#&?]error=/i.test(search) ||
    /[#&?]client_info=/i.test(hash)
  );
}

/** Se o usuário voltou do login Microsoft, devolve o id_token; senão null. */
let redirectConsumePromise: Promise<string | null> | null = null;

export async function consumeMicrosoftRedirectIdToken(): Promise<string | null> {
  // Uma única troca code→token por carga da página (evita Strict Mode / remount).
  if (!redirectConsumePromise) {
    redirectConsumePromise = (async () => {
      const hadResponse = hasMicrosoftRedirectResponse();
      await getMsalInstance();
      if (!hadResponse) return null;
      const result = await redirectPromise;
      const idToken = result?.idToken?.trim() || null;
      if (typeof window !== "undefined" && window.location.hash) {
        window.history.replaceState(
          {},
          document.title,
          window.location.pathname + window.location.search,
        );
      }
      return idToken;
    })();
  }
  return redirectConsumePromise;
}

/** Redireciona a janela inteira para a tela de login da Microsoft. */
export async function loginWithMicrosoftRedirect(): Promise<void> {
  const instance = await getMsalInstance();
  await instance.loginRedirect(loginRequest);
}
