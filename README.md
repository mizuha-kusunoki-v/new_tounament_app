# 2vs2 シャッフル型ダブルエリミネーション大会運営アプリ

設計の詳細は `C:\Users\KSeki\.claude\plans\ancient-tumbling-jellyfish.md` を参照。

## 構成

- `backend/` — FastAPI + SQLAlchemy + Alembic（SQLite、`DATABASE_URL`環境変数でPostgres等に切替可）
- `frontend/` — Next.js (App Router) + TypeScript + SWR

## ローカル起動

### backend

```
cd backend
python -m venv venv
./venv/Scripts/pip install -r requirements.txt   # Windows: venv\Scripts\pip
./venv/Scripts/python -m alembic upgrade head
./venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

テスト実行: `./venv/Scripts/python -m pytest app/tests/`

### frontend

```
cd frontend
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

- `/` — 大会作成（シングル/ダブルエリミネーションを選択可能。デフォルトはダブルエリミネーション）
- `/manage/{manageToken}` — 主催者用管理画面（参加者登録・開始・結果報告）
- `/view/{publicSlug}` — 参加者向け公開閲覧（ログイン不要、3秒間隔で自動更新）

シングルエリミネーションでは敗者復活ブラケット・グランドファイナルは一切生成されず、勝者ブラケットの優勝チームがそのまま大会優勝となる。チームの毎ラウンド再シャッフルはどちらの形式でも共通。

`manage_token` / `public_slug` は推測困難なトークンによる簡易的なアクセス制御であり、本格的なログイン認証ではない（MVP範囲外として計画済みの仕様）。
