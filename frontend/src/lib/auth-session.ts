/** Cookie leve para o middleware Next (localStorage não é visível no servidor). */

export const AUTH_COOKIE = "erp_ml_auth";
const MAX_AGE_SEC = 60 * 60 * 24 * 7; // 7 dias

function cookieSecureFlag(): string {
  if (typeof window === "undefined") return "";
  return window.location.protocol === "https:" ? "; Secure" : "";
}

export function setAuthSession(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE}=1; path=/; max-age=${MAX_AGE_SEC}; SameSite=Lax${cookieSecureFlag()}`;
}

export function clearAuthSession(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE}=; path=/; max-age=0; SameSite=Lax${cookieSecureFlag()}`;
}

export function syncAuthSessionFromStorage(): void {
  if (typeof window === "undefined") return;
  const token = localStorage.getItem("access_token");
  if (token) setAuthSession();
  else clearAuthSession();
}
