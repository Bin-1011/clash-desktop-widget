# -*- coding: utf-8 -*-
"""组 B（H-9）配置保存失败要暴露的单元测试。

只用标准库，不创建 Tk 窗口。
"""

import json
import os
import tempfile
import unittest
from unittest import mock

import conn_widget


class SaveCfgTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "widget_state.json")
        patcher = mock.patch.object(conn_widget, "CONFIG_FILE", self.path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_writable_dir_returns_true_and_writes_expected_json(self):
        cfg = {
            "lang": "zh",
            "note": "配置成功",
            "profiles": [{"name": "默认", "api": "http://127.0.0.1:9090", "secret": ""}],
        }
        self.assertIs(conn_widget.save_cfg(cfg), True)
        with open(self.path, "r", encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), cfg)
        with open(self.path, "r", encoding="utf-8") as fh:
            self.assertIn("配置成功", fh.read())

    def test_open_failure_returns_false_without_raising(self):
        with mock.patch("builtins.open", side_effect=OSError("read-only directory")):
            self.assertIs(conn_widget.save_cfg({"lang": "zh"}), False)
        self.assertFalse(os.path.exists(self.path))

    def test_replace_failure_returns_false_without_raising(self):
        with mock.patch.object(conn_widget.os, "replace",
                               side_effect=PermissionError("denied")):
            self.assertIs(conn_widget.save_cfg({"lang": "zh"}), False)

    def test_failed_save_does_not_truncate_existing_config(self):
        original = json.dumps({"old": True, "note": "原配置"}, ensure_ascii=False, indent=2)
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(original)
        with mock.patch.object(conn_widget.os, "replace",
                               side_effect=OSError("disk full")):
            self.assertIs(conn_widget.save_cfg({"new": 1}), False)
        with open(self.path, "r", encoding="utf-8") as fh:
            self.assertEqual(fh.read(), original)


class SaveErrorNotifierTests(unittest.TestCase):
    def setUp(self):
        self.notifier = conn_widget.SaveErrorNotifier()

    def test_first_failure_reports_then_same_failure_is_silent(self):
        self.assertIs(self.notifier.note(False, OSError("denied")), True)
        self.assertIs(self.notifier.note(False, OSError("denied")), False)

    def test_success_resets_so_next_failure_reports_again(self):
        self.assertIs(self.notifier.note(False, OSError("denied")), True)
        self.assertIs(self.notifier.note(True, None), False)
        self.assertIs(self.notifier.note(False, OSError("denied")), True)

    def test_different_failure_reports_again(self):
        self.assertIs(self.notifier.note(False, OSError("denied")), True)
        self.assertIs(self.notifier.note(False, PermissionError("read-only")), True)

    def test_failure_without_exception_still_reports_once(self):
        self.assertIs(self.notifier.note(False, None), True)
        self.assertIs(self.notifier.note(False, None), False)

    def test_pure_should_report_helper(self):
        self.assertIs(conn_widget.should_report_save_error(None, OSError("denied")), True)
        key = conn_widget.save_error_key(OSError("denied"))
        self.assertIs(conn_widget.should_report_save_error(key, OSError("denied")), False)


class PersistReportsFailureTests(unittest.TestCase):
    """不建 Tk 窗口，只验证 _persist 会检查 save_cfg 的返回值并去重提示。"""

    def _widget(self):
        w = conn_widget.ConnWidget.__new__(conn_widget.ConnWidget)
        w.cfg = {}
        w.root = mock.Mock()
        w.root.winfo_x.return_value = 10
        w.root.winfo_y.return_value = 20
        w.W = 300
        w._save_notifier = conn_widget.SaveErrorNotifier()
        w._save_error = ""
        w._settings_error = ""
        w.toasts = []
        w._toast = w.toasts.append
        w.t = lambda key, **kw: f"{key}:{kw.get('path', '')}"
        return w

    def test_persist_toasts_same_failure_once_and_resets_after_success(self):
        w = self._widget()
        with mock.patch.object(conn_widget, "save_cfg", return_value=False), \
                mock.patch.object(conn_widget, "LAST_SAVE_ERROR", OSError("denied")):
            w._persist()
            w._persist()
        self.assertEqual(len(w.toasts), 1)
        self.assertIn("save_fail", w._settings_error)

        with mock.patch.object(conn_widget, "save_cfg", return_value=True), \
                mock.patch.object(conn_widget, "LAST_SAVE_ERROR", None):
            w._persist()
        self.assertEqual(w._settings_error, "")
        self.assertEqual(len(w.toasts), 1)

        with mock.patch.object(conn_widget, "save_cfg", return_value=False), \
                mock.patch.object(conn_widget, "LAST_SAVE_ERROR", OSError("denied")):
            w._persist()
        self.assertEqual(len(w.toasts), 2)

    def test_successful_save_keeps_autostart_error_visible(self):
        w = self._widget()
        w._settings_error = "autostart_fail"
        with mock.patch.object(conn_widget, "save_cfg", return_value=True), \
                mock.patch.object(conn_widget, "LAST_SAVE_ERROR", None):
            w._persist()
        self.assertEqual(w._settings_error, "autostart_fail")


class SaveFailI18nTests(unittest.TestCase):
    def test_save_fail_message_exists_in_both_languages(self):
        for lang in ("zh", "en"):
            self.assertIn("save_fail", conn_widget.I18N[lang])
        self.assertIn("设置可能不会被记住", conn_widget.I18N["zh"]["save_fail"])
        self.assertIn("remembered", conn_widget.I18N["en"]["save_fail"])


if __name__ == "__main__":
    unittest.main()
