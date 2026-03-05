"""
tests/test_wjx_filler.py — wjx_filler 单元测试

使用 unittest.mock 隔离 Playwright，无需真实网络连接即可验证核心逻辑。
"""

from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# 为了在没有安装 playwright 的 CI 环境也能运行，先用 mock 注入
# ---------------------------------------------------------------------------
def _make_playwright_stub():
    pw_mod = types.ModuleType("playwright")
    sync_mod = types.ModuleType("playwright.sync_api")

    class _FakePW:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        chromium = MagicMock()

    def sync_playwright():
        return _FakePW()

    class TimeoutError(Exception):
        pass

    # Stub out every name imported by wjx_filler from playwright.sync_api
    sync_mod.sync_playwright = sync_playwright
    sync_mod.TimeoutError = TimeoutError
    sync_mod.Page = MagicMock          # type alias used only in annotations
    pw_mod.sync_api = sync_mod
    sys.modules["playwright"] = pw_mod
    sys.modules["playwright.sync_api"] = sync_mod
    return TimeoutError


_TimeoutError = _make_playwright_stub()

import wjx_filler  # noqa: E402  (imported after stub)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_question_div(data_type: str, children: dict | None = None):
    """构建一个模拟的题目 div 对象。"""
    div = MagicMock()
    div.get_attribute.return_value = data_type

    div.query_selector_all.return_value = []
    div.query_selector.return_value = None

    if children:
        def _qsa(selector):
            for key, val in children.items():
                if key in selector:
                    return val
            return []
        div.query_selector_all.side_effect = _qsa

        def _qs(selector):
            for key, val in children.items():
                if key in selector:
                    return val[0] if val else None
            return None
        div.query_selector.side_effect = _qs

    return div


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFillRadio(unittest.TestCase):
    def test_clicks_one_option(self):
        page = MagicMock()
        options = [MagicMock(), MagicMock(), MagicMock()]
        qdiv = _make_question_div("1", {"li.label": options, "li": options})
        wjx_filler._fill_radio(page, qdiv)
        total_clicks = sum(o.click.call_count for o in options)
        self.assertEqual(total_clicks, 1)

    def test_empty_options_no_crash(self):
        page = MagicMock()
        qdiv = _make_question_div("1")
        wjx_filler._fill_radio(page, qdiv)  # should not raise


class TestFillCheckbox(unittest.TestCase):
    def test_clicks_at_least_one(self):
        page = MagicMock()
        options = [MagicMock() for _ in range(5)]
        qdiv = _make_question_div("2", {"li.label": options, "li": options})
        wjx_filler._fill_checkbox(page, qdiv)
        total_clicks = sum(o.click.call_count for o in options)
        self.assertGreaterEqual(total_clicks, 1)

    def test_empty_options_no_crash(self):
        page = MagicMock()
        qdiv = _make_question_div("2")
        wjx_filler._fill_checkbox(page, qdiv)


class TestFillText(unittest.TestCase):
    def test_fills_textarea(self):
        page = MagicMock()
        textarea = MagicMock()
        qdiv = _make_question_div("3", {"textarea": [textarea]})
        wjx_filler._fill_text(page, qdiv)
        textarea.fill.assert_called_once()
        filled_value = textarea.fill.call_args[0][0]
        self.assertIsInstance(filled_value, str)
        self.assertGreater(len(filled_value), 0)

    def test_fills_text_input(self):
        page = MagicMock()
        text_input = MagicMock()

        div = MagicMock()
        div.get_attribute.return_value = "3"

        def _qs(selector):
            if "textarea" in selector and "text" not in selector.replace("textarea", ""):
                return None
            if "input[type='text']" in selector:
                return text_input
            return None

        div.query_selector.side_effect = _qs
        div.query_selector_all.return_value = []

        wjx_filler._fill_text(page, div)
        text_input.fill.assert_called_once()


class TestFillScale(unittest.TestCase):
    def test_clicks_one_scale_item(self):
        page = MagicMock()
        labels = [MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        qdiv = _make_question_div("4", {"ul.scale li": labels, "li.label": labels})
        wjx_filler._fill_scale(page, qdiv)
        total_clicks = sum(l.click.call_count for l in labels)
        self.assertEqual(total_clicks, 1)


class TestFillSelect(unittest.TestCase):
    def test_selects_valid_option(self):
        page = MagicMock()
        opt0 = MagicMock(); opt0.get_attribute.return_value = ""
        opt1 = MagicMock(); opt1.get_attribute.return_value = "a"
        opt2 = MagicMock(); opt2.get_attribute.return_value = "b"
        sel = MagicMock()
        sel.query_selector_all.return_value = [opt0, opt1, opt2]

        div = MagicMock()
        div.get_attribute.return_value = "7"
        div.query_selector.return_value = sel

        wjx_filler._fill_select(page, div)
        sel.select_option.assert_called_once()
        chosen = sel.select_option.call_args[1]["value"]
        self.assertIn(chosen, ("a", "b"))

    def test_no_select_element_no_crash(self):
        page = MagicMock()
        div = MagicMock()
        div.get_attribute.return_value = "7"
        div.query_selector.return_value = None
        wjx_filler._fill_select(page, div)


class TestFillMatrixRadio(unittest.TestCase):
    def test_clicks_one_per_row(self):
        page = MagicMock()
        rows = []
        for _ in range(3):
            row = MagicMock()
            cols = [MagicMock(), MagicMock(), MagicMock()]
            row.query_selector_all.return_value = cols
            rows.append(row)

        qdiv = MagicMock()
        qdiv.query_selector_all.return_value = rows
        qdiv.get_attribute.return_value = "8"

        wjx_filler._fill_matrix_radio(page, qdiv)
        for row in rows:
            total = sum(c.click.call_count for c in row.query_selector_all.return_value)
            self.assertEqual(total, 1)


class TestFillBatchCount(unittest.TestCase):
    """fill_batch 应该调用 fill_once 指定次数。"""

    def test_batch_calls_fill_once_n_times(self):
        with patch.object(wjx_filler, "fill_once", return_value=True) as mock_fill:
            with patch("time.sleep"):
                result = wjx_filler.fill_batch("http://example.com", count=3, interval=0)
        self.assertEqual(mock_fill.call_count, 3)
        self.assertEqual(result, 3)

    def test_batch_counts_failures(self):
        returns = [True, False, True]
        with patch.object(wjx_filler, "fill_once", side_effect=returns):
            with patch("time.sleep"):
                result = wjx_filler.fill_batch("http://example.com", count=3, interval=0)
        self.assertEqual(result, 2)


class TestMain(unittest.TestCase):
    """main.py CLI 逻辑测试。"""

    def test_main_returns_zero_on_success(self):
        from main import main as cli_main
        with patch("main.fill_batch", return_value=1) as mock_fb:
            with patch("sys.argv", ["wjx", "http://example.com"]):
                code = cli_main()
        self.assertEqual(code, 0)
        mock_fb.assert_called_once_with(
            url="http://example.com",
            count=1,
            headless=True,
            interval=2.0,
        )

    def test_main_returns_one_on_all_fail(self):
        from main import main as cli_main
        with patch("main.fill_batch", return_value=0):
            with patch("sys.argv", ["wjx", "http://example.com", "--count", "2"]):
                code = cli_main()
        self.assertEqual(code, 1)

    def test_main_show_flag(self):
        from main import main as cli_main
        with patch("main.fill_batch", return_value=1) as mock_fb:
            with patch("sys.argv", ["wjx", "http://example.com", "--show"]):
                cli_main()
        self.assertFalse(mock_fb.call_args[1]["headless"])


if __name__ == "__main__":
    unittest.main()
