# ===================================================
# ユーザー：投資プロファイル /user/profile
#
# 本物のユーザーのデータは読まない・書かない。
# 存在しないユーザーIDで呼んで、エラーにならないことだけを確認する
# （アプリはこの結果を見て、初回プロファイル設定を出すかを決めている）。
# ===================================================

from playwright.sync_api import APIRequestContext


def test_存在しないユーザーのプロファイルはexists_falseで返る(api: APIRequestContext):
    res = api.get("/user/profile", params={"userId": "e2e-nonexistent-user"})
    assert res.ok, res.text()
    assert res.json() == {"exists": False}
