import type { Participant } from "@/lib/types";

interface Props {
  participants: Participant[];
  onRemove?: (participantId: string) => void;
}

export default function ParticipantList({ participants, onRemove }: Props) {
  if (participants.length === 0) {
    return <p>まだ参加者がいません。</p>;
  }

  return (
    <ul className="participant-list">
      {participants.map((p) => (
        <li key={p.id}>
          <span className={p.is_eliminated ? "eliminated" : ""}>{p.display_name}</span>
          {onRemove && (
            <button className="secondary" onClick={() => onRemove(p.id)}>
              削除
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}
