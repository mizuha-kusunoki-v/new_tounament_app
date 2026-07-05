import type { Bracket, Round } from "@/lib/types";
import MatchCard from "./MatchCard";

const BRACKET_LABEL: Record<Bracket, string> = {
  WINNERS: "勝者ブラケット",
  LOSERS: "敗者復活ブラケット",
  GRAND_FINAL: "グランドファイナル",
};

interface Props {
  bracket: Bracket;
  rounds: Round[];
  isManage: boolean;
  onReport?: (matchId: string, winnerTeamId: string) => void;
  reportingMatchId?: string | null;
}

export default function BracketColumn({ bracket, rounds, isManage, onReport, reportingMatchId }: Props) {
  const bracketRounds = rounds
    .filter((r) => r.bracket === bracket)
    .sort((a, b) => a.round_number - b.round_number);

  if (bracketRounds.length === 0) {
    return null;
  }

  return (
    <section className="bracket-section">
      <h2>{BRACKET_LABEL[bracket]}</h2>
      {bracketRounds.map((round) => (
        <div key={round.id}>
          <p className="round-heading">
            ラウンド {round.round_number}
            {round.status === "PENDING" && "（人数が揃うまで待機中）"}
            {round.waiting_bye_participant && ` / ${round.waiting_bye_participant.display_name} は次ラウンドへシード`}
            {round.excluded_participant && ` / ${round.excluded_participant.display_name} は人数調整のため対象外`}
          </p>
          {round.matches.map((match) => (
            <MatchCard
              key={match.id}
              match={match}
              isManage={isManage}
              onReport={onReport}
              reporting={reportingMatchId === match.id}
            />
          ))}
        </div>
      ))}
    </section>
  );
}
