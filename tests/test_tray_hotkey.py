# -*- coding: utf-8 -*-
"""组 E（H-3 / H-7）热键失败提示与 TaskbarCreated 重建托盘的单元测试。

只用标准库，mock 掉 Windows API / Tk，不启动 mainloop，也不创建真实托盘。
"""

import unittest
from unittest import mock

import conn_widget


class HotkeyFailMessageTests(unittest.TestCase):
    def test_success_returns_no_message(self):
        for lang in ("zh", "en"):
            self.assertIsNone(conn_widget.hotkey_fail_message(True, lang))

    def test_failure_has_chinese_message(self):
        msg = conn_widget.hotkey_fail_message(False, "zh")
        self.assertIsInstance(msg, str)
        self.assertIn("Ctrl+Shift+C", msg)
        self.assertIn("占用", msg)

    def test_failure_has_english_message(self):
        msg = conn_widget.hotkey_fail_message(False, "en")
        self.assertIsInstance(msg, str)
        self.assertIn("Ctrl+Shift+C", msg)
        self.assertIn("another app", msg)

    def test_unknown_language_falls_back_to_chinese(self):
        self.assertEqual(
            conn_widget.hotkey_fail_message(False, "xx"),
            conn_widget.hotkey_fail_message(False, "zh"),
        )


class TrayShouldReaddTests(unittest.TestCase):
    TASKBAR_CREATED = 0xC123

    def test_matching_message_should_readd(self):
        self.assertTrue(
            conn_widget.tray_should_readd(
                self.TASKBAR_CREATED, self.TASKBAR_CREATED
            )
        )

    def test_other_message_should_not_readd(self):
        self.assertFalse(
            conn_widget.tray_should_readd(0x0400, self.TASKBAR_CREATED)
        )

    def test_zero_message_id_never_matches(self):
        # RegisterWindowMessageW 失败时为 0，绝不能因此对所有 0 消息重建。
        self.assertFalse(conn_widget.tray_should_readd(0, 0))
        self.assertFalse(conn_widget.tray_should_readd(self.TASKBAR_CREATED, 0))


class TrayReaddTests(unittest.TestCase):
    def _new_tray(self):
        tray = conn_widget.TrayIcon.__new__(conn_widget.TrayIcon)
        tray.nid = conn_widget.NOTIFYICONDATAW()
        tray.ok = False
        return tray

    def test_readd_calls_nim_add_and_marks_ok(self):
        shell32 = mock.Mock()
        shell32.Shell_NotifyIconW.return_value = 1
        windll = mock.Mock(shell32=shell32)
        tray = self._new_tray()

        with mock.patch.object(conn_widget.ctypes, "windll", windll, create=True):
            self.assertTrue(tray.readd())

        action, _nid = shell32.Shell_NotifyIconW.call_args.args
        self.assertEqual(action, conn_widget.NIM_ADD)
        self.assertTrue(tray.ok)

    def test_readd_failure_clears_ok(self):
        shell32 = mock.Mock()
        shell32.Shell_NotifyIconW.return_value = 0
        windll = mock.Mock(shell32=shell32)
        tray = self._new_tray()
        tray.ok = True

        with mock.patch.object(conn_widget.ctypes, "windll", windll, create=True):
            self.assertFalse(tray.readd())

        self.assertFalse(tray.ok)


class TrayHandlerTaskbarTests(unittest.TestCase):
    TASKBAR_CREATED = 0xC123

    def _new_tray(self):
        tray = conn_widget.TrayIcon.__new__(conn_widget.TrayIcon)
        tray.taskbar_created = self.TASKBAR_CREATED
        tray._old = 123
        tray._hotkey_cb = None
        tray.pending = None
        tray.readd = mock.Mock(return_value=True)
        return tray

    def test_taskbar_created_message_readds_without_tk(self):
        user32 = mock.Mock()
        windll = mock.Mock(user32=user32)
        tray = self._new_tray()

        with mock.patch.object(conn_widget.ctypes, "windll", windll, create=True):
            result = tray._handler(1, self.TASKBAR_CREATED, 0, 0)

        self.assertEqual(result, 0)
        tray.readd.assert_called_once_with()
        user32.CallWindowProcW.assert_not_called()
        self.assertIsNone(tray.pending)

    def test_other_message_does_not_readd(self):
        user32 = mock.Mock()
        user32.CallWindowProcW.return_value = 77
        windll = mock.Mock(user32=user32)
        tray = self._new_tray()

        with mock.patch.object(conn_widget.ctypes, "windll", windll, create=True):
            result = tray._handler(1, 0x1234, 0, 0)

        self.assertEqual(result, 77)
        tray.readd.assert_not_called()
        user32.CallWindowProcW.assert_called_once()


class InitTrayHotkeyTests(unittest.TestCase):
    def _new_widget(self):
        w = conn_widget.ConnWidget.__new__(conn_widget.ConnWidget)
        w.cfg = {"lang": "zh"}
        w.root = mock.Mock()
        return w

    def test_register_failure_sets_flag_and_schedules_toast(self):
        w = self._new_widget()
        fake_tray = mock.Mock()
        fake_tray.register_hotkey.return_value = False

        with mock.patch.object(conn_widget, "TrayIcon", return_value=fake_tray), \
                mock.patch.object(conn_widget.sys, "platform", "win32"):
            w._init_tray()

        self.assertIs(w.tray, fake_tray)
        self.assertFalse(w.hotkey_ok)
        self.assertTrue(w.root.after.called)
        delay, callback = w.root.after.call_args.args
        self.assertGreater(delay, 0)
        w._toast = mock.Mock()
        callback()
        w._toast.assert_called_once_with(
            conn_widget.hotkey_fail_message(False, "zh")
        )

    def test_register_success_keeps_flag_and_does_not_toast(self):
        w = self._new_widget()
        fake_tray = mock.Mock()
        fake_tray.register_hotkey.return_value = True

        with mock.patch.object(conn_widget, "TrayIcon", return_value=fake_tray), \
                mock.patch.object(conn_widget.sys, "platform", "win32"):
            w._init_tray()

        self.assertTrue(w.hotkey_ok)
        self.assertFalse(w.root.after.called)

    def test_non_windows_failure_does_not_toast(self):
        w = self._new_widget()
        fake_tray = mock.Mock()
        fake_tray.register_hotkey.return_value = False

        with mock.patch.object(conn_widget, "TrayIcon", return_value=fake_tray), \
                mock.patch.object(conn_widget.sys, "platform", "linux"):
            w._init_tray()

        self.assertFalse(w.hotkey_ok)
        self.assertFalse(w.root.after.called)


if __name__ == "__main__":
    unittest.main()
