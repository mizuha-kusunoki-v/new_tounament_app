import type {
  AdminTournamentListItem,
  AdminUser,
  TournamentCreated,
  TournamentFormat,
  TournamentManageState,
  TournamentState,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const ADMIN_TOKEN_KEY = "admin_token";

class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ADMIN_TOKEN_KEY);
}

export function setAdminToken(token: string): void {
  localStorage.setItem(ADMIN_TOKEN_KEY, token);
}

export function clearAdminToken(): void {
  localStorage.removeItem(ADMIN_TOKEN_KEY);
}

async function adminRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAdminToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (res.status === 401) {
    clearAdminToken();
    throw new ApiError("認証が必要です。再度ログインしてください。");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(body.detail ?? `Request failed: ${res.status}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

export function createTournament(name: string, format: TournamentFormat): Promise<TournamentCreated> {
  return request("/tournaments", { method: "POST", body: JSON.stringify({ name, format }) });
}

export function addParticipant(manageToken: string, displayName: string) {
  return request(`/tournaments/${manageToken}/participants`, {
    method: "POST",
    body: JSON.stringify({ display_name: displayName }),
  });
}

export function removeParticipant(manageToken: string, participantId: string): Promise<void> {
  return request(`/tournaments/${manageToken}/participants/${participantId}`, { method: "DELETE" });
}

export function startTournament(manageToken: string): Promise<TournamentManageState> {
  return request(`/tournaments/${manageToken}/start`, { method: "POST" });
}

export function getManageState(manageToken: string): Promise<TournamentManageState> {
  return request(`/tournaments/${manageToken}/manage`);
}

export function getPublicState(publicSlug: string): Promise<TournamentState> {
  return request(`/tournaments/public/${publicSlug}`);
}

export function reportMatch(
  manageToken: string,
  matchId: string,
  winnerTeamId: string
): Promise<TournamentManageState> {
  return request(`/tournaments/${manageToken}/matches/${matchId}/report`, {
    method: "POST",
    body: JSON.stringify({ winner_team_id: winnerTeamId }),
  });
}

export async function adminLogin(username: string, password: string): Promise<void> {
  const body = await request<{ access_token: string }>("/admin/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setAdminToken(body.access_token);
}

export function adminMe(): Promise<{ username: string }> {
  return adminRequest("/admin/me");
}

export function listAllTournaments(): Promise<AdminTournamentListItem[]> {
  return adminRequest("/admin/tournaments");
}

export function deleteTournamentAsAdmin(tournamentId: string): Promise<void> {
  return adminRequest(`/admin/tournaments/${tournamentId}`, { method: "DELETE" });
}

export function createAdminUser(username: string, password: string): Promise<AdminUser> {
  return adminRequest("/admin/users", { method: "POST", body: JSON.stringify({ username, password }) });
}

export { ApiError };
