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
      pca = instance;
      return instance;
    })();
  }
  return initPromise;
}

const loginRequest = {
  scopes: ["openid", "profile", "email"],
};

/** Popup Microsoft → id_token para trocar no backend. */
export async function loginWithMicrosoftPopup(): Promise<string> {
  const instance = await getMsalInstance();
  let result: AuthenticationResult;
  try {
    result = await instance.loginPopup(loginRequest);
  } catch (err: unknown) {
    const code = (err as { errorCode?: string })?.errorCode;
    if (code === "interaction_in_progress") {
      throw new Error("Já existe um login Microsoft em andamento. Feche o popup e tente de novo.");
    }
    throw err;
  }
  const idToken = result.idToken;
  if (!idToken) {
    throw new Error("Microsoft não retornou id_token.");
  }
  return idToken;
}
