export type Bracket = "WINNERS" | "LOSERS" | "GRAND_FINAL";
export type RoundStatus = "PENDING" | "IN_PROGRESS" | "COMPLETE";
export type MatchKind = "NORMAL" | "TEAM_BYE" | "GRAND_FINAL" | "GRAND_FINAL_RESET";
export type TournamentStatus = "SETUP" | "IN_PROGRESS" | "COMPLETE";
export type TournamentFormat = "SINGLE_ELIMINATION" | "DOUBLE_ELIMINATION";

export const FORMAT_LABEL: Record<TournamentFormat, string> = {
  SINGLE_ELIMINATION: "シングルエリミネーション",
  DOUBLE_ELIMINATION: "ダブルエリミネーション",
};

export interface Participant {
  id: string;
  display_name: string;
  is_eliminated: boolean;
}

export interface Team {
  id: string;
  player_one: Participant;
  player_two: Participant;
}

export interface Match {
  id: string;
  kind: MatchKind;
  team_a: Team | null;
  team_b: Team | null;
  winner_team_id: string | null;
  sequence_in_round: number;
}

export interface Round {
  id: string;
  bracket: Bracket;
  round_number: number;
  status: RoundStatus;
  waiting_bye_participant: Participant | null;
  excluded_participant: Participant | null;
  matches: Match[];
}

export interface TournamentState {
  id: string;
  name: string;
  status: TournamentStatus;
  format: TournamentFormat;
  public_slug: string;
  participants: Participant[];
  rounds: Round[];
  overall_champion: Participant[] | null;
}

export interface TournamentManageState extends TournamentState {
  manage_token: string;
}

export interface TournamentCreated {
  id: string;
  name: string;
  manage_token: string;
  public_slug: string;
  format: TournamentFormat;
}

export interface AdminTournamentListItem {
  id: string;
  name: string;
  format: TournamentFormat;
  status: TournamentStatus;
  created_at: string;
  manage_token: string;
  public_slug: string;
}

export interface AdminUser {
  id: string;
  username: string;
  created_at: string;
}
