# ===================================================
# お知らせ（アップデート告知のポップアップ）
#
# バックエンドの config/notices.py に追加してデプロイすると、
# アプリ起動時に未読分がポップアップで出る仕組み。
# アプリは「既読の version」を since に渡して未読分を取る。
# ===================================================

from playwright.sync_api import APIRequestContext


def _get(api: APIRequestContext, since: int) -> dict:
    res = api.get("/notices", params={"since": since})
    assert res.ok, res.text()
    return res.json()


def test_全件取得でversionの古い順に並ぶ(api: APIRequestContext):
    body = _get(api, 0)
    notices = body["notices"]
    assert notices, "お知らせが1件も無い"
    versions = [n["version"] for n in notices]
    assert versions == sorted(versions), versions
    assert body["latest_version"] == versions[-1]


def test_お知らせの形式がアプリの表示と合っている(api: APIRequestContext):
    for n in _get(api, 0)["notices"]:
        assert isinstance(n["version"], int)
        assert n["title"], n
        assert len(n["date"]) == 10  # YYYY-MM-DD
        assert isinstance(n["sections"], list) and n["sections"]
        for s in n["sections"]:
            assert "heading" in s
            assert isinstance(s["items"], list) and s["items"]
        assert "footer" in n


def test_最新を既読ならお知らせは出ない(api: APIRequestContext):
    latest = _get(api, 0)["latest_version"]
    assert _get(api, latest)["notices"] == []


def test_ひとつ前まで既読なら最新の1件だけ出る(api: APIRequestContext):
    latest = _get(api, 0)["latest_version"]
    notices = _get(api, latest - 1)["notices"]
    assert [n["version"] for n in notices] == [latest]
