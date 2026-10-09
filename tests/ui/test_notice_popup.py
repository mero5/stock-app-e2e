# ===================================================
# 画面テスト：お知らせのポップアップ（NoticeDialog）
#
# バックエンドの config/notices.py に追加してデプロイすると、
# アプリ起動時に未読分が1件ずつポップアップで出る仕組み。
# 「最新の1つ前まで読んだ」状態にしてログインし、最新の1件が出て閉じられるかを確認する。
# ===================================================

import pytest
from playwright.sync_api import APIRequestContext, Page, expect

pytestmark = [pytest.mark.ui, pytest.mark.login]


@pytest.fixture(scope="module")
def latest_notice(api: APIRequestContext) -> dict:
    res = api.get("/notices", params={"since": 0})
    assert res.ok, res.text()
    return res.json()["notices"][-1]


@pytest.fixture
def last_seen_notice(latest_notice: dict) -> int:
    """conftest.py の既定（全部既読）を上書きして、最新の1件だけ未読にする"""
    return latest_notice["version"] - 1


def test_未読のお知らせがログイン後に出て閉じられる(logged_in: Page, latest_notice: dict):
    expect(logged_in.get_by_text(latest_notice["title"]).first).to_be_visible()
    logged_in.get_by_role("button", name="閉じる").click()
    expect(logged_in.get_by_text(latest_notice["title"])).to_have_count(0)
