# ===================================================
# テスト結果の記録（○×の一覧を作るための材料）
#
# テストが1件終わるごとに「どのテストが・どうなったか・理由」を記録し、
# 最後に JSON ファイルに書き出す。scripts/summary.py がこれを読んで、
# GitHub Actions の実行結果ページに機能ごとの○×の表を出す。
#
# 環境変数 E2E_RESULTS に書き出し先を入れたときだけ動く（ローカルでは何もしない）。
# tests/conftest.py の pytest_plugins で読み込む。
# ===================================================

import json
import os
from pathlib import Path

_results: list[dict] = []


def _status(report) -> str:
    """pytest の結果を ○× 表の区分に直す"""
    xfail = hasattr(report, "wasxfail")
    if report.passed:
        return "xpass" if xfail else "pass"
    if report.skipped:
        return "xfail" if xfail else "skip"
    return "fail"


def _reason(report, status: str) -> str:
    """表に1行で添える理由（失敗の要点・スキップや xfail の理由）"""
    if status in ("xfail", "xpass"):
        return report.wasxfail
    if status == "skip" and isinstance(report.longrepr, tuple):
        return report.longrepr[2].removeprefix("Skipped: ")
    if status == "fail":
        crash = getattr(report.longrepr, "reprcrash", None)
        message = crash.message if crash else str(report.longrepr)
        return message.strip().splitlines()[0][:150]
    return ""


def pytest_runtest_logreport(report):
    # 本体（call）の結果を記録する。準備（setup）で失敗・スキップしたときは本体が動かないので、そちらを記録する
    if report.when == "call" or (report.when == "setup" and not report.passed):
        status = _status(report)
        _results.append({"nodeid": report.nodeid, "status": status, "reason": _reason(report, status)})


def pytest_sessionfinish(session, exitstatus):
    out = os.getenv("E2E_RESULTS")
    if not out:
        return
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_results, ensure_ascii=False, indent=2), encoding="utf-8")
