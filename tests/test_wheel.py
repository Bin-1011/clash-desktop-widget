# -*- coding: utf-8 -*-
"""组 F（X11 滚轮）滚轮步数换算的单元测试。

只用标准库；用假事件对象，不启动 Tk mainloop。
"""

import types
import unittest

import conn_widget


class WheelStepsTests(unittest.TestCase):
    def test_windows_positive_delta_scrolls_up(self):
        self.assertEqual(conn_widget.wheel_steps(types.SimpleNamespace(delta=120)), 1)
        self.assertEqual(conn_widget.wheel_steps(types.SimpleNamespace(delta=240)), 2)

    def test_windows_negative_delta_scrolls_down(self):
        self.assertEqual(conn_widget.wheel_steps(types.SimpleNamespace(delta=-120)), -1)
        self.assertEqual(conn_widget.wheel_steps(types.SimpleNamespace(delta=-240)), -2)

    def test_x11_button_4_scrolls_up_when_delta_is_zero(self):
        e = types.SimpleNamespace(delta=0, num=4)
        self.assertEqual(conn_widget.wheel_steps(e), 1)

    def test_x11_button_5_scrolls_down_when_delta_is_zero(self):
        e = types.SimpleNamespace(delta=0, num=5)
        self.assertEqual(conn_widget.wheel_steps(e), -1)

    def test_x11_button_works_when_delta_is_missing(self):
        self.assertEqual(conn_widget.wheel_steps(types.SimpleNamespace(num=4)), 1)
        self.assertEqual(conn_widget.wheel_steps(types.SimpleNamespace(num=5)), -1)

    def test_other_buttons_and_zero_delta_do_nothing(self):
        self.assertEqual(
            conn_widget.wheel_steps(types.SimpleNamespace(delta=0, num=1)), 0)
        self.assertEqual(conn_widget.wheel_steps(types.SimpleNamespace()), 0)


if __name__ == "__main__":
    unittest.main()
