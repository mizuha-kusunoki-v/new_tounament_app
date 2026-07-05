import type { TournamentCreated, TournamentFormat, TournamentManageState, TournamentState } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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

export { ApiError };
