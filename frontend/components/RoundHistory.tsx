import type { TournamentState } from "@/lib/types";
import BracketColumn from "./BracketColumn";

interface Props {
  state: TournamentState;
  isManage: boolean;
  onReport?: (matchId: string, winnerTeamId: string) => void;
  reportingMatchId?: string | null;
}

export default function RoundHistory({ state, isManage, onReport, reportingMatchId }: Props) {
  return (
    <div>
      {state.overall_champion && (
        <div className="champion-banner">
          優勝: {state.overall_champion.map((p) => p.display_name).join(" & ")}
        </div>
      )}
      <BracketColumn
        bracket="WINNERS"
        rounds={state.rounds}
        isManage={isManage}
        onReport={onReport}
        reportingMatchId={reportingMatchId}
      />
      <BracketColumn
        bracket="LOSERS"
        rounds={state.rounds}
        isManage={isManage}
        onReport={onReport}
        reportingMatchId={reportingMatchId}
      />
      <BracketColumn
        bracket="GRAND_FINAL"
        rounds={state.rounds}
        isManage={isManage}
        onReport={onReport}
        reportingMatchId={reportingMatchId}
      />
    </div>
  );
}
