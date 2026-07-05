"use client";

import { useRef, useState } from "react";
import { toPng } from "html-to-image";

interface Props {
  filename: string;
  buttonLabel: string;
  children: React.ReactNode;
}

export default function ImageCapture({ filename, buttonLabel, children }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    if (!ref.current) return;
    setSaving(true);
    setError(null);
    try {
      const dataUrl = await toPng(ref.current, { pixelRatio: 2, backgroundColor: "#ffffff" });
      const link = document.createElement("a");
      link.download = filename;
      link.href = dataUrl;
      link.click();
    } catch {
      setError("画像の生成に失敗しました");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="image-capture">
      <div ref={ref} className="image-capture-target">
        {children}
      </div>
      <button className="secondary" onClick={handleSave} disabled={saving}>
        {saving ? "画像を生成中..." : buttonLabel}
      </button>
      {error && <p className="error-banner">{error}</p>}
    </div>
  );
}
