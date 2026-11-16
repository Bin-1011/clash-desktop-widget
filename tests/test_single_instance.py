# -*- coding: utf-8 -*-
"""组 D（H-1 / H-2）单实例 Mutex 与动态标题查找的单元测试。

只用标准库，mock 掉 Windows API，不启动 Tk mainloop。
"""

import unittest
from unittest import mock

import conn_widget


class IsWidgetTitleTests(unittest.TestCase):
    def test_exact_app_name(self):
        self.assertTrue(conn_widget.is_widget_title(conn_widget.APP_NAME))

    def test_dynamic_rate_title(self):
        self.assertTrue(
            conn_widget.is_widget_title(f"↓12.3KB/s ↑1.0KB/s · {conn_widget.APP_NAME}")
        )

    def test_unrelated_title(self):
        self.assertFalse(conn_widget.is_widget_title("记事本"))

    def test_empty_title(self):
        self.assertFalse(conn_widget.is_widget_title(""))
        self.assertFalse(conn_widget.is_widget_title(None))

    def test_only_partial_contains_app_name(self):
        self.assertFalse(
            conn_widget.is_widget_title(f"关于 {conn_widget.APP_NAME} 的说明")
        )
        self.assertFalse(
            conn_widget.is_widget_title(f"{conn_widget.APP_NAME} · ↓12.3KB/s")
        )


class FindWidgetHwndTests(unittest.TestCase):
    def _enum_from(self, titles):
        calls = []

        def enum_windows(callback, lparam):
            for hwnd in titles:
                calls.append(hwnd)
                # 与 Win32 回调一致：返回 False 表示停止枚举。
                if not callback(hwnd, lparam):
                    return

        return enum_windows, calls

    def test_finds_hwnd_with_dynamic_title(self):
        titles = {
            101: "记事本",
            202: f"↓12.3KB/s ↑1.0KB/s · {conn_widget.APP_NAME}",
            303: "其他窗口",
        }
        enum_windows, _ = self._enum_from(titles)

        def get_window_text(hwnd):
            return titles[hwnd]

        self.assertEqual(
            conn_widget.find_widget_hwnd(enum_windows, get_window_text), 202
        )

    def test_finds_hwnd_with_original_title(self):
        titles = {11: conn_widget.APP_NAME}
        enum_windows, _ = self._enum_from(titles)
        self.assertEqual(
            conn_widget.find_widget_hwnd(enum_windows, titles.get), 11
        )

    def test_returns_empty_when_no_widget_window(self):
        titles = {1: "记事本", 2: "关于 Clash 连接小窗"}
        enum_windows, _ = self._enum_from(titles)
        self.assertFalse(
            conn_widget.find_widget_hwnd(enum_windows, titles.get)
        )

    def test_stops_after_first_match(self):
        titles = {
            1: f"↓1KB/s ↑2KB/s · {conn_widget.APP_NAME}",
            2: f"↓3KB/s ↑4KB/s · {conn_widget.APP_NAME}",
            3: "无关窗口",
        }
        enum_windows, calls = self._enum_from(titles)
        self.assertEqual(
            conn_widget.find_widget_hwnd(enum_windows, titles.get), 1
        )
        self.assertEqual(calls, [1])

    def test_get_window_text_failure_is_ignored(self):
        def enum_windows(callback, lparam):
            callback(1, lparam)
            callback(2, lparam)

        def get_window_text(hwnd):
            if hwnd == 1:
                raise OSError("window disappeared")
            return f"↓1KB/s ↑2KB/s · {conn_widget.APP_NAME}"

        self.assertEqual(conn_widget.find_widget_hwnd(enum_windows, get_window_text), 2)


class MutexFirstInstanceTests(unittest.TestCase):
    def test_error_already_exists_means_not_first(self):
        self.assertFalse(conn_widget.mutex_means_first_instance(183))

    def test_zero_last_error_means_first(self):
        self.assertTrue(conn_widget.mutex_means_first_instance(0))


class SingleInstanceTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(conn_widget, "_mutex", None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _patches(self, last_error):
        events = []
        kernel32 = mock.Mock()

        def create_mutex(*args, **kwargs):
            events.append("CreateMutexW")
            return 1234

        kernel32.CreateMutexW.side_effect = create_mutex
        win_dll = mock.Mock(return_value=kernel32)

        def set_last_error(value):
            events.append(("set_last_error", value))

        def get_last_error():
            events.append("get_last_error")
            return last_error

        return win_dll, kernel32, events, set_last_error, get_last_error

    def test_last_error_183_means_not_first(self):
        win_dll, kernel32, events, set_err, get_err = self._patches(183)
        with mock.patch.object(conn_widget.ctypes, "WinDLL", win_dll, create=True), \
                mock.patch.object(conn_widget.ctypes, "set_last_error", set_err,
                                  create=True), \
                mock.patch.object(conn_widget.ctypes, "get_last_error", get_err,
                                  create=True):
            self.assertIs(conn_widget.single_instance(), False)

        win_dll.assert_called_once_with("kernel32", use_last_error=True)
        self.assertEqual(events[0], ("set_last_error", 0))
        self.assertEqual(events[1], "CreateMutexW")
        self.assertEqual(events[2], "get_last_error")
        kernel32.CreateMutexW.assert_called_once_with(
            None, False, "Local\\ClashConnWidget_v2"
        )

    def test_last_error_zero_means_first(self):
        win_dll, kernel32, events, set_err, get_err = self._patches(0)
        with mock.patch.object(conn_widget.ctypes, "WinDLL", win_dll, create=True), \
                mock.patch.object(conn_widget.ctypes, "set_last_error", set_err,
                                  create=True), \
                mock.patch.object(conn_widget.ctypes, "get_last_error", get_err,
                                  create=True):
            self.assertIs(conn_widget.single_instance(), True)

        self.assertEqual(events[0], ("set_last_error", 0))
        self.assertEqual(events[1], "CreateMutexW")
        self.assertEqual(events[2], "get_last_error")
        self.assertIsNotNone(conn_widget._mutex)

    def test_win_dll_failure_allows_start(self):
        with mock.patch.object(conn_widget.ctypes, "WinDLL",
                               side_effect=OSError("no kernel32"), create=True):
            self.assertIs(conn_widget.single_instance(), True)

    def test_missing_win_dll_allows_start(self):
        with mock.patch.object(conn_widget.ctypes, "WinDLL",
                               side_effect=AttributeError("no WinDLL"),
                               create=True):
            self.assertIs(conn_widget.single_instance(), True)


if __name__ == "__main__":
    unittest.main()
