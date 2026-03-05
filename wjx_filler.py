"""
wjx_filler.py — 问卷星自动快填核心模块
使用 Playwright 驱动 Chromium 浏览器，自动识别并填写问卷星问卷。

支持题型：
  1  单选题   (radio)
  2  多选题   (checkbox)
  3  填空题   (text / textarea)
  4  量表/评分题 (scale / rating)
  5  矩阵单选 (matrix radio)
  6  矩阵多选 (matrix checkbox)
  7  下拉题   (select)
"""

from __future__ import annotations

import random
import time
from typing import Optional

from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeoutError


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------

def _random_sleep(min_s: float = 0.3, max_s: float = 1.2) -> None:
    """模拟人工操作停顿，避免被风控识别。"""
    time.sleep(random.uniform(min_s, max_s))


def _fill_radio(page: Page, question_div) -> None:
    """单选题：随机选择一个选项。"""
    options = question_div.query_selector_all("li.label")
    if not options:
        options = question_div.query_selector_all("li")
    if options:
        choice = random.choice(options)
        choice.click()
        _random_sleep()


def _fill_checkbox(page: Page, question_div) -> None:
    """多选题：随机勾选 1～N 个选项（至少选 1 个）。"""
    options = question_div.query_selector_all("li.label")
    if not options:
        options = question_div.query_selector_all("li")
    if not options:
        return
    k = random.randint(1, len(options))
    chosen = random.sample(list(options), k)
    for item in chosen:
        item.click()
        _random_sleep(0.1, 0.4)


def _fill_text(page: Page, question_div) -> None:
    """填空/简答题：填入随机中文短句。"""
    texts = [
        "非常满意",
        "一般般吧",
        "还不错",
        "有待改善",
        "挺好的",
        "符合预期",
        "超出预期",
        "需要改进",
        "满意",
        "不错",
    ]
    textarea = question_div.query_selector("textarea")
    if textarea:
        textarea.fill(random.choice(texts))
        _random_sleep()
        return
    inp = question_div.query_selector("input[type='text']")
    if inp:
        inp.fill(random.choice(texts))
        _random_sleep()


def _fill_scale(page: Page, question_div) -> None:
    """量表/评分题：随机点击某一刻度。"""
    labels = question_div.query_selector_all("ul.scale li")
    if not labels:
        labels = question_div.query_selector_all("li.label")
    if labels:
        choice = random.choice(labels)
        choice.click()
        _random_sleep()


def _fill_select(page: Page, question_div) -> None:
    """下拉题：随机选择一个非空选项。"""
    sel = question_div.query_selector("select")
    if not sel:
        return
    opts = sel.query_selector_all("option")
    valid = [o for o in opts if (o.get_attribute("value") or "").strip() not in ("", "0")]
    if valid:
        val = random.choice(valid).get_attribute("value")
        sel.select_option(value=val)
        _random_sleep()


def _fill_matrix_radio(page: Page, question_div) -> None:
    """矩阵单选题：每行随机选一列。"""
    rows = question_div.query_selector_all("tr.trQue")
    for row in rows:
        cols = row.query_selector_all("td label, td.td-radio")
        if cols:
            random.choice(cols).click()
            _random_sleep(0.1, 0.3)


def _fill_matrix_checkbox(page: Page, question_div) -> None:
    """矩阵多选题：每行随机勾选至少一列。"""
    rows = question_div.query_selector_all("tr.trQue")
    for row in rows:
        cols = row.query_selector_all("td label, td.td-checkbox")
        if cols:
            k = random.randint(1, max(1, len(cols)))
            for col in random.sample(list(cols), k):
                col.click()
                _random_sleep(0.05, 0.2)


# ---------------------------------------------------------------------------
# 题型分发
# ---------------------------------------------------------------------------

# 问卷星 data-type 属性 → 填写函数映射
_TYPE_HANDLERS = {
    "1": _fill_radio,           # 单选
    "2": _fill_checkbox,        # 多选
    "3": _fill_text,            # 填空
    "4": _fill_scale,           # 量表
    "5": _fill_radio,           # 顺序（与单选类似）
    "6": _fill_scale,           # 矩阵量表
    "7": _fill_select,          # 下拉
    "8": _fill_matrix_radio,    # 矩阵单选
    "9": _fill_matrix_checkbox, # 矩阵多选
    "11": _fill_text,           # 填空（多行）
}


def _fill_page_questions(page: Page) -> None:
    """填写当前页面上所有可见题目。"""
    # 问卷星题目容器：div[topic] 或 div.field
    question_divs = page.query_selector_all("div[topic]")
    if not question_divs:
        question_divs = page.query_selector_all("div.field")

    for qdiv in question_divs:
        dtype = qdiv.get_attribute("data-type") or ""
        handler = _TYPE_HANDLERS.get(dtype)
        if handler:
            try:
                handler(page, qdiv)
            except Exception as exc:
                print(f"[wjx_filler] 跳过题目（data-type={dtype}）：{type(exc).__name__}: {exc}")
        else:
            # 未知题型：尝试通用 radio → checkbox → text 顺序
            try:
                radios = qdiv.query_selector_all("input[type='radio']")
                if radios:
                    random.choice(radios).click()
                    _random_sleep()
                    continue
                checks = qdiv.query_selector_all("input[type='checkbox']")
                if checks:
                    k = random.randint(1, max(1, len(checks)))
                    for cb in random.sample(list(checks), k):
                        cb.click()
                        _random_sleep(0.05, 0.2)
                    continue
                inp = qdiv.query_selector("input[type='text'], textarea")
                if inp:
                    inp.fill("满意")
                    _random_sleep()
            except Exception as exc:
                print(f"[wjx_filler] 跳过未知题型：{type(exc).__name__}: {exc}")


def _submit(page: Page) -> bool:
    """点击提交按钮并等待结果页面。"""
    submit_btn = page.query_selector("#submit_button, .submit-button, input[type='submit']")
    if not submit_btn:
        return False
    submit_btn.click()
    try:
        # 等待跳转至感谢页 / 提交成功提示
        page.wait_for_selector(
            ".thanks, .finish, #divSubmit, .submitted, .end-page",
            timeout=10000,
        )
    except PWTimeoutError:
        pass
    return True


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------

def fill_once(url: str, headless: bool = True, slow_mo: int = 0) -> bool:
    """
    打开问卷 URL，自动填写并提交，返回是否成功。

    Parameters
    ----------
    url       : 问卷星问卷链接，例如 https://www.wjx.cn/vm/xxxxxxx.aspx
    headless  : 是否无头模式运行（默认 True）
    slow_mo   : Playwright 慢动作延迟毫秒数（调试时设为 500~1000）
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless, slow_mo=slow_mo)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 390, "height": 844},
            locale="zh-CN",
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            _random_sleep(1, 2)
            _fill_page_questions(page)
            _ = _submit(page)
            _random_sleep(1, 2)
        finally:
            browser.close()
    return success


def fill_batch(url: str, count: int = 1, headless: bool = True,
               interval: float = 2.0) -> int:
    """
    批量填写问卷。

    Parameters
    ----------
    url      : 问卷链接
    count    : 填写次数
    headless : 是否无头模式
    interval : 每次提交后的等待秒数

    Returns
    -------
    成功提交次数
    """
    success_count = 0
    for i in range(1, count + 1):
        print(f"[{i}/{count}] 正在填写…", end=" ", flush=True)
        ok = fill_once(url, headless=headless)
        if ok:
            success_count += 1
            print("✓ 提交成功")
        else:
            print("✗ 提交失败（可能已到达答题上限或页面结构不识别）")
        if i < count:
            time.sleep(interval + random.uniform(0, 1))
    return success_count
