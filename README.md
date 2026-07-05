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

大会終了後（status=COMPLETE）は主催者画面・参加者公開画面の両方に「優勝カードを画像で保存」「ブラケット全体を画像で保存」ボタンが表示され、`html-to-image`でクライアント側のみでPNG画像として保存できる（サーバー保存はせず、都度その場で生成してダウンロードする方式）。X等への投稿はこの画像を手動で添付する想定。

`manage_token` / `public_slug` は推測困難なトークンによる簡易的なアクセス制御であり、本格的なログイン認証ではない（MVP範囲外として計画済みの仕様）。一般公開する場合、`manage_token`を含むURLの取り扱いには注意（漏洩するとその大会を誰でも操作できてしまう）。

### 管理者ダッシュボード（複数人主催向け）

- `/admin/login` — 管理者ログイン
- `/admin` — 全大会の一覧・削除、管理者アカウントの追加

`manage_token`/`public_slug`とは別の、ユーザー名+パスワードによる本格的な認証レイヤー。JWT（有効期限7日）を発行し、フロントは`localStorage`に保存して`Authorization`ヘッダーで送信する（Cookieセッションではない。理由: フロントとバックエンドが別ドメインのため）。

最初の管理者アカウントは環境変数`ADMIN_BOOTSTRAP_USERNAME`/`ADMIN_BOOTSTRAP_PASSWORD`から起動時に自動生成される（`admin_users`テーブルが空の場合のみ、冪等）。2人目以降はログイン後にダッシュボード上の「管理者を追加」フォームから追加する。ローカル開発では`backend/.env`にこの2つの環境変数を設定してから起動する。

## Renderへのデプロイ

ルートの `render.yaml` がBlueprintとして以下3つを定義済み:

- `new-tounament-db` — 管理型Postgres
- `new-tounament-backend` — FastAPI（デプロイのたびに`alembic upgrade head`を実行）
- `new-tounament-frontend` — Next.js

手順:

1. GitHubにpush済みのこのリポジトリをRenderに接続し、「New +」→「Blueprint」から`render.yaml`を検出させて作成する。
2. 両サービスのデプロイ完了後、URLがそれぞれ `https://new-tounament-backend.onrender.com` / `https://new-tounament-frontend.onrender.com` になっているか確認する（Renderダッシュボードでサービス名を変えた場合は`render.yaml`内の`ALLOWED_ORIGINS`と`NEXT_PUBLIC_API_BASE_URL`を実際のURLに書き換えて再デプロイが必要）。
3. `NEXT_PUBLIC_API_BASE_URL`はNext.jsのビルド時に埋め込まれる値のため、後から環境変数を変更した場合は再ビルド（Manual Deploy）が必要。
4. `new-tounament-backend`のEnvironmentタブで`ADMIN_JWT_SECRET`が自動生成されているか確認し、`ADMIN_BOOTSTRAP_USERNAME`/`ADMIN_BOOTSTRAP_PASSWORD`を手動で追加してManual Deployを実行する（このBlueprintは既にデプロイ済みのため、`sync: false`の入力プロンプトが自動で出ない場合がある）。これで最初の管理者アカウントが作成され、`/admin/login`からログインできるようになる。

**Renderの無料プランの制約（要確認）:**
- 無料Postgresは**作成から30日で期限切れ**、その後14日間の猶予期間内にアップグレードしないと削除される。継続的にデータを残したい場合は有料プラン（`basic-1gb`等）への変更を検討。
- 無料Webサービスは**15分間アクセスがないとスリープ**し、次のアクセス時に起動に数十秒かかる。
- ワークスペース全体で月750時間の無料枠。

本番運用でデータを保持し続けたい場合は、`render.yaml`の`databases.plan`を無料以外に変更することを推奨。
