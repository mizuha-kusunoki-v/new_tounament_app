import type { Match, Team } from "@/lib/types";

interface Props {
  match: Match;
  isManage: boolean;
  onReport?: (matchId: string, winnerTeamId: string) => void;
  reporting?: boolean;
}

function teamLabel(team: Team): string {
  return `${team.player_one.display_name} & ${team.player_two.display_name}`;
}

export default function MatchCard({ match, isManage, onReport, reporting }: Props) {
  if (!match.team_b) {
    // TEAM_BYE / terminal round: a single team auto-advances, no match played.
    return (
      <div className="card match-card">
        <div className="team-box winner">{match.team_a ? teamLabel(match.team_a) : "-"}</div>
        <span className="vs">不戦勝で通過</span>
      </div>
    );
  }

  const teamA = match.team_a!;
  const teamB = match.team_b;
  const canReport = isManage && !match.winner_team_id && onReport;

  return (
    <div className="card match-card">
      <div className={`team-box ${match.winner_team_id === teamA.id ? "winner" : ""}`}>{teamLabel(teamA)}</div>
      <span className="vs">vs</span>
      <div className={`team-box ${match.winner_team_id === teamB.id ? "winner" : ""}`}>{teamLabel(teamB)}</div>
      {canReport && (
        <>
          <button disabled={reporting} onClick={() => onReport(match.id, teamA.id)}>
            左の勝利
          </button>
          <button disabled={reporting} onClick={() => onReport(match.id, teamB.id)}>
            右の勝利
          </button>
        </>
      )}
      {!match.winner_team_id && !isManage && <span className="vs">結果待ち</span>}
    </div>
  );
}
