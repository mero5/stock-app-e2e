# ===================================================
# 共通の設定（フィクスチャ）
#
# フィクスチャ＝テストの前準備を関数にしたもの。
# テスト関数の引数に `api` と書くと、ここで作った
# 「バックエンドAPIを呼ぶためのPlaywrightのクライアント」が渡される。
# ===================================================

import os
from datetime import datetime, timedelta, timezone

import pytest
from playwright.sync_api import APIRequestContext, Playwright

# テスト対象のバックエンド（FastAPI on Lambda）。
# 環境変数 STOCK_API_URL で上書きできる（ステージングやローカルを叩くとき用）。
DEFAULT_API_URL = "https://pcg3tt7tmvzye4pwh3mqkfdjs40muver.lambda-url.ap-northeast-1.on.aws"

# Lambda のコールドスタート（しばらく呼ばれていない後の初回起動）は
# 銘柄マスタの読み込みで遅くなるので、1リクエストの待ち時間は長めにする
REQUEST_TIMEOUT_MS = 90_000

JST = timezone(timedelta(hours=9))


@pytest.fixture(scope="session")
def base_url() -> str:
    # 空文字（GitHub の変数が未設定）のときも既定値を使う
    return (os.getenv("STOCK_API_URL") or DEFAULT_API_URL).rstrip("/")


@pytest.fixture(scope="session")
def api(playwright: Playwright, base_url: str) -> APIRequestContext:
    """
    バックエンドAPI用のHTTPクライアント（PlaywrightのAPIRequestContext）

    session スコープなので、全テストで1つを使い回す。
    """
    ctx = playwright.request.new_context(
        base_url=base_url,
        timeout=REQUEST_TIMEOUT_MS,
        extra_http_headers={"Accept": "application/json"},
    )
    # 最初に1回 /health を呼んで、Lambda を起こしておく（ウォームアップ）
    ctx.get("/health")
    yield ctx
    ctx.dispose()


@pytest.fixture
def today_jst():
    """日本時間の今日"""
    return datetime.now(JST).date()


def pytest_collection_modifyitems(config, items):
    """
    AIを呼ぶテスト（@pytest.mark.ai）は、OpenAIの料金がかかるので
    環境変数 RUN_AI_TESTS=1 のときだけ実行する。
    """
    if os.getenv("RUN_AI_TESTS") == "1":
        return
    skip_ai = pytest.mark.skip(reason="AIを呼ぶテストは RUN_AI_TESTS=1 のときだけ実行（料金がかかるため）")
    for item in items:
        if "ai" in item.keywords:
            item.add_marker(skip_ai)
