# ===================================================
# 画面テスト：ログイン後の画面をひととおり開く
#
# test_logged_in.py（主要画面）に続いて、残りの画面も開けるかを確認する。
# 見るだけの操作に限る（保存・削除・AIの実行はしない）。
#
# ★押さないもの
#   ・「ウォッチリストに追加」「保存」など、データが変わるボタン
#   ・「AI分析を実行」「ニュースを取得する」「最新動画を要約する」「AI相場解説」
#     → OpenAI の料金がかかる
#   ・YouTube のチャンネル検索 → YouTube API の1日の無料枠を大きく使う
#
# ★AI予測の成績の画面は、開くと「期限が来た予測の答え合わせ」が走る
#   （アプリを普通に使ったときと同じ動き。データが壊れることはない）
# ===================================================

import re

import pytest
from playwright.sync_api import APIRequestContext, Page, expect

from tests.ui.helpers import bottom_tab, fill_text, open_settings_item, tab, text

pytestmark = [pytest.mark.ui, pytest.mark.login]

# 下のタブと、開いたときに上に出る画面名
TAB_TITLES = [
    ("YouTube", "YouTube要約"),
    ("スケジュール", "カレンダー"),
    ("マーケット", "マーケット"),
    ("設定", "設定"),
    ("ポートフォリオ", "ポートフォリオ診断"),
    ("ホーム", "株アプリ"),
]


def test_下の6つのタブを順番に全部開ける(logged_in: Page):
    for name, title in TAB_TITLES:
        bottom_tab(logged_in, name).click()
        expect(text(logged_in, title, exact=True)).to_be_visible()


# ---------- ホーム → 銘柄を追加（検索） ----------

def test_銘柄を検索すると候補が出る(logged_in: Page):
    logged_in.get_by_role("button", name="銘柄を追加").click()
    box = logged_in.get_by_role("textbox", name=re.compile("銘柄名 or コード"))
    fill_text(logged_in, box, "トヨタ")
    expect(text(logged_in, "トヨタ自動車")).to_be_visible()
    # テスト用アカウントはトヨタを登録済みなので「追加済み」になる
    expect(text(logged_in, "追加済み")).to_be_visible()


# ---------- 銘柄詳細の中身 ----------

def test_銘柄詳細のテクニカルとファンダに指標が出る(logged_in: Page):
    text(logged_in, "トヨタ").click()
    tab(logged_in, "テクニカル").click()
    expect(text(logged_in, "RSI（相対力指数）")).to_be_visible()
    tab(logged_in, "ファンダ").click()
    expect(text(logged_in, "PER（株価収益率）")).to_be_visible()


def test_銘柄詳細のAI分析とニュースはボタンが出る(logged_in: Page):
    """ボタンは押さない（OpenAI の料金がかかる）"""
    text(logged_in, "トヨタ").click()
    tab(logged_in, "AI分析").click()
    expect(text(logged_in, "AI分析を実行")).to_be_visible()
    tab(logged_in, "ニュース").click()
    expect(text(logged_in, "ニュースを取得する")).to_be_visible()


# ---------- YouTube・ポートフォリオ ----------

def test_YouTubeに検索と登録のタブがある(logged_in: Page):
    bottom_tab(logged_in, "YouTube").click()
    expect(text(logged_in, "YouTube要約", exact=True)).to_be_visible()
    for name in ["検索", "登録"]:
        expect(tab(logged_in, name)).to_be_visible()


def test_ポートフォリオに銘柄追加と注意書きが出る(logged_in: Page):
    bottom_tab(logged_in, "ポートフォリオ").click()
    expect(text(logged_in, "銘柄を追加")).to_be_visible()
    expect(text(logged_in, "サーバーに保存されません")).to_be_visible()


# ---------- 設定の中の画面 ----------

def test_設定に投資プロファイルの中身が出る(logged_in: Page):
    bottom_tab(logged_in, "設定").click()
    for name in ["投資期間", "取引種別", "リスク許容度", "投資経験"]:
        expect(text(logged_in, name)).to_be_visible()


def test_お知らせ履歴に過去のお知らせが出る(logged_in: Page, api: APIRequestContext):
    res = api.get("/notices", params={"since": 0})
    assert res.ok, res.text()
    latest = res.json()["notices"][-1]

    open_settings_item(logged_in, "お知らせ履歴")
    expect(text(logged_in, latest["title"])).to_be_visible()
    expect(logged_in.get_by_text(re.compile("お知らせを取得できませんでした"))).to_have_count(0)


def test_AI予測の成績が開ける(logged_in: Page):
    open_settings_item(logged_in, "AI予測の成績")
    # 判定済みの予測があれば的中率、無ければ案内が出る
    has_stats = logged_in.get_by_text("全体の的中率")
    empty = logged_in.get_by_text("まだ判定できる予測がありません")
    expect(has_stats.or_(empty).first).to_be_visible(timeout=90_000)
    expect(logged_in.get_by_text(re.compile("^エラー:"))).to_have_count(0)
