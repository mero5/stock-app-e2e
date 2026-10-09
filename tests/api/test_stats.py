# ===================================================
# AI予測の成績：設定 → AI予測の成績 の画面で使うAPI
#
# AIを呼ぶAPIではないので料金はかからない。
# /stats/accuracy は既定だと「期限が来た予測の答え合わせ（書き込み）」もするので、
# テストでは evaluate=false で集計だけを取る。
# ===================================================

from playwright.sync_api import APIRequestContext

VERDICTS = {"up", "sideways", "down"}


def test_予測の一覧の形式が画面の表示と合っている(api: APIRequestContext):
    res = api.get("/stats/predictions", params={"limit": 10})
    assert res.ok, res.text()
    body = res.json()
    assert body["threshold_pct"] > 0
    preds = body["predictions"]
    assert len(preds) <= 10
    for p in preds:
        assert p["verdict"] in VERDICTS, p
        assert p["status"] in {"pending", "evaluated"}, p
        assert p["period"] in {"短期", "中期", "長期"}, p
        assert len(p["evaluate_at"]) == 10, p  # YYYY-MM-DD
        if p["status"] == "evaluated":
            assert p["actual_verdict"] in VERDICTS, p
            assert isinstance(p["is_correct"], bool), p


def test_予測の一覧は予測した日の新しい順(api: APIRequestContext):
    preds = api.get("/stats/predictions", params={"limit": 30}).json()["predictions"]
    dates = [p["predicted_at"] for p in preds]
    assert dates == sorted(dates, reverse=True), dates


def test_的中率の集計の形式が画面の表示と合っている(api: APIRequestContext):
    res = api.get("/stats/accuracy", params={"evaluate": "false"})
    assert res.ok, res.text()
    s = res.json()
    assert s["total"] == s["evaluated"] + s["pending"], s
    # 答え合わせをしていないので 0 件のまま
    assert s["just_evaluated"]["evaluated"] == 0
    if s["evaluated"] > 0:
        assert 0 <= s["accuracy"] <= 100
    for key in ["by_period", "by_verdict", "by_confidence", "by_prompt_version"]:
        assert isinstance(s[key], dict), key
