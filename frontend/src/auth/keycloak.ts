import Keycloak from "keycloak-js";

export const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL || `${window.location.origin}/auth`,
  realm: import.meta.env.VITE_KEYCLOAK_REALM || "zero-dose-realm",
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "zd-frontend",
});

let initPromise: Promise<boolean> | null = null;

export function initKeycloak(): Promise<boolean> {
  if (!initPromise) {
    initPromise = keycloak.init({
      onLoad: "login-required",
      pkceMethod: "S256",
      checkLoginIframe: false,
    });
  }
  return initPromise;
}

export function getUserRoles(): string[] {
  return keycloak.tokenParsed?.realm_access?.roles ?? [];
}

export function hasRole(role: string): boolean {
  return getUserRoles().includes(role);
}

export function getUsername(): string {
  return (
    (keycloak.tokenParsed?.preferred_username as string | undefined) || "user"
  );
}

export async function getFreshToken(): Promise<string> {
  await keycloak.updateToken(30);
  if (!keycloak.token) {
    throw new Error("No active access token");
  }
  return keycloak.token;
}