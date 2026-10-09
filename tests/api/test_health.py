# ===================================================
# /health：サーバーと外部データ元（yfinance・J-Quants）の疎通確認
#
# アプリはホーム画面を開いたときにこれを呼び、NGなら
# 「Yahoo Finance に接続できません」等の帯を出す。
# ===================================================

from playwright.sync_api import APIRequestContext


def test_ヘルスチェックが正常(api: APIRequestContext):
    res = api.get("/health")
    assert res.ok, res.text()
    body = res.json()
    assert body.get("yfinance") == "ok", f"yfinance に接続できていない: {body}"
    # J-Quants の銘柄マスタが読めていないと、日本語での銘柄検索が0件になる
    assert body.get("jquants") == "ok", f"J-Quants の銘柄マスタが空: {body}"
