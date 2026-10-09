# ===================================================
# テスト結果を「機能ごとの○×の表」にする
#
# 使い方：python scripts/summary.py <結果のJSON> <見出し>
#   tests/result_recorder.py が書き出した JSON を読み、Markdown の表を出す。
#   GitHub Actions では $GITHUB_STEP_SUMMARY に追記して、実行結果ページに表示する。
#
# ★新しいテストファイルを足したら、下の FEATURES に「何の機能のテストか」を1行足す
# ===================================================

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# テストファイル → 何の機能のテストか（表の見出し）。上から順に表示する
FEATURES = {
    "tests/ui/test_login_screen.py": "画面：ログイン画面（入力チェック・パスワード表示）",
    "tests/ui/test_logged_in.py": "画面：ログイン後の主要画面（ホーム・銘柄詳細・スケジュール・マーケット・設定）",
    "tests/ui/test_logged_in_screens.py": "画面：ひととおりの画面（タブ移動・検索・銘柄詳細の中身・YouTube・ポートフォリオ・設定の中）",
    "tests/ui/test_notice_popup.py": "画面：お知らせのポップアップ",
    "tests/api/test_health.py": "API：サーバーの稼働確認",
    "tests/api/test_stock.py": "API：銘柄検索・株価・銘柄詳細・決算日",
    "tests/api/test_market.py": "API：スケジュール（FOMC・日銀・SQ・祝日）・日経平均・セクター騰落・騰落レシオ",
    "tests/api/test_notices.py": "API：お知らせ",
    "tests/api/test_stats.py": "API：AI予測の成績",
    "tests/api/test_user.py": "API：投資プロファイル",
    "tests/api/test_ai.py": "API：AI分析・AI相談（料金がかかるので手動でONのときだけ）",
}

MARKS = {
    "pass": "✅",
    "fail": "❌",
    "xfail": "⏳",
    "xpass": "🎉",
    "skip": "⏭️",
}
LEGEND = "✅ 成功 ／ ❌ 失敗 ／ ⏳ 直す修正のデプロイ待ち（失敗して当然） ／ 🎉 デプロイ待ちだったが成功した（印を外す合図） ／ ⏭️ 実行しなかった"


def readable_name(nodeid: str) -> str:
    """tests/api/test_stock.py::test_株価と前日比が取れる[7203] → 株価と前日比が取れる（7203）"""
    name = nodeid.split("::")[-1].removeprefix("test_")
    name = re.sub(r"\[chromium\]$", "", name)
    name = re.sub(r"\[(.+)\]$", r"（\1）", name)
    return name.replace("_", "・")


def build(results: list[dict], title: str) -> str:
    counts = defaultdict(int)
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        counts[r["status"]] += 1
        groups[r["nodeid"].split("::")[0]].append(r)

    total = " ／ ".join(f"{MARKS[k]} {counts[k]}" for k in MARKS if counts[k])
    verdict = "❌ 失敗あり" if counts["fail"] else "✅ 問題なし"
    lines = [f"## {title}：{verdict}", "", f"**{total}**（全{len(results)}件）", "", LEGEND, ""]

    order = [f for f in FEATURES if f in groups] + sorted(f for f in groups if f not in FEATURES)
    for file in order:
        rows = groups[file]
        bad = sum(r["status"] == "fail" for r in rows)
        ok = sum(r["status"] in ("pass", "xpass") for r in rows)
        mark = "❌" if bad else ("✅" if ok else "⏭️")
        lines += [
            f"### {mark} {FEATURES.get(file, file)}（{ok}/{len(rows)} 成功）",
            "",
            "| 結果 | 確認していること | 補足 |",
            "|:---:|---|---|",
        ]
        for r in rows:
            reason = r["reason"].replace("|", "｜").replace("\n", " ")
            lines.append(f"| {MARKS[r['status']]} | {readable_name(r['nodeid'])} | {reason} |")
        lines.append("")

    if counts["fail"]:
        lines.append("> 失敗の詳しい様子は、このページ下の **Artifacts** のレポート（画面テストはスクリーンショット・トレース付き）で見られる。")
    return "\n".join(lines) + "\n"


def main() -> None:
    path, title = Path(sys.argv[1]), sys.argv[2]
    if not path.exists():
        markdown = f"## {title}：⚠️ 結果がありません\n\nテストが始まる前に止まった可能性があります。ログを確認してください。\n"
    else:
        markdown = build(json.loads(path.read_text(encoding="utf-8")), title)

    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(markdown)
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(markdown)


if __name__ == "__main__":
    main()
