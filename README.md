# stock-app-e2e

株分析アプリ [mero5/stock_app](https://github.com/mero5/stock_app) の **E2Eテスト**（Playwright × pytest）。
本番のバックエンド（FastAPI on AWS Lambda）を外から呼び出し、アプリが使っているAPIが正しく動いているかを確認する。GitHub Actions で自動実行する。

> E2Eテスト（End to End）＝ 実際に動いているシステムを、利用者と同じ入口から通しで確認するテスト。

## 何をテストしているか

```
GitHub Actions（push / PR / 平日9時 / 手動 / stock_appのデプロイ後）
        │
        ▼
pytest ＋ Playwright（APIRequestContext）
        │ HTTPS
        ▼
stock_app バックエンド（Lambda Function URL）── yfinance / J-Quants / DynamoDB / OpenAI
```

| ファイル | 対象API | 主な確認内容 |
|---|---|---|
| `tests/api/test_health.py` | `/health` | yfinance・J-Quants の疎通 |
| `tests/api/test_stock.py` | `/search` `/stock/name` `/stock/price` `/stock/detail` `/stock/events` | 日本語・数字・英字での検索、銘柄コードの4桁/5桁の変換、株価・ローソク足・RSI、NaNが混ざらないこと、決算・配当の予定 |
| `tests/api/test_market.py` | `/market/events` `/market/upcoming` `/nikkei/monthly` `/market/sectors` `/market/breadth` | FOMC・日銀・SQ（第2金曜）・祝日、直近の予定の並び順、セクター騰落の並び順、騰落レシオの計算 |
| `tests/api/test_notices.py` | `/notices` | アプリ内のお知らせ（アップデート告知）の形式と、既読管理（`since`） |
| `tests/api/test_stats.py` | `/stats/predictions` `/stats/accuracy` | AI予測の成績画面の形式（答え合わせの書き込みをしないよう `evaluate=false`） |
| `tests/api/test_user.py` | `/user/profile`（GET） | 存在しないユーザーで `exists: false` が返ること（本物のユーザーのデータは読まない） |
| `tests/api/test_ai.py` | `/stock/consult` `/stock/swing_analysis` | AIの回答の形式（**料金がかかるので既定ではスキップ**） |

### マーカー（テストの分類）

| マーカー | 意味 |
|---|---|
| `ai` | OpenAI を呼ぶテスト。`RUN_AI_TESTS=1` のときだけ実行する |
| `pending_deploy` | stock_app の**未デプロイの修正PR**で直る予定のテスト。`xfail`（失敗するのが分かっている）として記録し、デプロイされて成功するようになったら（`XPASS`）マーカーを外す |

## ローカルでの実行

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
```

| やりたいこと | コマンド |
|---|---|
| HTMLレポートを出す | `pytest --html=reports/report.html --self-contained-html` |
| AIテストも実行する | `$env:RUN_AI_TESTS="1"; pytest` |
| 別の環境を叩く | `$env:STOCK_API_URL="https://..."; pytest` |
| 1ファイルだけ | `pytest tests/api/test_market.py` |

## GitHub Actions

`.github/workflows/e2e.yml`

| きっかけ | 内容 |
|---|---|
| main への push、PR | テストコードの変更を確認 |
| 平日 9:00（JST） | 本番のAPIが壊れていないかの定期チェック |
| 手動（Run workflow） | `run_ai` にチェックを入れると AI テストも実行 |
| `repository_dispatch`（`stock-app-deployed`） | stock_app のデプロイ後に呼ぶ想定（連携は今後） |

### 結果の見方

Actions の実行結果ページを開くと、先頭（Summary）に**機能ごとの○×の表**が出る（APIテスト・画面テストそれぞれ）。

| 記号 | 意味 |
|:---:|---|
| ✅ | 成功 |
| ❌ | 失敗（補足欄に理由の1行目） |
| ⏳ | 直す修正のデプロイ待ち（`pending_deploy` ＋ `xfail`。失敗して当然） |
| 🎉 | デプロイ待ちだったが成功した → 直ったので `pending_deploy`・`xfail` を外す |
| ⏭️ | 実行しなかった（AIテスト・テスト用アカウント未設定など） |

- 表は `tests/result_recorder.py`（結果を JSON に記録）→ `scripts/summary.py`（表にする）で作っている
- **新しいテストファイルを足したら、`scripts/summary.py` の `FEATURES` に「何の機能のテストか」を1行足す**（無いとファイル名がそのまま見出しになる）
- 表の「確認していること」はテスト関数名（`test_` を除き、`_` を「・」に）。名前は「何ができること」を日本語で書く

詳しいレポート（HTML。画面テストは失敗時のスクリーンショット・トレース付き）は、同じページの **Artifacts** からダウンロードできる。

## これまでに見つけた不具合

| 日付 | 内容 | 課題 |
|---|---|---|
| 2026-10-10 | yfinance が日本株の最新日を「値が空の行」で返し、**日本株の株価・ローソク足・セクター騰落が null** になっていた | K-27（stock_app で修正PR作成済み） |

## 画面テスト（Flutter Web × Playwright）

stock_app を **Flutter Web** でビルドしてブラウザで開き、Playwright で実際に画面を操作する。

| ファイル | 内容 | 実行に必要なもの |
|---|---|---|
| `tests/ui/test_login_screen.py` | ログイン画面の表示、未入力時のエラー、パスワードの表示切替、注意書き | `STOCK_APP_WEB_URL` |
| `tests/ui/test_logged_in.py` | ログイン → ホーム（6タブ・ウォッチリストの株価）→ 銘柄詳細の5タブ → スケジュール「直近の予定」→ マーケット → 設定 | ＋ `E2E_EMAIL` / `E2E_PASSWORD`（テスト専用アカウント） |
| `tests/ui/test_logged_in_screens.py` | 下の6タブを順番に全部開く、銘柄検索、銘柄詳細のテクニカル・ファンダ・AI分析・ニュース、YouTube、ポートフォリオ、投資プロファイル、お知らせ履歴、AI予測の成績（**見るだけ。保存・削除・AIの実行はしない**） | 同上 |
| `tests/ui/test_notice_popup.py` | 最新のお知らせだけ未読にしてログイン → ポップアップが出て閉じられる | 同上 |

### Flutter Web を Playwright で操作する工夫
Flutter Web は画面を canvas（絵）に描くので、そのままではボタンを見つけられない。
画面の裏にある隠しボタン「Enable accessibility」（`flt-semantics-placeholder`）を押すと、セマンティクス（読み上げ用の要素情報）が有効になり、`get_by_role("button", name="ログイン")` のように探せる。**アプリ側のコードは変えていない**（`tests/ui/helpers.py` の `enable_semantics()`）。

### ローカルでの実行
```powershell
# stock_app 側
flutter build web --release
python -m http.server 8765 --bind 127.0.0.1 --directory build/web

# このリポジトリ側（初回だけブラウザをインストール）
.\.venv\Scripts\python.exe -m playwright install chromium
$env:STOCK_APP_WEB_URL="http://127.0.0.1:8765/"
.\.venv\Scripts\python.exe -m pytest tests/ui --headed   # --headed でブラウザの動きが見える
```

### テスト専用アカウントの準備（ログイン後のテストを動かすため）
1. アプリで新規登録する（テスト専用のメールアドレス）。ウォッチリストに「トヨタ自動車（7203）」を1件登録しておく
2. GitHub のこのリポジトリ → Settings → Secrets and variables → Actions → New repository secret
   - `E2E_EMAIL`：テスト用アカウントのメールアドレス
   - `E2E_PASSWORD`：そのパスワード

未登録の間は、ログイン後のテストは自動でスキップされる。

## 今後
- テストレポートを GitHub Pages で公開し、失敗したら Discord に通知する
- stock_app のデプロイ後に `repository_dispatch` で自動実行する

## ルール

- PR の本文は `.github/pull_request_template.md` に沿って書く
- **PR のマージはレビュー後に mero5 が行う**（作成者はマージしない）
