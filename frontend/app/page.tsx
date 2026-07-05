"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createTournament, ApiError } from "@/lib/api";
import type { TournamentFormat } from "@/lib/types";

export default function Home() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [format, setFormat] = useState<TournamentFormat>("DOUBLE_ELIMINATION");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await createTournament(name.trim(), format);
      router.push(`/manage/${created.manage_token}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "大会の作成に失敗しました");
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <h1>2vs2 シャッフル大会を作成</h1>
      <p>
        参加者を1人ずつ登録し、ラウンドごとにランダムでペアを組み直すトーナメントを運営できます。
      </p>
      {error && <p className="error-banner">{error}</p>}
      <form onSubmit={handleSubmit}>
        <div className="field-row">
          <input
            type="text"
            placeholder="大会名"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="field-row" role="radiogroup" aria-label="大会形式">
          <label>
            <input
              type="radio"
              name="format"
              value="DOUBLE_ELIMINATION"
              checked={format === "DOUBLE_ELIMINATION"}
              onChange={() => setFormat("DOUBLE_ELIMINATION")}
            />
            ダブルエリミネーション（敗者復活あり・推奨）
          </label>
          <label>
            <input
              type="radio"
              name="format"
              value="SINGLE_ELIMINATION"
              checked={format === "SINGLE_ELIMINATION"}
              onChange={() => setFormat("SINGLE_ELIMINATION")}
            />
            シングルエリミネーション（敗者復活なし）
          </label>
        </div>
        <button type="submit" disabled={submitting || !name.trim()}>
          作成
        </button>
      </form>
    </div>
  );
}
