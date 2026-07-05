"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { adminLogin, ApiError } from "@/lib/api";

export default function AdminLoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await adminLogin(username, password);
      router.push("/admin");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "ログインに失敗しました");
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <h1>管理者ログイン</h1>
      {error && <p className="error-banner">{error}</p>}
      <form onSubmit={handleSubmit}>
        <div className="field-row">
          <input
            type="text"
            placeholder="ユーザー名"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        <div className="field-row">
          <input
            type="password"
            placeholder="パスワード"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <button type="submit" disabled={submitting || !username || !password}>
          ログイン
        </button>
      </form>
    </div>
  );
}
