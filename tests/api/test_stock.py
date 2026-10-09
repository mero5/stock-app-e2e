# ===================================================
# 銘柄まわり：検索・銘柄名・株価・詳細（チャート用データ）
#
# 銘柄コードの形式が場所によって違うので、その変換が
# 壊れていないかを重点的に確認する。
#   J-Quants（検索結果）: 72030（5桁）
#   画面表示            : 7203
#   yfinance            : 7203.T
# ===================================================

import math
import re

import pytest
from playwright.sync_api import APIRequestContext


# ---------- 検索 /search ----------

def test_日本語で検索するとJQuantsの5桁コードで返る(api: APIRequestContext):
    res = api.get("/search", params={"q": "トヨタ"})
    assert res.ok, res.text()
    results = res.json()
    assert isinstance(results, list) and results, "トヨタで1件もヒットしない"
    assert len(results) <= 20, "最大20件のはず"
    codes = [r["code"] for r in results]
    assert "72030" in codes, f"トヨタ自動車（72030）が含まれない: {codes}"
    assert all(r["market"] == "JP" for r in results)


def test_数字で検索するとコードの前方一致で返る(api: APIRequestContext):
    res = api.get("/search", params={"q": "7203"})
    assert res.ok, res.text()
    results = res.json()
    assert results, "7203 で1件もヒットしない"
    assert all(r["code"].startswith("7203") for r in results), results


def test_英字で検索すると米国株が返る(api: APIRequestContext):
    res = api.get("/search", params={"q": "Apple"})
    assert res.ok, res.text()
    results = res.json()
    assert any(r["code"] == "AAPL" and r["market"] == "US" for r in results), results


def test_空文字で検索すると空のリスト(api: APIRequestContext):
    res = api.get("/search", params={"q": ""})
    assert res.ok, res.text()
    assert res.json() == []


# ---------- 銘柄名 /stock/name ----------

@pytest.mark.parametrize("code", ["7203", "72030"])
def test_4桁でも5桁でも銘柄名が取れる(api: APIRequestContext, code: str):
    res = api.get("/stock/name", params={"code": code})
    assert res.ok, res.text()
    body = res.json()
    assert body["code"] == code
    assert "トヨタ" in body["name"], f"銘柄名が取れていない（コードのまま返っている？）: {body}"


# ---------- 株価 /stock/price（ホーム画面の一覧用） ----------

@pytest.mark.parametrize("code", [
    pytest.param("7203", marks=[pytest.mark.pending_deploy, pytest.mark.xfail(reason="K-27：日本株の最新日が空の行で返ると price が null（修正PRのデプロイ待ち）", strict=False)]),
    pytest.param("72030", marks=[pytest.mark.pending_deploy, pytest.mark.xfail(reason="K-27：同上", strict=False)]),
    "AAPL",
])
def test_株価と前日比が取れる(api: APIRequestContext, code: str):
    res = api.get("/stock/price", params={"code": code})
    assert res.ok, res.text()
    body = res.json()
    assert isinstance(body["price"], (int, float)) and body["price"] > 0, body
    # 前日比は休日明けなどで取れないこともあるが、取れたときは数値であること
    if body["change_pct"] is not None:
        assert isinstance(body["change_pct"], (int, float))


# ---------- 詳細 /stock/detail（詳細画面のチャート・指標） ----------

@pytest.mark.pending_deploy
@pytest.mark.xfail(reason="stock_app の PR「日本株の株価・指標が null になる不具合を修正」がデプロイされるまでは、yfinanceが最新日を空の行で返す日に失敗する（課題 K-27）", strict=False)
def test_詳細データにチャート用のローソク足と指標が入っている(api: APIRequestContext):
    res = api.get("/stock/detail", params={"code": "7203"})
    assert res.ok, res.text()
    body = res.json()
    assert "error" not in body, body.get("error")

    assert body["price"] and body["price"] > 0
    assert body["currency"] == "JPY"

    candles = body["candles"]
    # 3ヶ月分（営業日で約60本）
    assert len(candles) >= 40, f"ローソク足が少なすぎる: {len(candles)}本"

    required = {"date", "open", "high", "low", "close", "volume",
                "ma5", "ma25", "bb_upper", "bb_middle", "bb_lower", "macd", "rsi"}
    assert required <= set(candles[-1]), f"足りない項目: {required - set(candles[-1])}"

    last = candles[-1]
    assert last["close"] is not None, f"最新のローソク足（{last['date']}）の終値が空"
    assert last["low"] <= last["close"] <= last["high"]
    # RSI は 0〜100
    assert 0 <= last["rsi"] <= 100, last["rsi"]
    # 日付は古い順
    dates = [c["date"] for c in candles]
    assert dates == sorted(dates)


def test_詳細データにNaNが含まれない(api: APIRequestContext):
    """yfinance の欠損値（NaN）はJSONにできないので、null に変換されているはず"""
    res = api.get("/stock/detail", params={"code": "7203"})
    body = res.json()

    def walk(v):
        if isinstance(v, float):
            assert not math.isnan(v) and not math.isinf(v)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(body)


# ---------- 銘柄イベント /stock/events（スケジュール画面の決算・配当） ----------

def test_ウォッチリスト銘柄の決算と配当の予定が取れる(api: APIRequestContext):
    res = api.get("/stock/events", params={"codes": "7203,AAPL"})
    assert res.ok, res.text()
    events = res.json()
    assert events, "トヨタ・Apple のどちらも予定が取れていない"
    for e in events:
        assert e["code"] in {"7203", "AAPL"}, e
        assert e["type"] in {"earnings", "ex_dividend"}, e
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"]), e
        assert e["label"], e
