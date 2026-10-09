# ===================================================
# 画面テスト（Flutter Web × Playwright）の共通設定
#
# ■ 前提
#   stock_app を Web 向けにビルドして、どこかで配信しておく。
#     flutter build web --release
#     python -m http.server 8765 --directory build/web
#   その URL を環境変数 STOCK_APP_WEB_URL に入れて pytest を実行する。
#   （未設定なら画面テストは全部スキップする）
#
# ■ Flutter Web を Playwright で操作するための工夫
#   Flutter Web は画面を canvas（絵）として描くので、そのままでは
#   ボタンや入力欄を HTML の要素として見つけられない。
#   Flutter は画面の裏に「Enable accessibility」という隠しボタン
#   （flt-semantics-placeholder）を置いていて、これを押すと
#   セマンティクス（読み上げ用の要素情報）が有効になり、
#   get_by_role("button", name="ログイン") のように探せるようになる。
#   → アプリ側のコードを変えずにテストできる。
#
# ■ ログインが必要なテスト
#   テスト専用アカウントのメールアドレス・パスワードを
#   環境変数 E2E_EMAIL / E2E_PASSWORD に入れたときだけ実行する
#   （GitHub Actions では Secrets から渡す）。
# ===================================================

import os

import pytest
from playwright.sync_api import Page

from tests.ui.helpers import enable_semantics, login

# 画面の描画・Cognito・APIの応答を待つ時間
UI_TIMEOUT_MS = 30_000

# スマホと同じくらいの画面サイズで確認する
PHONE_VIEWPORT = {"width": 412, "height": 915}


def pytest_collection_modifyitems(config, items):
    """STOCK_APP_WEB_URL が無ければ画面テストを、ログイン情報が無ければログイン後のテストをスキップ"""
    no_url = not os.getenv("STOCK_APP_WEB_URL")
    no_cred = not (os.getenv("E2E_EMAIL") and os.getenv("E2E_PASSWORD"))
    for item in items:
        if "tests/ui" not in str(item.fspath).replace("\\", "/"):
            continue
        if no_url:
            item.add_marker(pytest.mark.skip(reason="STOCK_APP_WEB_URL が未設定（Web版を配信していない）"))
        elif "login" in item.keywords and no_cred:
            item.add_marker(pytest.mark.skip(reason="E2E_EMAIL / E2E_PASSWORD が未設定（テスト用アカウント待ち）"))


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """pytest-playwright のブラウザ設定を上書き（スマホサイズ・日本語）"""
    return {**browser_context_args, "viewport": PHONE_VIEWPORT, "locale": "ja-JP"}


@pytest.fixture
def last_seen_notice() -> int:
    """
    アプリを開く前に「ここまで読んだ」ことにしておくお知らせの version。

    まっさらなブラウザだと全部のお知らせが未読になり、ログイン直後に
    ポップアップが何枚も出て他のテストの邪魔になるので、既定では全部既読にしておく。
    ポップアップ自体の確認は test_notice_popup.py で、このフィクスチャを上書きして行う。
    """
    return 1_000_000


@pytest.fixture
def app(page: Page, last_seen_notice: int) -> Page:
    """
    アプリを開いて、セマンティクスを有効にした状態の Page を返す。

    毎回新しいブラウザのコンテキスト（＝まっさらな端末）で開くので、
    ログイン状態や「規約に同意済み」などは残っていない。
    """
    page.set_default_timeout(UI_TIMEOUT_MS)
    # Flutter Web の SharedPreferences は localStorage に「flutter.キー名」で保存される
    page.add_init_script(
        f"localStorage.setItem('flutter.last_seen_notice_version', '{last_seen_notice}')"
    )
    page.goto(os.environ["STOCK_APP_WEB_URL"])
    enable_semantics(page)
    return page


@pytest.fixture
def logged_in(app: Page) -> Page:
    """ログイン済みでホーム画面を開いた Page"""
    login(app, os.environ["E2E_EMAIL"], os.environ["E2E_PASSWORD"])
    return app
