"use client";

import { useParams } from "next/navigation";
import useSWR from "swr";
import { getPublicState } from "@/lib/api";
import { FORMAT_LABEL } from "@/lib/types";
import ParticipantList from "@/components/ParticipantList";
import RoundHistory from "@/components/RoundHistory";

export default function PublicViewPage() {
  const { publicSlug } = useParams<{ publicSlug: string }>();
  const { data: state, error } = useSWR(
    publicSlug ? ["public", publicSlug] : null,
    () => getPublicState(publicSlug),
    { refreshInterval: 3000 }
  );

  if (error) return <div className="page error-banner">大会が見つかりませんでした。</div>;
  if (!state) return <div className="page">読み込み中...</div>;

  return (
    <div className="page">
      <h1>{state.name}</h1>
      <p>形式: {FORMAT_LABEL[state.format]}</p>

      {state.status === "SETUP" && (
        <>
          <p>大会の開始を待っています。（現在 {state.participants.length} 人参加）</p>
          <ParticipantList participants={state.participants} />
        </>
      )}

      {state.status !== "SETUP" && <RoundHistory state={state} isManage={false} />}
    </div>
  );
}
