import type { TournamentState } from "@/lib/types";
import { FORMAT_LABEL } from "@/lib/types";

interface Props {
  state: TournamentState;
}

export default function ChampionCard({ state }: Props) {
  if (!state.overall_champion) return null;

  return (
    <div className="champion-card">
      <p className="champion-card-format">{FORMAT_LABEL[state.format]}</p>
      <h2 className="champion-card-title">{state.name}</h2>
      <p className="champion-card-trophy">🏆</p>
      <p className="champion-card-names">
        {state.overall_champion.map((p) => p.display_name).join(" & ")}
      </p>
      <p className="champion-card-label">優勝</p>
    </div>
  );
}
