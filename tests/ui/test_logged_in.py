# ===================================================
# 画面テスト：ログイン後の主要な画面
#
# テスト専用アカウント（E2E_EMAIL / E2E_PASSWORD）でログインして、
# ユーザーがよく使う画面が表示されるかを確認する。
#
# ★テスト用アカウントの前提
#   ・ウォッチリストに「トヨタ自動車（7203）」を1件登録しておく（銘柄詳細のテストで使う）
#   ・AI分析は料金がかかるので、ここでは実行しない（タブが開くところまで）
#
# ★2026-10-10 時点の状態
#   テスト用アカウントがまだ無いので、このファイルは一度も実行できていない。
#   画面の要素の探し方（特に下のタブ）は、初回の実行で調整が必要になる可能性がある。
# ===================================================

import re

import pytest
from playwright.sync_api import Page, expect

from tests.ui.helpers import bottom_tab

pytestmark = [pytest.mark.ui, pytest.mark.login]

TABS = ["ホーム", "YouTube", "スケジュール", "マーケット", "設定", "ポートフォリオ"]


def test_ログインするとホーム画面と下の6つのタブが出る(logged_in: Page):
    expect(logged_in.get_by_text("株アプリ", exact=True).first).to_be_visible()
    for name in TABS:
        expect(bottom_tab(logged_in, name)).to_be_visible()


def test_ホームにウォッチリストの銘柄と株価が出る(logged_in: Page):
    expect(logged_in.get_by_text(re.compile("トヨタ")).first).to_be_visible()
    # 株価が取れていないときは「---」になる（K-25・K-27 の症状）
    expect(logged_in.get_by_text("---", exact=True)).to_have_count(0)


def test_銘柄をタップすると詳細画面の5つのタブが出る(logged_in: Page):
    logged_in.get_by_text(re.compile("トヨタ")).first.click()
    for name in ["チャート", "テクニカル", "ファンダ", "AI分析", "ニュース"]:
        expect(logged_in.get_by_text(name, exact=True).first).to_be_visible()


def test_スケジュールで直近の予定に切り替えられる(logged_in: Page):
    bottom_tab(logged_in, "スケジュール").click()
    expect(logged_in.get_by_text("カレンダー", exact=True).first).to_be_visible()
    logged_in.get_by_text("直近の予定", exact=True).first.click()
    # 直近の予定には「あと◯日」が付く
    expect(logged_in.get_by_text(re.compile(r"あと\d+日")).first).to_be_visible()


def test_マーケットにセクター騰落率が出る(logged_in: Page):
    bottom_tab(logged_in, "マーケット").click()
    expect(logged_in.get_by_text(re.compile("セクター騰落率")).first).to_be_visible()


def test_設定に投資プロファイル_お知らせ履歴_AI予測の成績がある(logged_in: Page):
    bottom_tab(logged_in, "設定").click()
    for name in ["投資プロファイル", "お知らせ履歴", "AI予測の成績"]:
        expect(logged_in.get_by_text(name).first).to_be_visible()
