# ===================================================
# マーケット：スケジュール画面のイベント・日経平均・セクター騰落
# ===================================================

from datetime import date, timedelta

import pytest
from playwright.sync_api import APIRequestContext


def _events(api: APIRequestContext, year: int, month: int) -> list:
    res = api.get("/market/events", params={"year": year, "month": month})
    assert res.ok, res.text()
    return res.json()


def _second_friday(year: int, month: int) -> date:
    d = date(year, month, 1)
    fridays = [d + timedelta(days=i) for i in range(31)
               if (d + timedelta(days=i)).month == month and (d + timedelta(days=i)).weekday() == 4]
    return fridays[1]


# ---------- /market/events ----------

def test_2026年10月のFOMCと日銀が出る(api: APIRequestContext):
    events = _events(api, 2026, 10)
    pairs = {(e["date"], e["type"]) for e in events}
    assert ("2026-10-28", "fomc") in pairs
    assert ("2026-10-28", "boj") in pairs


@pytest.mark.parametrize("year,month", [(2026, 3), (2026, 10), (2026, 12)])
def test_SQは第2金曜で3_6_9_12月はメジャーSQ(api: APIRequestContext, year, month):
    events = _events(api, year, month)
    sq = [e for e in events if e["type"] in ("sq", "major_sq")]
    assert len(sq) == 1, sq
    assert sq[0]["date"] == str(_second_friday(year, month))
    expected = "major_sq" if month in (3, 6, 9, 12) else "sq"
    assert sq[0]["type"] == expected


def test_日本の祝日が出る(api: APIRequestContext):
    events = _events(api, 2026, 11)
    holidays = {e["date"] for e in events if e["type"] == "holiday_jp"}
    assert "2026-11-03" in holidays, "文化の日が出ていない"
    assert "2026-11-23" in holidays, "勤労感謝の日が出ていない"


def test_イベントの項目がそろっている(api: APIRequestContext):
    for e in _events(api, 2026, 10):
        assert {"date", "label", "type", "color"} <= set(e), e


@pytest.mark.pending_deploy
@pytest.mark.xfail(reason="stock_app の PR「FOMC・日銀の2027年の日程を追加」がデプロイされるまでは失敗する（課題 K-01）", strict=False)
def test_2027年のFOMCと日銀が出る(api: APIRequestContext):
    events = _events(api, 2027, 1)
    pairs = {(e["date"], e["type"]) for e in events}
    assert ("2027-01-27", "fomc") in pairs, "2027年1月のFOMCが無い"
    assert ("2027-01-22", "boj") in pairs, "2027年1月の日銀会合が無い"


# ---------- /market/upcoming（直近の予定） ----------

def test_直近の予定は日付順で今日以降(api: APIRequestContext, today_jst):
    res = api.get("/market/upcoming", params={"months": 3})
    assert res.ok, res.text()
    events = res.json()
    assert events, "直近3ヶ月のイベントが0件"
    dates = [e["date"] for e in events]
    assert dates == sorted(dates), "日付順になっていない"
    # サーバーがUTCで動いていると「今日」が日本時間より最大1日前になるので、ここでは1日の誤差を許す
    # （厳密な確認は下の test_直近の予定の今日が日本時間）
    assert dates[0] >= str(today_jst - timedelta(days=1)), dates[0]


@pytest.mark.pending_deploy
@pytest.mark.xfail(reason="stock_app の PR「日付・時刻を日本時間（JST）基準に統一」がデプロイされるまでは、日本時間0〜9時に失敗しうる（課題 K-02）", strict=False)
def test_直近の予定の今日が日本時間(api: APIRequestContext, today_jst):
    res = api.get("/market/upcoming", params={"months": 1})
    dates = [e["date"] for e in res.json()]
    assert all(d >= str(today_jst) for d in dates), f"日本時間の今日（{today_jst}）より前のイベントが入っている: {dates[:3]}"


# ---------- /nikkei/monthly ----------

def test_日経平均の月次データ(api: APIRequestContext):
    res = api.get("/nikkei/monthly", params={"year": 2026, "month": 9})
    assert res.ok, res.text()
    data = res.json()
    assert len(data) >= 15, f"9月の営業日分が無い: {len(data)}日"
    for day, v in data.items():
        assert day.startswith("2026-09")
        assert v["close"] > 0
        assert {"change", "change_pct"} <= set(v)


# ---------- /market/sectors ----------

@pytest.mark.pending_deploy
@pytest.mark.xfail(reason="stock_app の PR「日本株の株価・指標が null になる不具合を修正」がデプロイされるまでは、yfinanceが最新日を空の行で返す日に失敗する（課題 K-27）", strict=False)
def test_セクター騰落が日米とも騰落率の降順(api: APIRequestContext):
    res = api.get("/market/sectors", params={"period": "5d"})
    assert res.ok, res.text()
    body = res.json()
    for region, minimum in (("jp", 10), ("us", 8)):
        items = body[region]
        assert len(items) >= minimum, f"{region} のセクターが少ない: {len(items)}"
        pcts = [s["change_pct"] for s in items]
        missing = [s["name"] for s in items if s["change_pct"] is None]
        assert not missing, f"{region} の騰落率が空のセクター: {missing}"
        assert pcts == sorted(pcts, reverse=True), f"{region} が降順になっていない"
        assert {"name", "ticker", "change_pct", "trend_5d"} <= set(items[0])


# ---------- /market/breadth（騰落レシオ。AIに渡す指標の1つ） ----------

def test_騰落レシオが値上がり数と値下がり数から計算されている(api: APIRequestContext):
    res = api.get("/market/breadth")
    assert res.ok, res.text()
    b = res.json()
    assert b["advancers"] >= 0 and b["decliners"] >= 0, b
    assert b["advancers"] + b["decliners"] > 0, f"銘柄数が0（データが取れていない）: {b}"
    if b["decliners"] > 0:
        assert b["advance_decline_ratio"] == pytest.approx(b["advancers"] / b["decliners"], abs=0.01), b


@pytest.mark.pending_deploy
@pytest.mark.xfail(reason="K-43：権利落ち日が「目安」で祝日・年末がずれる（stock_app#36 のデプロイ待ち）", strict=False)
def test_権利落ち日が東証の休業日をふまえた日付で出る(api: APIRequestContext):
    # 2026年12月は 12/31 が休場なので、権利確定日 12/30・権利落ち日 12/29。
    # 以前は土日だけで数えて 12/30 を「権利落ち日（目安）」として出していた
    rights = [e for e in _events(api, 2026, 12) if e["type"] == "rights"]
    assert [(e["date"], e["label"]) for e in rights] == [("2026-12-29", "権利落ち日")], rights


# ---------- 2026-10-10（2回目の調査）の不具合の再発防止 ----------

@pytest.mark.pending_deploy
@pytest.mark.xfail(reason="K-45：日本のセクターETFの名前が17本中15本ずれている（stock_app#38 のデプロイ待ち）", strict=False)
def test_日本のセクターETFの名前がTOPIX17の業種と合っている(api: APIRequestContext):
    # JPX の ETF 一覧：1617 は「TOPIX-17 食品」、1625 は「電機・精密」、1631 は「銀行」
    res = api.get("/market/sectors", params={"period": "5d"})
    assert res.ok, res.text()
    names = {s["ticker"]: s["name"] for s in res.json()["jp"]}
    expected = {"1617.T": "食品", "1625.T": "電機・精密", "1631.T": "銀行"}
    for ticker, name in expected.items():
        if ticker in names:  # yfinance で取れなかったETFは返らないことがある
            assert names[ticker] == name, f"{ticker} の名前が {names[ticker]}（正しくは {name}）"
    assert set(expected) & set(names), f"確認するETFが1本も返らない: {names}"
