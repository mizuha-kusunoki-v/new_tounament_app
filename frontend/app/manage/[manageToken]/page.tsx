"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { addParticipant, ApiError, getManageState, removeParticipant, reportMatch, startTournament } from "@/lib/api";
import { FORMAT_LABEL } from "@/lib/types";
import ParticipantList from "@/components/ParticipantList";
import RoundHistory from "@/components/RoundHistory";

export default function ManagePage() {
  const { manageToken } = useParams<{ manageToken: string }>();
  const { data: state, error, mutate } = useSWR(
    manageToken ? ["manage", manageToken] : null,
    () => getManageState(manageToken),
    { refreshInterval: 3000 }
  );

  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);
  const [reportingMatchId, setReportingMatchId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function handleAddParticipant(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setBusy(true);
    setActionError(null);
    try {
      await addParticipant(manageToken, newName.trim());
      setNewName("");
      await mutate();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "参加者の追加に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  async function handleRemoveParticipant(participantId: string) {
    setBusy(true);
    setActionError(null);
    try {
      await removeParticipant(manageToken, participantId);
      await mutate();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "参加者の削除に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  async function handleStart() {
    setBusy(true);
    setActionError(null);
    try {
      await mutate(startTournament(manageToken));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "大会の開始に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  async function handleReport(matchId: string, winnerTeamId: string) {
    setReportingMatchId(matchId);
    setActionError(null);
    try {
      await mutate(reportMatch(manageToken, matchId, winnerTeamId));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "結果の報告に失敗しました");
    } finally {
      setReportingMatchId(null);
    }
  }

  if (error) return <div className="page error-banner">大会が見つかりませんでした。</div>;
  if (!state) return <div className="page">読み込み中...</div>;

  const publicUrl = typeof window !== "undefined" ? `${window.location.origin}/view/${state.public_slug}` : "";

  return (
    <div className="page">
      <h1>{state.name}（主催者用）</h1>
      <p>形式: {FORMAT_LABEL[state.format]}</p>
      <p className="share-link">参加者向け閲覧リンク: {publicUrl}</p>
      {actionError && <p className="error-banner">{actionError}</p>}

      {state.status === "SETUP" && (
        <>
          <h2>参加者登録（{state.participants.length}人）</h2>
          <ParticipantList participants={state.participants} onRemove={handleRemoveParticipant} />
          <form onSubmit={handleAddParticipant} className="field-row">
            <input
              type="text"
              placeholder="参加者名"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <button type="submit" disabled={busy || !newName.trim()}>
              追加
            </button>
          </form>
          <button onClick={handleStart} disabled={busy || state.participants.length < 4}>
            大会を開始（最低4人）
          </button>
        </>
      )}

      {state.status !== "SETUP" && (
        <RoundHistory
          state={state}
          isManage
          onReport={handleReport}
          reportingMatchId={reportingMatchId}
        />
      )}
    </div>
  );
}
