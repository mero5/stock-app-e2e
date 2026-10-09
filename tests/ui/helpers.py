# ===================================================
# 画面テストの操作手順（ヘルパー）
# conftest.py とテストファイルの両方から使う
# ===================================================

import re

from playwright.sync_api import Locator, Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def enable_semantics(page: Page) -> None:
    """Flutter Web の隠しボタンを押して、セマンティクス（要素情報）を有効にする"""
    placeholder = page.locator("flt-semantics-placeholder")
    placeholder.wait_for(state="attached")
    # 画面外に置かれていて普通のクリックが届かないので、イベントを直接送る
    placeholder.dispatch_event("click")
    page.locator("flt-semantics").first.wait_for(state="attached")


def fill_text(page: Page, box: Locator, value: str) -> None:
    """
    Flutter Web の入力欄に文字を入れる。

    Flutter は入力欄をタップしてから「入力の受け付け」を準備するので、
    準備が終わる前に fill すると、入れた文字が空に戻されることがある
    （2026-10-10：ログインのメール欄が空のままになり、ログイン後のテストが全部止まった）。
    入れたあとに値が残っているかを確かめて、消えていたら入れ直す。
    """
    for _ in range(5):
        box.click()
        box.fill(value)
        page.wait_for_timeout(300)
        if box.input_value() == value:
            return
    raise AssertionError("入力欄に文字が入らない（Flutter 側で消されている）")


def dismiss_dialog(page: Page, button: str = "OK") -> None:
    page.get_by_role("button", name=button).click()


def login(page: Page, email: str, password: str) -> None:
    """
    ログインして、ホーム画面まで進める。

    まっさらなブラウザで開くので、ログイン後に次の画面が出ることがある。
    それぞれ通過してホームまで進める。
      アプリ説明（OnboardingScreen）→「スキップ」
      利用規約（TermsScreen）      → 6項目にチェック →「同意してアプリを始める」
      初回プロファイル設定          →「設定して始める」（テスト用アカウントが未設定の場合だけ）
    """
    fill_text(page, page.get_by_role("textbox", name=re.compile("example@email.com")), email)
    fill_text(page, page.get_by_role("textbox", name=re.compile("8文字以上")), password)
    page.get_by_role("button", name="ログイン", exact=True).click()

    home_tab = bottom_tab(page, "ホーム")
    skip = page.get_by_role("button", name="スキップ")
    terms_agree = page.get_by_text(re.compile("確認済み")).first
    profile_start = page.get_by_role("button", name="設定して始める")

    # どの画面が出るかはアカウントと端末の状態次第なので、順番に確認して進める。
    # 画面の切り替えアニメーション中に押すと届かないことがあるので、
    # 押せなかったら次の周でもう一度、今どの画面かを確かめ直す。
    for _ in range(8):
        expect(home_tab.or_(skip).or_(terms_agree).or_(profile_start).first).to_be_visible()
        try:
            if skip.is_visible():
                skip.click(timeout=5_000)
            elif terms_agree.is_visible():
                agree_terms(page)
            elif profile_start.is_visible():
                profile_start.click(timeout=5_000)
            else:
                return
        except PlaywrightTimeoutError:
            continue
    expect(home_tab.first).to_be_visible()


# 利用規約（TermsScreen）の6項目。チェックボックスではなく、カード全体をタップして丸を付ける作り
TERMS_ITEMS = [
    "投資は自己責任で行います",
    "データに誤りが含まれる場合があることを理解しました",
    "AI分析は参考情報であることを理解しました",
    "株価データの遅延および乖離があることを理解しました",
    "サービスが予告なく変更・停止される場合があることを理解しました",
    "データ管理・プライバシーについて理解しました",
]


def _terms_checked_count(page: Page) -> int:
    """利用規約の「◯ / 6 確認済み」の◯を読む"""
    m = re.search(r"(\d+) / \d+ 確認済み", page.get_by_text(re.compile("確認済み")).first.inner_text())
    return int(m.group(1)) if m else -1


def agree_terms(page: Page) -> None:
    """
    利用規約の6項目をタップして「同意してアプリを始める」を押す。

    タップが反映されないことがある（画面のスクロール中など）ので、
    1項目押すごとに「確認済み」の数が増えたかを確かめ、増えていなければ押し直す。
    タップするたびに丸が付いたり外れたりするので、数が減ったときも押し直して戻す。
    """
    for title in TERMS_ITEMS:
        card = page.get_by_role("button", name=re.compile("^" + re.escape(title)))
        before = _terms_checked_count(page)
        for _ in range(4):
            card.click(timeout=5_000)
            page.wait_for_timeout(300)
            if _terms_checked_count(page) > before:
                break
    expect(page.get_by_text(f"{len(TERMS_ITEMS)} / {len(TERMS_ITEMS)} 確認済み")).to_be_visible()
    page.get_by_role("button", name="同意してアプリを始める").click(timeout=5_000)


def tab(page: Page, name: str):
    """
    タブを名前で探す（画面下のタブ・銘柄詳細の上のタブ・YouTubeの検索/登録 など共通）。

    Flutter のタブは、読み上げ用の名前が「ホーム」だけでなく
    「ホーム タブ 1/6」のように番号付きになることがあるので、
    役割（tab）か、名前が「ホーム」で始まる要素のどちらかで探す。
    """
    by_role = page.get_by_role("tab", name=re.compile("^" + re.escape(name)))
    by_text = page.locator("flt-semantics").filter(has_text=re.compile("^" + re.escape(name)))
    return by_role.or_(by_text).first


def text(page: Page, value: str, exact: bool = False) -> Locator:
    """
    画面に出ている文字を探す。

    Flutter は、カードなどのまとまりの中の文字を、要素の文字ではなく
    「読み上げ用の名前（aria-label）」として持つことがある（設定の投資プロファイルなど）。
    get_by_text だけだと見つからないので、読み上げ用の名前でも探す。
    """
    pattern = re.compile(("^" + re.escape(value) + "$") if exact else re.escape(value))
    return page.get_by_text(pattern).or_(page.get_by_label(pattern)).first


def bottom_tab(page: Page, name: str):
    """画面下のタブ（BottomNavigationBar）を名前で探す"""
    return tab(page, name)


def open_settings_item(page: Page, name: str) -> None:
    """設定タブを開いて、項目（お知らせ履歴・AI予測の成績 など）をタップする"""
    bottom_tab(page, "設定").click()
    page.get_by_text(name).first.click()
