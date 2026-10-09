# ===================================================
# AI系API
#
# OpenAI の料金がかかるので、既定では実行しない。
# RUN_AI_TESTS=1 を付けたときだけ実行する（tests/conftest.py 参照）。
# ===================================================

import pytest
from playwright.sync_api import APIRequestContext

pytestmark = pytest.mark.ai


def test_AI相談がJSONで判定を返す(api: APIRequestContext):
    res = api.post("/stock/consult", data={
        "code": "7203", "name": "トヨタ自動車",
        "direction": "買い", "trade_type": "現物", "period": "短期",
        "extra_questions": [],
        "price": 3000, "rsi": 50, "macd": 0, "ma5": 3000, "ma25": 3000,
    })
    assert res.ok, res.text()
    body = res.json()
    # AI系はエラーでも HTTP 200 + {"error": ...} で返る決まり
    assert "error" not in body, f"{body.get('error_type')}: {body.get('error_detail')}"
    assert body["judgment"] in ("適切", "要注意", "不適切"), body


def test_AI診断が確率の合計100で返る(api: APIRequestContext):
    res = api.post("/stock/swing_analysis", data={
        "code": "7203", "name": "トヨタ自動車", "period": "短期",
        "checks": {"technical": True, "fundamental": True},
    })
    assert res.ok, res.text()
    body = res.json()
    assert "error" not in body, f"{body.get('error_type')}: {body.get('error_detail')}"
    assert body["verdict"]["value"] in ("up", "sideways", "down")
    total = sum(body["probability"][k]["value"] for k in ("up", "sideways", "down"))
    assert 95 <= total <= 105, f"確率の合計が100から大きくずれている: {total}"
