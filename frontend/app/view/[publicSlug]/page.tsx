"use client";

import { useParams } from "next/navigation";
import useSWR from "swr";
import { getPublicState } from "@/lib/api";
import { FORMAT_LABEL } from "@/lib/types";
import ParticipantList from "@/components/ParticipantList";
import RoundHistory from "@/components/RoundHistory";
import ChampionCard from "@/components/ChampionCard";
import ImageCapture from "@/components/ImageCapture";

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

      {state.status === "COMPLETE" && (
        <ImageCapture filename={`${state.name}-champion.png`} buttonLabel="優勝カードを画像で保存">
          <ChampionCard state={state} />
        </ImageCapture>
      )}

      {state.status !== "SETUP" &&
        (state.status === "COMPLETE" ? (
          <ImageCapture filename={`${state.name}-bracket.png`} buttonLabel="ブラケット全体を画像で保存">
            <RoundHistory state={state} isManage={false} />
          </ImageCapture>
        ) : (
          <RoundHistory state={state} isManage={false} />
        ))}
    </div>
  );
}
