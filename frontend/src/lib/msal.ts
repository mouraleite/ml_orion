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
};

/** Se o usuário voltou do login Microsoft, devolve o id_token; senão null. */
export async function consumeMicrosoftRedirectIdToken(): Promise<string | null> {
  await getMsalInstance();
  const result = await redirectPromise;
  return result?.idToken?.trim() || null;
}

/** Redireciona a janela inteira para a tela de login da Microsoft. */
export async function loginWithMicrosoftRedirect(): Promise<void> {
  const instance = await getMsalInstance();
  await instance.loginRedirect(loginRequest);
}
