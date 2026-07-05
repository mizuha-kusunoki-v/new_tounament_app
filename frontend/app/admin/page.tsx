"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import {
  ApiError,
  clearAdminToken,
  createAdminUser,
  deleteTournamentAsAdmin,
  getAdminToken,
  listAllTournaments,
} from "@/lib/api";
import { FORMAT_LABEL } from "@/lib/types";
import { useRequireAdmin } from "@/lib/useAdminAuth";

const STATUS_LABEL: Record<string, string> = {
  SETUP: "登録受付中",
  IN_PROGRESS: "進行中",
  COMPLETE: "終了",
};

export default function AdminDashboardPage() {
  const router = useRouter();
  const token = useRequireAdmin();

  const { data: tournaments, error, mutate } = useSWR(token ? "admin-tournaments" : null, () =>
    listAllTournaments()
  );

  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [creatingAdmin, setCreatingAdmin] = useState(false);
  const [createAdminMessage, setCreateAdminMessage] = useState<string | null>(null);

  useEffect(() => {
    if (error instanceof ApiError && !getAdminToken()) {
      router.push("/admin/login");
    }
  }, [error, router]);

  function handleLogout() {
    clearAdminToken();
    router.push("/admin/login");
  }

  async function handleDelete(id: string, name: string) {
    if (!window.confirm(`「${name}」を削除します。元に戻せません。よろしいですか？`)) return;
    setDeletingId(id);
    setActionError(null);
    try {
      await deleteTournamentAsAdmin(id);
      await mutate();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "削除に失敗しました");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleCreateAdmin(e: React.FormEvent) {
    e.preventDefault();
    setCreatingAdmin(true);
    setActionError(null);
    setCreateAdminMessage(null);
    try {
      const created = await createAdminUser(newUsername, newPassword);
      setCreateAdminMessage(`管理者「${created.username}」を追加しました`);
      setNewUsername("");
      setNewPassword("");
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "管理者の追加に失敗しました");
    } finally {
      setCreatingAdmin(false);
    }
  }

  if (!token) return null;
  if (error && getAdminToken()) return <div className="page error-banner">大会一覧の取得に失敗しました。</div>;
  if (!tournaments) return <div className="page">読み込み中...</div>;

  return (
    <div className="page">
      <div className="field-row" style={{ justifyContent: "space-between" }}>
        <h1>管理者ダッシュボード</h1>
        <button className="secondary" onClick={handleLogout}>
          ログアウト
        </button>
      </div>

      {actionError && <p className="error-banner">{actionError}</p>}

      <div className="field-row" style={{ justifyContent: "space-between" }}>
        <h2>登録済みの大会（{tournaments.length}件）</h2>
        <a href="/admin/create">
          <button>＋ 大会を作成</button>
        </a>
      </div>
      {tournaments.length === 0 && <p>まだ大会がありません。</p>}
      {tournaments.map((t) => (
        <div key={t.id} className="card match-card">
          <div>
            <strong>{t.name}</strong>
            <div className="round-heading">
              {FORMAT_LABEL[t.format]} / {STATUS_LABEL[t.status] ?? t.status} /{" "}
              {new Date(t.created_at).toLocaleString("ja-JP")}
            </div>
          </div>
          <a href={`/manage/${t.manage_token}`} target="_blank" rel="noopener noreferrer">
            <button className="secondary">管理画面を開く</button>
          </a>
          <button disabled={deletingId === t.id} onClick={() => handleDelete(t.id, t.name)}>
            {deletingId === t.id ? "削除中..." : "削除"}
          </button>
        </div>
      ))}

      <h2>管理者を追加</h2>
      {createAdminMessage && <p>{createAdminMessage}</p>}
      <form onSubmit={handleCreateAdmin}>
        <div className="field-row">
          <input
            type="text"
            placeholder="新しいユーザー名"
            value={newUsername}
            onChange={(e) => setNewUsername(e.target.value)}
          />
          <input
            type="password"
            placeholder="新しいパスワード（8文字以上）"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
          <button type="submit" disabled={creatingAdmin || !newUsername || newPassword.length < 8}>
            追加
          </button>
        </div>
      </form>
    </div>
  );
}
