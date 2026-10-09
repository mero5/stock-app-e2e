# ===================================================
# 画面テスト：ログイン画面（ログイン前）
#
# Cognito（認証サーバー）に問い合わせる前の、画面だけで完結する動きを確認する。
# 実際のログイン・新規登録は行わない（アカウントが作られたり、ロックされたりしないように）。
# ===================================================

import re

import pytest
from playwright.sync_api import Page, expect

from tests.ui.helpers import dismiss_dialog, fill_text

pytestmark = pytest.mark.ui

EMAIL = re.compile("example@email.com")
PASSWORD = re.compile("8文字以上")


def test_ログイン画面が表示される(app: Page):
    expect(app.get_by_text("株アプリ", exact=True)).to_be_visible()
    expect(app.get_by_text("投資情報をシンプルに")).to_be_visible()
    expect(app.get_by_role("textbox", name=EMAIL)).to_be_visible()
    expect(app.get_by_role("textbox", name=PASSWORD)).to_be_visible()
    expect(app.get_by_role("button", name="ログイン", exact=True)).to_be_visible()
    expect(app.get_by_role("button", name="新規登録", exact=True)).to_be_visible()


def test_何も入力せずにログインするとエラーが出る(app: Page):
    app.get_by_role("button", name="ログイン", exact=True).click()
    expect(app.get_by_text("メールアドレスとパスワードを入力してください。")).to_be_visible()
    dismiss_dialog(app)
    expect(app.get_by_text("メールアドレスとパスワードを入力してください。")).to_be_hidden()


def test_パスワードを入れずにログインするとエラーが出る(app: Page):
    fill_text(app, app.get_by_role("textbox", name=EMAIL), "someone@example.com")
    app.get_by_role("button", name="ログイン", exact=True).click()
    expect(app.get_by_text("メールアドレスとパスワードを入力してください。")).to_be_visible()


def test_何も入力せずに新規登録するとエラーが出る(app: Page):
    app.get_by_role("button", name="新規登録", exact=True).click()
    expect(app.get_by_text("メールアドレスとパスワードを入力してください。")).to_be_visible()


def test_パスワードは最初は隠れていて目のボタンで表示できる(app: Page):
    password = app.get_by_role("textbox", name=PASSWORD)
    fill_text(app, password, "Secret-123")
    expect(password).to_have_attribute("type", "password")

    # 入力欄の右端の目のアイコン（名前の無いボタン）を押す
    eye = app.locator("flt-semantics[role=button]").filter(has_not_text=re.compile(r"\S"))
    eye.first.click()
    expect(app.get_by_role("textbox", name=PASSWORD)).not_to_have_attribute("type", "password")


def test_新規登録の注意書きが表示される(app: Page):
    expect(app.get_by_text(re.compile("新規登録の際は、実在するメールアドレス"))).to_be_visible()
    expect(app.get_by_text(re.compile("大文字・小文字・数字・記号"))).to_be_visible()
