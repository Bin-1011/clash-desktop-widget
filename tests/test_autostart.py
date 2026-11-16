# -*- coding: utf-8 -*-
"""组 A 开机自启修复的单元测试。

测试只使用标准库，mock 掉 Windows API / 当前可执行文件，不启动 Tk。
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

import conn_widget


class BuildVbsTests(unittest.TestCase):
    def test_frozen_exe_path_with_spaces(self):
        cmd = r'"C:\Program Files\Clash\ClashConnWidget.exe"'
        content = conn_widget.build_autostart_vbs(cmd)
        self.assertIn(
            'sh.Run """C:\\Program Files\\Clash\\ClashConnWidget.exe""", 0, False',
            content,
        )
        self.assertTrue(content.startswith('Set sh = CreateObject("WScript.Shell")'))

    def test_unpacked_python_and_script_with_chinese_space_path(self):
        cmd = (r'"C:\Python314\pythonw.exe" '
               r'"D:\中文 目录\conn_widget.py"')
        content = conn_widget.build_autostart_vbs(cmd)
        self.assertIn(
            'sh.Run """C:\\Python314\\pythonw.exe"" '
            '""D:\\中文 目录\\conn_widget.py""", 0, False',
            content,
        )

    def test_generated_vbs_is_valid_three_quote_form(self):
        content = conn_widget.build_autostart_vbs(r'"C:\a b\app.exe"')
        run_line = [ln for ln in content.splitlines() if ln.startswith("sh.Run")][0]
        self.assertTrue(run_line.startswith('sh.Run """'))
        self.assertIn('""", 0, False', run_line)


class SetAutostartTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.appdata = self.tmp.name

    def _startup_file(self):
        return os.path.join(
            self.appdata, "Microsoft", "Windows", "Start Menu", "Programs",
            "Startup", "ClashConnWidget.vbs",
        )

    def test_true_writes_utf16_le_bom_with_expected_quotes(self):
        exe = r"C:\Program Files\Clash 中文工具\ClashConnWidget.exe"
        with mock.patch.dict(os.environ, {"APPDATA": self.appdata}), \
                mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "executable", exe):
            ok = conn_widget.set_autostart(True)

        self.assertTrue(ok)
        path = self._startup_file()
        self.assertTrue(os.path.exists(path))
        with open(path, "rb") as fh:
            raw = fh.read()
        self.assertTrue(raw.startswith(b"\xff\xfe"), "VBS 必须是 UTF-16 LE 带 BOM")
        text = raw.decode("utf-16")
        self.assertIn("中文", text)
        self.assertIn(
            'sh.Run """C:\\Program Files\\Clash 中文工具\\ClashConnWidget.exe""", 0, False',
            text,
        )

    def test_unpacked_true_uses_python_and_script_path(self):
        script = os.path.join(r"D:\中文 目录", "conn_widget.py")
        with mock.patch.dict(os.environ, {"APPDATA": self.appdata}), \
                mock.patch.object(sys, "frozen", False, create=True), \
                mock.patch.object(sys, "executable", r"C:\Python314\pythonw.exe"), \
                mock.patch.object(conn_widget, "app_dir", return_value=r"D:\中文 目录"):
            ok = conn_widget.set_autostart(True)

        self.assertTrue(ok)
        with open(self._startup_file(), "rb") as fh:
            text = fh.read().decode("utf-16")
        self.assertIn(
            'sh.Run """C:\\Python314\\pythonw.exe"" '
            f'""{script}""", 0, False',
            text,
        )

    def test_false_removes_file(self):
        path = self._startup_file()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(b"x")
        with mock.patch.dict(os.environ, {"APPDATA": self.appdata}):
            ok = conn_widget.set_autostart(False)
        self.assertTrue(ok)
        self.assertFalse(os.path.exists(path))

    def test_no_appdata_returns_false_and_creates_nothing_in_cwd(self):
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as cwd:
            try:
                os.chdir(cwd)
                with mock.patch.dict(os.environ, {}, clear=True):
                    ok = conn_widget.set_autostart(True)
                self.assertFalse(ok)
                self.assertFalse(os.path.exists(os.path.join(cwd, "Microsoft")))
            finally:
                os.chdir(old_cwd)

    def test_write_failure_returns_false(self):
        with mock.patch.dict(os.environ, {"APPDATA": self.appdata}), \
                mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch("builtins.open", side_effect=OSError("denied")):
            ok = conn_widget.set_autostart(True)
        self.assertFalse(ok)


class ApplyAutostartFlagTests(unittest.TestCase):
    def test_success_updates_cfg(self):
        cfg = {"autostart": False}
        with mock.patch.object(conn_widget, "set_autostart", return_value=True) as m:
            ok = conn_widget.apply_autostart_flag(cfg, True)
        self.assertTrue(ok)
        self.assertIs(cfg["autostart"], True)
        m.assert_called_once_with(True)

    def test_failure_does_not_leave_flag_true(self):
        cfg = {"autostart": True}
        with mock.patch.object(conn_widget, "set_autostart", return_value=False):
            ok = conn_widget.apply_autostart_flag(cfg, True)
        self.assertFalse(ok)
        self.assertIs(cfg["autostart"], False)

    def test_disable_updates_cfg(self):
        cfg = {"autostart": True}
        with mock.patch.object(conn_widget, "set_autostart", return_value=True):
            ok = conn_widget.apply_autostart_flag(cfg, False)
        self.assertTrue(ok)
        self.assertIs(cfg["autostart"], False)


class RefreshAutostartTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.appdata = self.tmp.name
        self.path = os.path.join(
            self.appdata, "Microsoft", "Windows", "Start Menu", "Programs",
            "Startup", "ClashConnWidget.vbs",
        )

    def test_enabled_rewrites_with_current_executable(self):
        cfg = {"autostart": True}
        with mock.patch.dict(os.environ, {"APPDATA": self.appdata}), \
                mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "executable", r"C:\Old\clash.exe"):
            self.assertTrue(conn_widget.refresh_autostart_if_enabled(cfg))

        with open(self.path, "rb") as fh:
            old = fh.read().decode("utf-16")
        self.assertIn(r'"""C:\Old\clash.exe"""', old)

        with mock.patch.dict(os.environ, {"APPDATA": self.appdata}), \
                mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "executable", r"D:\New Folder\clash.exe"):
            self.assertTrue(conn_widget.refresh_autostart_if_enabled(cfg))

        with open(self.path, "rb") as fh:
            new = fh.read().decode("utf-16")
        self.assertIn(r'"""D:\New Folder\clash.exe"""', new)
        self.assertNotIn(r'C:\Old\clash.exe', new)
        self.assertIs(cfg["autostart"], True)

    def test_disabled_does_not_write(self):
        cfg = {"autostart": False}
        with mock.patch.object(conn_widget, "set_autostart") as m:
            result = conn_widget.refresh_autostart_if_enabled(cfg)
        self.assertFalse(result)
        m.assert_not_called()
        self.assertFalse(os.path.exists(self.path))


class I18nTests(unittest.TestCase):
    def test_autostart_fail_message_exists_in_both_languages(self):
        self.assertIn("autostart_fail", conn_widget.I18N["zh"])
        self.assertIn("autostart_fail", conn_widget.I18N["en"])


if __name__ == "__main__":
    unittest.main()
