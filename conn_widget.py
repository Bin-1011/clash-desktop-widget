# -*- coding: utf-8 -*-
"""
Clash / Mihomo 桌面连接小窗 v2

- 任意 Clash / mihomo 后台（多配置档、地址容错、https、路径前缀、secret）
- 只显示有活动的连接，按实时速率排序；「不限」行数时可滚轮浏览、右侧悬浮滑块
- 双风格：精修 / 仪表盘；四套主题；中英双语
- 搜索、点表头排序、点行看详情、断连诊断、首启引导、自动检测后台
- 托盘图标、关闭到托盘、开机自启、可打包单文件 exe

依赖：仅 Python 3.10+ 标准库（tkinter / urllib / ctypes）。
"""

import argparse
import base64
import ctypes
import json
import os
import queue
import re
import socket
import ssl
import struct
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
import winreg
from tkinter import colorchooser
from tkinter import font as tkfont

VERSION = "3.0.0"
APP_REPO = "Bin-1011/clash-desktop-widget"
APP_AUTHOR = "Bin-1011"
APP_NAME = "Clash 连接小窗"


def app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def res_path(name: str) -> str:
    base = getattr(sys, "_MEIPASS", None) or app_dir()
    p = os.path.join(base, name)
    return p if os.path.exists(p) else os.path.join(app_dir(), name)


CONFIG_FILE = os.path.join(app_dir(), "widget_state.json")
DEFAULT_API = "http://192.168.50.1:9999"
ACTIVE_MIN_BPS = 1.0
HIST_LEN = 60

DEFAULT_CFG = {
    "profiles": [{"name": "默认", "api": DEFAULT_API, "secret": ""}],
    "active": 0,
    "interval": 1.0,
    "theme": "dark",
    "accent": "",
    "style": "polish",
    "lang": "zh",
    "font_scale": 1.0,
    "opacity": 1.0,
    "rows": 10,
    "view": "conn",
    "curve": "60",
    "mini": False,
    "native": False,
    "show_cols": {"rule": False, "src": False, "net": False},
    "topmost": True,
    "collapsed": False,
    "collapse_start": False,
    "close_to_tray": True,
    "autostart": False,
    "filter_ip": "",
    "sort": "speed",
    "sort_desc": True,
    "col_w": None,
    "win_w": None,
    "win_h": None,
    "x": None,
    "y": None,
    "first_run_done": False,
}

THEMES = {
    "dark": {
        "zh": "暗夜", "en": "Dark",
        "bg": "#0e1015", "row": "#0e1015", "row_alt": "#12151b",
        "hover": "#1a202b", "sel": "#1f2733", "border": "#2b3342",
        "title": "#e8edf5", "sub": "#78849a", "colhdr": "#46505f",
        "host": "#dbe2ec", "host_idle": "#7d8798",
        "node": "#a78bfa", "node_idle": "#5a6474", "direct": "#6b7787",
        "down": "#34d399", "up": "#60a5fa", "zero": "#3d4757",
        "ok": "#22c55e", "err": "#ef4444", "wait": "#f59e0b",
        "chip_bg": "#1a2029", "chip_fg": "#93a1b5", "chip_hover": "#232b38",
        "chip_on_bg": "#2f3d52", "chip_on_fg": "#eaf0f8",
        "menu_bg": "#171c25", "menu_fg": "#e6ebf3", "menu_sel": "#2a3446",
        "input_bg": "#141a23", "accent": "#60a5fa",
        "head_bg": "#0b0d12", "bar_track": "#1a2029",
        "dots": ["#f87171", "#fbbf24", "#34d399", "#60a5fa", "#a78bfa", "#f472b6", "#22d3ee", "#94a3b8"],
    },
    "graphite": {
        "zh": "石墨", "en": "Graphite",
        "bg": "#17181c", "row": "#17181c", "row_alt": "#1b1d22",
        "hover": "#232630", "sel": "#2a2e3a", "border": "#33373f",
        "title": "#eceff4", "sub": "#8a919e", "colhdr": "#6d7583",
        "host": "#e2e6ec", "host_idle": "#8b93a1",
        "node": "#8fb8de", "node_idle": "#5f6874", "direct": "#737b88",
        "down": "#5cc98d", "up": "#6aa8e8", "zero": "#444b57",
        "ok": "#5cc98d", "err": "#e5735f", "wait": "#d9a441",
        "chip_bg": "#22252c", "chip_fg": "#9aa3b1", "chip_hover": "#2b2f38",
        "chip_on_bg": "#3a4250", "chip_on_fg": "#eef2f7",
        "menu_bg": "#22252c", "menu_fg": "#eceff4", "menu_sel": "#363c47",
        "input_bg": "#1d2026", "accent": "#8fb8de",
        "head_bg": "#141519", "bar_track": "#262a31",
        "dots": ["#e5735f", "#d9a441", "#5cc98d", "#6aa8e8", "#a48bd4", "#d98bb6", "#59c3c3", "#98a2b3"],
    },
    "nord": {
        "zh": "午夜蓝", "en": "Nord",
        "bg": "#2e3440", "row": "#2e3440", "row_alt": "#333a47",
        "hover": "#3b4252", "sel": "#434c5e", "border": "#4c566a",
        "title": "#eceff4", "sub": "#9aa7ba", "colhdr": "#7d8ca1",
        "host": "#e5e9f0", "host_idle": "#9aa7ba",
        "node": "#b48ead", "node_idle": "#7b8798", "direct": "#7c8a9e",
        "down": "#8fbcbb", "up": "#81a1c1", "zero": "#4c566a",
        "ok": "#a3be8c", "err": "#bf616a", "wait": "#ebcb8b",
        "chip_bg": "#3b4252", "chip_fg": "#c3ccd9", "chip_hover": "#434c5e",
        "chip_on_bg": "#4c566a", "chip_on_fg": "#eceff4",
        "menu_bg": "#3b4252", "menu_fg": "#eceff4", "menu_sel": "#4c566a",
        "input_bg": "#343b47", "accent": "#88c0d0",
        "head_bg": "#272c37", "bar_track": "#3b4252",
        "dots": ["#bf616a", "#d08770", "#ebcb8b", "#a3be8c", "#88c0d0", "#81a1c1", "#b48ead", "#8fbcbb"],
    },
    "light": {
        "zh": "浅色", "en": "Light",
        "bg": "#f6f7f9", "row": "#f6f7f9", "row_alt": "#ffffff",
        "hover": "#eef1f6", "sel": "#e3e9f2", "border": "#d8dee8",
        "title": "#1d2430", "sub": "#6b7686", "colhdr": "#8b95a6",
        "host": "#25303f", "host_idle": "#8a94a3",
        "node": "#6d4aff", "node_idle": "#a5aec0", "direct": "#8b95a3",
        "down": "#059669", "up": "#2563eb", "zero": "#c3cad6",
        "ok": "#16a34a", "err": "#dc2626", "wait": "#d97706",
        "chip_bg": "#e9edf3", "chip_fg": "#55606f", "chip_hover": "#dde3ec",
        "chip_on_bg": "#dbeafe", "chip_on_fg": "#1d4ed8",
        "menu_bg": "#ffffff", "menu_fg": "#1d2430", "menu_sel": "#e9eef7",
        "input_bg": "#ffffff", "accent": "#2563eb",
        "head_bg": "#eef1f5", "bar_track": "#e3e8f0",
        "dots": ["#dc2626", "#d97706", "#059669", "#2563eb", "#7c3aed", "#db2777", "#0891b2", "#64748b"],
    },
}
THEME_ORDER = ["auto", "dark", "graphite", "nord", "light"]
ACCENTS = ["#60a5fa", "#34d399", "#f59e0b", "#f472b6", "#a78bfa", "#22d3ee", "#ef4444", "#94a3b8"]

STYLES = {
    "polish": {"row_h": 27, "header_h": 20, "spark": 0, "title": 10, "pad": 12, "bar": 2},
    "dash": {"row_h": 32, "header_h": 26, "spark": 40, "title": 11, "pad": 14, "bar": 3},
}
STYLE_ORDER = ["polish", "dash"]

I18N = {
    "zh": {
        "app": "连接监视", "starting": "启动中…", "count": "{n} 条 · {a} 活跃",
        "all_ip": "全部 IP", "all": "全部",
        "col_host": "主机", "col_node": "节点", "col_down": "下行", "col_up": "上行",
        "direct": "直连", "empty": "暂无活动连接", "no_ip": "该 IP 下暂无连接",
        "no_match": "没有匹配的连接",
        "offline": "API 未连接", "diagnose": "诊断",
        "menu_open": "打开 Clash 面板", "menu_copy": "复制全部主机名",
        "menu_top": "窗口置顶", "menu_collapse": "折叠 / 展开", "menu_colw": "重置列宽",
        "menu_winw": "重置窗口宽度", "menu_interval": "刷新频率", "menu_settings": "设置…",
        "menu_search": "搜索…", "menu_quit": "退出", "search_btn": "⌕ 搜索",
        "set_title": "设置",
        "set_appearance": "外观", "set_list": "列表", "set_behavior": "行为",
        "set_conn": "后台连接", "set_lang": "语言", "set_about": "关于",
        "theme": "主题", "style": "风格", "font": "字号", "opacity": "不透明度",
        "accent": "强调色", "custom": "自定义", "default": "默认", "theme_auto": "自动",
        "rows": "显示行数", "interval": "刷新频率",
        "topmost": "窗口置顶", "collapse_start": "启动时折叠",
        "close_to_tray": "关闭收进托盘", "autostart": "开机自启",
        "on": "开", "off": "关", "small": "小", "normal": "标准", "large": "大",
        "rows_n": "{n} 行", "rows_all": "不限", "sec": "{v} 秒",
        "polish": "精修", "dash": "仪表盘",
        "profile": "配置档", "add_profile": "新增", "del_profile": "删除",
        "p_name": "名称", "p_api": "地址", "p_secret": "Secret",
        "test": "测试连接", "testing": "测试中…", "save": "保存",
        "test_ok": "连接成功 · {ver}", "test_fail": "失败：{msg}",
        "auto_detect": "自动检测", "detecting": "正在检测本机与网关…",
        "found": "发现 {url}（{ver}）", "not_found": "没有发现可用的后台",
        "import_cfg": "导入配置", "export_cfg": "导出配置",
        "wizard_title": "连接你的 Clash 后台", "wizard_desc":
            "填写 Clash / mihomo 的外部控制器地址（例如 http://192.168.50.1:9999）。\n地址带 /ui/#/connections 也可以，会自动识别。",
        "wizard_start": "开始使用", "wizard_skip": "跳过，用默认地址",
        "details_title": "连接详情", "d_host": "主机", "d_node": "节点", "d_rule": "规则",
        "d_chain": "链路", "d_src": "来源", "d_net": "协议", "d_data": "累计",
        "d_time": "持续时间", "copy": "复制", "close": "关闭",
        "reset": "恢复默认", "reset_colw": "重置列宽", "reset_winw": "重置窗口宽度",
        "search_ph": "搜索主机 / 节点…",
        "tray_show": "显示窗口", "tray_hide": "隐藏窗口", "tray_quit": "退出",
        "about_line": "数据源 {api} · 内核 {k}",
        "about_version": "版本 v{v} · MIT License",
        "about_author": "作者 {a}",
        "check_update": "检查更新", "checking": "检查中…",
        "update_latest": "已是最新版本 v{v}",
        "update_new": "发现新版本 v{v}，点击这里打开下载页",
        "update_none": "仓库还没有发布 Release",
        "update_err": "检查失败：{msg}",
        "diag_auth": "Secret 不正确（HTTP 401/403），请检查后台的 secret",
        "diag_not_clash": "该地址不是 Clash 接口（HTTP 404），检查端口或路径前缀",
        "diag_timeout": "连接超时：检查 IP、端口、防火墙与 external-controller 是否 0.0.0.0",
        "diag_refused": "端口拒绝连接：服务未启动或端口写错",
        "diag_net": "网络错误：{msg}", "diag_http": "接口返回 HTTP {code}",
        "diag_other": "错误：{msg}", "retry_hint": "点「设置」检查地址与 Secret",
        "sort_speed": "速率", "sort_host": "主机", "sort_node": "节点", "sort_time": "时间",
        "tab_conn": "连接", "tab_node": "节点", "tab_device": "设备",
        "view": "视图", "mini": "迷你模式",
        "shell": "窗口外壳", "shell_borderless": "无边框", "shell_native": "系统窗口",
        "cols": "显示列", "c_rule": "规则", "c_src": "来源", "c_net": "协议",
        "blur": "毛玻璃（实验）",
        "copy_row": "复制整行", "copy_tsv": "复制全部（表格）",
        "only_ip": "只看这个 IP", "only_node": "只看这个节点",
        "mini_hint": "{n} 条 · {a} 活跃",
    },
    "en": {
        "app": "Connections", "starting": "Starting…", "count": "{n} conns · {a} active",
        "all_ip": "All IPs", "all": "All",
        "col_host": "Host", "col_node": "Node", "col_down": "Down", "col_up": "Up",
        "direct": "Direct", "empty": "No active connections", "no_ip": "No connection from this IP",
        "no_match": "No matching connection",
        "offline": "API offline", "diagnose": "Diagnostics",
        "menu_open": "Open Clash dashboard", "menu_copy": "Copy all hostnames",
        "menu_top": "Always on top", "menu_collapse": "Collapse / expand",
        "menu_colw": "Reset column widths", "menu_winw": "Reset window width",
        "menu_interval": "Refresh rate", "menu_settings": "Settings…",
        "menu_search": "Search…", "menu_quit": "Quit", "search_btn": "⌕ Search",
        "set_title": "Settings",
        "set_appearance": "Appearance", "set_list": "List", "set_behavior": "Behavior",
        "set_conn": "Backend", "set_lang": "Language", "set_about": "About",
        "theme": "Theme", "style": "Style", "font": "Font size", "opacity": "Opacity",
        "accent": "Accent", "custom": "Custom", "default": "Default", "theme_auto": "System",
        "rows": "Visible rows", "interval": "Refresh rate",
        "topmost": "Always on top", "collapse_start": "Start collapsed",
        "close_to_tray": "Close to tray", "autostart": "Run at startup",
        "on": "On", "off": "Off", "small": "Small", "normal": "Normal", "large": "Large",
        "rows_n": "{n} rows", "rows_all": "All", "sec": "{v}s",
        "polish": "Polished", "dash": "Dashboard",
        "profile": "Profile", "add_profile": "Add", "del_profile": "Delete",
        "p_name": "Name", "p_api": "URL", "p_secret": "Secret",
        "test": "Test", "testing": "Testing…", "save": "Save",
        "test_ok": "Connected · {ver}", "test_fail": "Failed: {msg}",
        "auto_detect": "Detect", "detecting": "Scanning localhost and gateway…",
        "found": "Found {url} ({ver})", "not_found": "No backend found",
        "import_cfg": "Import", "export_cfg": "Export",
        "wizard_title": "Connect to your Clash", "wizard_desc":
            "Enter the external-controller URL (e.g. http://192.168.50.1:9999).\nA pasted dashboard link with /ui/#/connections also works.",
        "wizard_start": "Start", "wizard_skip": "Skip, use default",
        "details_title": "Connection details", "d_host": "Host", "d_node": "Node",
        "d_rule": "Rule", "d_chain": "Chain", "d_src": "Source", "d_net": "Network",
        "d_data": "Transferred", "d_time": "Duration", "copy": "Copy", "close": "Close",
        "reset": "Reset", "reset_colw": "Reset widths", "reset_winw": "Reset window width",
        "search_ph": "Search host / node…",
        "tray_show": "Show window", "tray_hide": "Hide window", "tray_quit": "Quit",
        "about_line": "source {api} · kernel {k}",
        "about_version": "Version v{v} · MIT License",
        "about_author": "Author {a}",
        "check_update": "Check for updates", "checking": "Checking…",
        "update_latest": "Up to date (v{v})",
        "update_new": "v{v} available — click to open",
        "update_none": "No releases published yet",
        "update_err": "Check failed: {msg}",
        "diag_auth": "Wrong secret (HTTP 401/403)",
        "diag_not_clash": "Not a Clash API (HTTP 404) — check port / path prefix",
        "diag_timeout": "Timed out — check IP, port, firewall and external-controller 0.0.0.0",
        "diag_refused": "Connection refused — service down or wrong port",
        "diag_net": "Network error: {msg}", "diag_http": "HTTP {code}",
        "diag_other": "Error: {msg}", "retry_hint": "Open Settings to fix URL / secret",
        "sort_speed": "Speed", "sort_host": "Host", "sort_node": "Node", "sort_time": "Time",
        "tab_conn": "Conns", "tab_node": "Nodes", "tab_device": "Devices",
        "view": "View", "mini": "Mini mode",
        "shell": "Window shell", "shell_borderless": "Borderless", "shell_native": "System window",
        "cols": "Columns", "c_rule": "Rule", "c_src": "Source", "c_net": "Proto",
        "blur": "Acrylic (experimental)",
        "copy_row": "Copy row", "copy_tsv": "Copy all (table)",
        "only_ip": "Only this IP", "only_node": "Only this node",
        "mini_hint": "{n} conns · {a} active",
    },
}


# ---------------------------------------------------------------- 工具
def dpi_scale() -> float:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        dpi = ctypes.windll.user32.GetDpiForSystem()
    except Exception:
        dpi = 96
    return max(1.0, min(3.0, dpi / 96.0))


def fmt_bytes(bps: float) -> str:
    bps = max(0.0, float(bps or 0))
    if bps < 1024:
        return f"{bps:.0f} B/s"
    for unit in ("KB/s", "MB/s", "GB/s"):
        bps /= 1024.0
        if bps < 1024 or unit == "GB/s":
            return f"{bps:.2f} {unit}" if bps < 10 else f"{bps:.1f} {unit}"
    return f"{bps:.1f} GB/s"


def fmt_short(bps: float) -> str:
    bps = max(0.0, float(bps or 0))
    if bps < 1024:
        return f"{bps:.0f}B"
    for unit in ("K", "M", "G"):
        bps /= 1024.0
        if bps < 1024 or unit == "G":
            return f"{bps:.1f}{unit}" if bps < 10 else f"{bps:.0f}{unit}"
    return f"{bps:.0f}G"


def fmt_time(seconds: float) -> str:
    s = int(max(0, seconds))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    if s < 86400:
        return f"{s // 3600}h {(s % 3600) // 60}m"
    return f"{s // 86400}d {(s % 86400) // 3600}h"


def norm_api(text: str) -> str:
    """把用户输入/粘贴的地址规范成 API 根地址。"""
    u = (text or "").strip().strip('"').strip("'")
    if not u:
        return ""
    u = re.sub(r"/ui/?.*$", "", u, flags=re.I)
    u = re.sub(r"/#/.*$", "", u)
    if not re.match(r"^https?://", u, re.I):
        u = "http://" + u
    u = u.rstrip("/")
    return u


def hex_rgb(h: str):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def blend(h1: str, h2: str, t: float) -> str:
    r1, g1, b1 = hex_rgb(h1)
    r2, g2, b2 = hex_rgb(h2)
    return "#%02x%02x%02x" % (int(r1 + (r2 - r1) * t),
                              int(g1 + (g2 - g1) * t),
                              int(b1 + (b2 - b1) * t))


def fit_text(text: str, font: tkfont.Font, max_px: int) -> str:
    if not text:
        return ""
    if font.measure(text) <= max_px:
        return text
    ell = "…"
    ew = font.measure(ell)
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.measure(text[:mid]) + ew <= max_px:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + ell if lo > 0 else ell


def load_cfg() -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CFG))
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        data = {}
    if isinstance(data, dict):
        for k in DEFAULT_CFG:
            if k in data:
                cfg[k] = data[k]
        old_api = data.get("api")
        if old_api and not data.get("profiles"):
            cfg["profiles"] = [{"name": "默认", "api": old_api,
                                "secret": data.get("secret", "")}]
    if not isinstance(cfg.get("profiles"), list) or not cfg["profiles"]:
        cfg["profiles"] = json.loads(json.dumps(DEFAULT_CFG["profiles"]))
    cfg["profiles"] = [{"name": str(p.get("name") or f"Config {i+1}"),
                        "api": norm_api(p.get("api", "")),
                        "secret": str(p.get("secret") or "")}
                       for i, p in enumerate(cfg["profiles"])]
    cfg["active"] = max(0, min(int(cfg.get("active", 0) or 0), len(cfg["profiles"]) - 1))
    if cfg["theme"] not in THEMES and cfg["theme"] != "auto":
        cfg["theme"] = "dark"
    if cfg["style"] not in STYLES:
        cfg["style"] = "polish"
    if cfg["lang"] not in I18N:
        cfg["lang"] = "zh"
    if not (isinstance(cfg["rows"], int) or cfg["rows"] == "all"):
        cfg["rows"] = 10
    if cfg.get("view") not in ("conn", "node", "device"):
        cfg["view"] = "conn"
    if cfg.get("curve") not in ("60", "300", "1800"):
        cfg["curve"] = "60"
    if not isinstance(cfg.get("win_h"), (int, float)):
        cfg["win_h"] = None
    if not isinstance(cfg.get("show_cols"), dict):
        cfg["show_cols"] = {"rule": False, "src": False, "net": False}
    for k in ("rule", "src", "net"):
        cfg["show_cols"][k] = bool(cfg["show_cols"].get(k, False))
    return cfg


def save_cfg(cfg: dict) -> None:
    try:
        tmp = CONFIG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, CONFIG_FILE)
    except Exception:
        pass


def autostart_file() -> str:
    base = os.environ.get("APPDATA", "")
    return os.path.join(base, "Microsoft", "Windows", "Start Menu", "Programs",
                        "Startup", "ClashConnWidget.vbs")


def set_autostart(flag: bool) -> bool:
    p = autostart_file()
    try:
        if flag:
            if getattr(sys, "frozen", False):
                cmd = f'"{sys.executable}"'
            else:
                cmd = f'"{sys.executable}" "{os.path.join(app_dir(), "conn_widget.py")}"'
            content = ('Set sh = CreateObject("WScript.Shell")\r\n'
                       f'sh.Run "{cmd.replace(chr(34), chr(34)*2)}", 0, False\r\n')
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(content)
        elif os.path.exists(p):
            os.remove(p)
        return True
    except Exception:
        return False


def system_dark() -> bool:
    """读取 Windows「应用使用浅色主题」设置；读不到时按深色处理。"""
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        v, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
        winreg.CloseKey(k)
        return int(v) == 0
    except Exception:
        return True


def gateway_ip() -> str:
    try:
        out = subprocess.run(["ipconfig"], capture_output=True, text=True,
                             errors="ignore", timeout=3,
                             creationflags=0x08000000).stdout
        for line in out.splitlines():
            if ("默认网关" in line or "Default Gateway" in line) and ":" in line:
                ip = line.split(":")[-1].strip()
                if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip):
                    return ip
    except Exception:
        pass
    return ""


def probe_api(base: str, secret: str, timeout: float = 0.6):
    """探测一个地址，返回 (api, version) 或 None。"""
    base = norm_api(base)
    if not base:
        return None
    try:
        req = urllib.request.Request(base + "/version")
        if secret:
            req.add_header("Authorization", "Bearer " + secret)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        return base, str(data.get("version") or data.get("meta") and "mihomo" or "clash")
    except Exception:
        return None


def discover_backends() -> list:
    hosts = ["127.0.0.1", "localhost"]
    gw = gateway_ip()
    if gw:
        hosts.append(gw)
    ports = (9090, 9999, 9091, 6170)
    found = []
    lock = threading.Lock()

    def work(h, p):
        r = probe_api(f"http://{h}:{p}", "", 0.5)
        if r:
            with lock:
                if r[0] not in [x[0] for x in found]:
                    found.append(r)

    threads = [threading.Thread(target=work, args=(h, p), daemon=True)
               for h in hosts for p in ports]
    for t in threads:
        t.start()
    for t in threads:
        t.join(1.2)
    return found


# ---------------------------------------------------------------- 轮询
class Poller(threading.Thread):
    """拉取 Clash 连接数据：优先 WebSocket 推送（mihomo 每秒推一次全量快照），
    失败或断开时自动回退到 HTTP 轮询。"""

    def __init__(self, api, secret, interval, out_q):
        super().__init__(daemon=True, name="clash-poller")
        self.api = api.rstrip("/")
        self.secret = secret or ""
        self.interval = interval
        self.out_q = out_q
        self.stop_evt = threading.Event()
        self.wake = threading.Event()
        self._lock = threading.Lock()
        self._reset = False
        self.kernel = "?"
        self.mode = "http"
        self._ws_disabled = False

    # ------------------------------------------------------------ 控制
    def set_endpoint(self, api, secret):
        with self._lock:
            self.api = (api or DEFAULT_API).rstrip("/")
            self.secret = secret or ""
            self._reset = True
            self.kernel = "?"
            self._ws_disabled = False
        self.wake.set()

    def set_interval(self, v):
        with self._lock:
            self.interval = max(0.2, float(v))
        self.wake.set()

    def stop(self):
        self.stop_evt.set()
        self.wake.set()

    def poke(self):
        self.wake.set()

    def _sleep(self, seconds):
        end = time.monotonic() + seconds
        while not self.stop_evt.is_set():
            remain = end - time.monotonic()
            if remain <= 0:
                return
            if self.wake.wait(min(remain, 0.2)):
                self.wake.clear()
                return

    def _check_reset(self):
        with self._lock:
            if self._reset:
                self._reset = False
                self._reset_state()

    # ------------------------------------------------------------ 数据获取
    def _get(self, path, timeout=3.0):
        with self._lock:
            api, secret = self.api, self.secret
        req = urllib.request.Request(api + path)
        if secret:
            req.add_header("Authorization", "Bearer " + secret)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))

    @staticmethod
    def _classify(exc):
        if isinstance(exc, urllib.error.HTTPError):
            if exc.code in (401, 403):
                return "auth", f"HTTP {exc.code}"
            if exc.code == 404:
                return "not_clash", "HTTP 404"
            return "http", f"HTTP {exc.code}"
        if isinstance(exc, urllib.error.URLError):
            reason = str(exc.reason)
            low = reason.lower()
            if "timed out" in low or "timeout" in low:
                return "timeout", reason[:80]
            if "refused" in low or "10061" in low:
                return "refused", reason[:80]
            return "net", reason[:80]
        return "other", str(exc)[:80]

    # ------------------------------------------------------------ 状态
    def _reset_state(self):
        self._prev = {}
        self._prev_ts = None
        self._prev_tot = None
        self._hot = {}
        self._hist = {"60": [], "300": [], "1800": []}
        self._tick = 0
        self._fail = 0

    def _ingest(self, raw):
        try:
            conns = raw.get("connections") or []
            tot_up = float(raw.get("uploadTotal") or 0)
            tot_down = float(raw.get("downloadTotal") or 0)
        except Exception:
            return
        now = time.monotonic()
        dt = (now - self._prev_ts) if self._prev_ts else 0.0
        new_prev = {}
        rows = []
        ip_counts = {}
        for conn in conns:
            cid = conn.get("id") or ""
            up = float(conn.get("upload") or 0)
            down = float(conn.get("download") or 0)
            old = self._prev.get(cid)
            if old is not None and dt > 0.15:
                ru = max(0.0, (up - old[0]) / dt)
                rd = max(0.0, (down - old[1]) / dt)
            else:
                ru = rd = 0.0
            if cid:
                new_prev[cid] = (up, down)
            meta = conn.get("metadata") or {}
            src = (meta.get("sourceIP") or "").strip()
            if src:
                ip_counts[src] = ip_counts.get(src, 0) + 1
            host = (meta.get("host") or "").strip() or (meta.get("sniffHost") or "").strip()
            if not host:
                dip = (meta.get("destinationIP") or "").strip()
                dport = str(meta.get("destinationPort") or "").strip()
                host = f"{dip}:{dport}" if dip else (meta.get("remoteDestination") or "—")
            chains = conn.get("chains") or []
            node = chains[0] if chains else ""
            is_direct = (not node) or node.upper() == "DIRECT"
            if ru + rd >= ACTIVE_MIN_BPS:
                self._hot[cid] = now
            rows.append({
                "id": cid, "src": src, "host": host,
                "node": "" if is_direct else node, "direct": is_direct,
                "rule": conn.get("rulePayload") or conn.get("rule") or "",
                "chain": " → ".join(reversed(chains)) if chains else "",
                "net": meta.get("network") or "",
                "sport": str(meta.get("sourcePort") or ""),
                "up": ru, "down": rd,
                "up_total": up, "down_total": down,
                "start": conn.get("start") or "",
                "hot": self._hot.get(cid, 0.0),
            })
        self._prev = new_prev
        self._prev_ts = now
        for cid in [k for k in self._hot if k not in new_prev]:
            self._hot.pop(cid, None)

        if self._prev_tot and dt > 0.15:
            g_up = max(0.0, (tot_up - self._prev_tot[0]) / dt)
            g_down = max(0.0, (tot_down - self._prev_tot[1]) / dt)
        else:
            g_up = sum(r["up"] for r in rows)
            g_down = sum(r["down"] for r in rows)
        self._prev_tot = (tot_up, tot_down)

        ts = time.time()
        self._tick += 1
        self._hist["60"].append([ts, g_up, g_down])
        if len(self._hist["60"]) > 60:
            del self._hist["60"][:-60]
        if self._tick % 5 == 0:
            self._hist["300"].append([ts, g_up, g_down])
            if len(self._hist["300"]) > 60:
                del self._hist["300"][:-60]
        if self._tick % 30 == 0:
            self._hist["1800"].append([ts, g_up, g_down])
            if len(self._hist["1800"]) > 60:
                del self._hist["1800"][:-60]

        rows.sort(key=lambda r: (r["down"] + r["up"] <= 0,
                                 -(r["down"] + r["up"]), -r["hot"]))
        active = sum(1 for r in rows if r["down"] + r["up"] >= ACTIVE_MIN_BPS)
        ips = sorted(((ip, n) for ip, n in ip_counts.items()),
                     key=lambda kv: (-kv[1], kv[0]))[:12]
        self.out_q.put({
            "ok": True, "ts": ts, "rows": rows,
            "count": len(rows), "active": active,
            "up": g_up, "down": g_down,
            "ips": [list(x) for x in ips],
            "hist": {k: list(v) for k, v in self._hist.items()},
            "kernel": self.kernel, "mode": self.mode,
        })

    # ------------------------------------------------------------ HTTP
    def _http_session(self, seconds=0):
        deadline = (time.monotonic() + seconds) if seconds else None
        self.mode = "http"
        while not self.stop_evt.is_set():
            self._check_reset()
            if deadline and time.monotonic() > deadline:
                return
            started = time.monotonic()
            try:
                raw = self._get("/connections")
                if self.kernel == "?":
                    try:
                        v = self._get("/version", 2.0)
                        self.kernel = str(v.get("version") or "clash")
                    except Exception:
                        self.kernel = "clash"
            except Exception as exc:
                self._fail += 1
                kind, detail = self._classify(exc)
                self.out_q.put({"ok": False, "kind": kind, "detail": detail,
                                "ts": time.time(), "kernel": self.kernel})
                self._sleep(min(3.0, 0.4 * self._fail))
                continue
            self._fail = 0
            self._ingest(raw)
            self._sleep(max(0.05, self.interval - (time.monotonic() - started)))

    # ------------------------------------------------------------ WebSocket
    def _ws_connect(self):
        with self._lock:
            api, secret = self.api, self.secret
        u = urllib.parse.urlsplit(api)
        secure = u.scheme == "https"
        host = u.hostname or ""
        port = u.port or (443 if secure else 80)
        path = (u.path or "") + "/connections"
        sock = socket.create_connection((host, port), timeout=5)
        if secure:
            import ssl
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
               "Upgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n")
        if secret:
            req += f"Authorization: Bearer {secret}\r\n"
        req += "\r\n"
        sock.sendall(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = sock.recv(4096)
            if not chunk:
                sock.close()
                return None, b""
            resp += chunk
        head, rest = resp.split(b"\r\n\r\n", 1)
        status = head.split(b"\r\n")[0]
        if b" 101 " not in status:
            sock.close()
            return None, b""
        return sock, rest

    @staticmethod
    def _ws_read(sock, buf):
        def need(n):
            nonlocal buf
            while len(buf) < n:
                chunk = sock.recv(65536)
                if not chunk:
                    raise ConnectionError("ws closed")
                buf += chunk

        need(2)
        b1, b2 = buf[0], buf[1]
        op = b1 & 0x0F
        masked = b2 & 0x80
        ln = b2 & 0x7F
        idx = 2
        if ln == 126:
            need(4)
            ln = struct.unpack(">H", buf[2:4])[0]
            idx = 4
        elif ln == 127:
            need(10)
            ln = struct.unpack(">Q", buf[2:10])[0]
            idx = 10
        if masked:
            need(idx + 4)
            mask = buf[idx:idx + 4]
            idx += 4
            need(idx + ln)
            data = bytes(buf[idx + i] ^ mask[i % 4] for i in range(ln))
        else:
            need(idx + ln)
            data = buf[idx:idx + ln]
        return op, data, buf[idx + ln:]

    @staticmethod
    def _ws_send(sock, op, data):
        mask = os.urandom(4)
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        n = len(data)
        header = bytes([0x80 | op])
        if n < 126:
            header += bytes([0x80 | n])
        elif n < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", n)
        sock.sendall(header + mask + payload)

    def _ws_session(self):
        try:
            sock, buf = self._ws_connect()
        except Exception:
            return False
        if sock is None:
            return False
        self.mode = "ws"
        got = False
        try:
            sock.settimeout(max(2.0, self.interval * 3))
            while not self.stop_evt.is_set():
                self._check_reset()
                try:
                    op, payload, buf = self._ws_read(sock, buf)
                except socket.timeout:
                    continue
                if op == 8:
                    break
                if op == 9:
                    self._ws_send(sock, 10, payload)
                    continue
                if op == 1 and payload:
                    try:
                        raw = json.loads(payload.decode("utf-8", "replace"))
                    except Exception:
                        continue
                    if self.kernel == "?":
                        try:
                            v = self._get("/version", 2.0)
                            self.kernel = str(v.get("version") or "clash")
                        except Exception:
                            self.kernel = "clash"
                    self._ingest(raw)
                    got = True
        except Exception:
            pass
        finally:
            try:
                sock.close()
            except Exception:
                pass
        self.mode = "http"
        return got

    # ------------------------------------------------------------ 主循环
    def run(self):
        self._reset_state()
        ws_fail = 0
        while not self.stop_evt.is_set():
            if not self._ws_disabled:
                got = self._ws_session()
                if self.stop_evt.is_set():
                    return
                if got:
                    ws_fail = 0
                else:
                    ws_fail += 1
                    if ws_fail >= 3:
                        self._ws_disabled = True
                    self._sleep(1.0)
                self._http_session(seconds=20 if got else 6)
            else:
                self._http_session(seconds=0)


# ---------------------------------------------------------------- 托盘
WM_TRAY = 0x0400 + 20
WM_HOTKEY = 0x0312
WM_LBUTTONUP, WM_RBUTTONUP, WM_LBUTTONDBLCLK = 0x0202, 0x0205, 0x0203
NIM_ADD, NIM_DELETE = 0, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 0x01, 0x02, 0x04


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint32),
        ("hWnd", ctypes.c_void_p),
        ("uID", ctypes.c_uint32),
        ("uFlags", ctypes.c_uint32),
        ("uCallbackMessage", ctypes.c_uint32),
        ("hIcon", ctypes.c_void_p),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", ctypes.c_uint32),
        ("dwStateMask", ctypes.c_uint32),
        ("szInfo", ctypes.c_wchar * 256),
        ("uVersion", ctypes.c_uint32),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", ctypes.c_uint32),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", ctypes.c_void_p),
    ]


class TrayIcon:
    """纯 ctypes 的托盘图标（Shell_NotifyIcon + 窗口过程钩子）。"""

    def __init__(self, root, icon_path, on_click, on_menu, tip=APP_NAME):
        self.ok = False
        self.root = root
        self.on_click = on_click
        self.on_menu = on_menu
        self.on_maximize = None
        try:
            user32 = ctypes.windll.user32
            user32.SetWindowLongPtrW.restype = ctypes.c_void_p
            user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                                 ctypes.c_void_p]
            user32.CallWindowProcW.restype = ctypes.c_ssize_t
            user32.CallWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                               ctypes.c_uint, ctypes.c_size_t,
                                               ctypes.c_ssize_t]
            self.hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
            self.hicon = 0
            if icon_path and os.path.exists(icon_path):
                self.hicon = ctypes.windll.user32.LoadImageW(
                    None, icon_path, 1, 16, 16, 0x10)  # IMAGE_ICON, LR_LOADFROMFILE
            if not self.hicon:
                self.hicon = ctypes.windll.user32.LoadIconW(None, 32512)

            self._wndproc_type = ctypes.WINFUNCTYPE(
                ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint,
                ctypes.c_size_t, ctypes.c_ssize_t)
            self._proc = self._wndproc_type(self._handler)
            self._old = user32.SetWindowLongPtrW(self.hwnd, -4,
                                                 ctypes.cast(self._proc, ctypes.c_void_p))
            self.nid = NOTIFYICONDATAW()
            self.nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            self.nid.hWnd = self.hwnd
            self.nid.uID = 1
            self.nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
            self.nid.uCallbackMessage = WM_TRAY
            self.nid.hIcon = self.hicon
            self.nid.szTip = tip[:127]
            self.ok = bool(ctypes.windll.shell32.Shell_NotifyIconW(NIM_ADD,
                                                                  ctypes.byref(self.nid)))
        except Exception:
            self.ok = False

    def _handler(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAY:
            ev = lparam & 0xFFFF
            try:
                if ev in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                    self.root.after(0, self.on_click)
                elif ev == WM_RBUTTONUP:
                    self.root.after(0, self.on_menu)
            except Exception:
                pass
            return 0
        if msg == 0x0112 and (wparam & 0xFFF0) == 0xF030:   # WM_SYSCOMMAND / SC_MAXIMIZE
            try:
                if getattr(self, "on_maximize", None):
                    self.root.after(0, self.on_maximize)
            except Exception:
                pass
            return 0
        if msg == WM_HOTKEY:
            try:
                if self._hotkey_cb:
                    self.root.after(0, self._hotkey_cb)
            except Exception:
                pass
            return 0
        return ctypes.windll.user32.CallWindowProcW(self._old, hwnd, msg, wparam, lparam)

    def register_hotkey(self, cb, vk=ord("C")):
        """Ctrl+Shift+C 呼出/隐藏（纯 RegisterHotKey，无需第三方库）。"""
        try:
            self._hotkey_cb = cb
            self._hotkey_ok = bool(ctypes.windll.user32.RegisterHotKey(
                self.hwnd, 1, 0x0002 | 0x0004, vk))
            return self._hotkey_ok
        except Exception:
            return False

    def remove(self):
        try:
            if getattr(self, "_hotkey_ok", False):
                ctypes.windll.user32.UnregisterHotKey(self.hwnd, 1)
                self._hotkey_ok = False
        except Exception:
            pass
        try:
            if self.ok:
                ctypes.windll.shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.nid))
                self.ok = False
            if getattr(self, "_old", None):
                ctypes.windll.user32.SetWindowLongPtrW(self.hwnd, -4, self._old)
                self._old = None
        except Exception:
            pass


# ---------------------------------------------------------------- 主窗
class ConnWidget:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.theme_name = self._resolved_theme()
        self.c = self._palette()
        self.st = STYLES[cfg["style"]]
        self.q = queue.Queue(maxsize=32)
        self.data = None
        self.rows = []
        self.rows_visible = []
        self.error = None
        self.kernel = "?"
        self.scroll = 0
        self.hover = -1
        self.press = None
        self.sb_hover = False
        self.sb_drag = None
        self.search_open = False
        self.details_win = None
        self.details_row = None
        self._set_win = None
        self._wizard = None
        self.tray = None
        self._save_job = None
        self._cdrag = None
        self._rsz = None
        self._sdrag = None

        self.scale = dpi_scale()
        self.fs = float(cfg["font_scale"])
        prof = cfg["profiles"][cfg["active"]]

        self.native = bool(cfg.get("native"))
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(APP_NAME)
        if self.native:
            try:
                ico = res_path("app.ico")
                if os.path.exists(ico):
                    self.root.iconbitmap(ico)
            except Exception:
                pass
        if not self.native:
            self.root.overrideredirect(True)
        self.root.configure(bg=self.c["bg"])
        self.root.attributes("-topmost", bool(cfg["topmost"]))
        try:
            alpha = max(0.4, min(1.0, float(cfg["opacity"])))
            if alpha < 0.999:      # 全不透明时不要设置 layered 属性，否则毛玻璃会失效
                self.root.attributes("-alpha", alpha)
        except Exception:
            pass

        self._fonts()
        self._metrics()
        self.p_name = tk.StringVar(master=self.root)
        self.p_api = tk.StringVar(master=self.root)
        self.p_secret = tk.StringVar(master=self.root)
        self._load_profile_vars()
        self._build()
        self._place_window()
        self._apply_collapsed()
        self.root.after(30, self._round_corners)
        self.root.after(120, self._drain)

        self.poller = Poller(prof["api"], prof["secret"], float(cfg["interval"]), self.q)
        self.poller.start()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Control-f>", lambda e: self.toggle_search())
        self.root.bind("<Escape>", lambda e: self._on_escape())

        if not cfg.get("first_run_done"):
            self.root.after(400, self.show_wizard)
        self.root.after(3000, self._watch_system_theme)

    # ------------------------------------------------------------ 基础
    def t(self, key, **kw):
        table = I18N.get(self.cfg.get("lang", "zh")) or I18N["zh"]
        txt = table.get(key, I18N["zh"].get(key, key))
        if kw:
            try:
                txt = txt.format(**kw)
            except Exception:
                pass
        return txt

    def S(self, v):
        return int(round(v * self.scale))

    def prof(self):
        return self.cfg["profiles"][self.cfg["active"]]

    def _resolved_theme(self) -> str:
        th = self.cfg.get("theme", "dark")
        if th == "auto":
            return "dark" if system_dark() else "light"
        return th if th in THEMES else "dark"

    def _palette(self) -> dict:
        pal = dict(THEMES[self.theme_name])
        acc = (self.cfg.get("accent") or "").strip()
        if re.match(r"^#[0-9a-fA-F]{6}$", acc):
            pal["accent"] = acc.lower()
        return pal

    def _fonts(self):
        fs = self.fs
        pt = lambda n: max(7, int(round(n * fs)))
        self.f_title = tkfont.Font(family="Microsoft YaHei UI", size=pt(self.st["title"]), weight="bold")
        self.f_ui = tkfont.Font(family="Microsoft YaHei UI", size=pt(9))
        self.f_small = tkfont.Font(family="Microsoft YaHei UI", size=pt(8))
        self.f_num = tkfont.Font(family="Cascadia Mono", size=pt(8))
        self.f_h2 = tkfont.Font(family="Microsoft YaHei UI", size=pt(11), weight="bold")
        self.f_chip = tkfont.Font(family="Microsoft YaHei UI", size=pt(8))

    def _metrics(self):
        fs = self.fs
        st = self.st
        base_w = self.S(round((500 if self.cfg["style"] == "dash" else 490)
                              * (1 + (fs - 1) * 0.75)))
        if isinstance(self.cfg.get("win_w"), (int, float)) and self.cfg["win_w"]:
            base_w = int(self.cfg["win_w"])
        self.W = max(self.S(340), base_w)
        self.HEAD_H = self.S(round(34 * (1 + (fs - 1) * 0.7)))
        self.HEADER_H = self.S(round(st["header_h"] * fs))
        self.SPARK_H = self.S(round(st["spark"] * fs)) if st["spark"] else 0
        self.ROW_H = self.S(round(st["row_h"] * fs))
        self.SEARCH_H = self.S(round(28 * fs))
        self.TABS_H = self.S(round(26 * fs))
        self.MINI_H = self.S(round(92 * fs))
        self.EXTRA_W = {"rule": self.S(round(88 * fs)),
                        "src": self.S(round(114 * fs)),
                        "net": self.S(round(46 * fs))}
        self.PAD_L = self.S(st["pad"])
        self.PAD_R = self.S(st["pad"])
        self.BAR = self.S(st["bar"])
        self.RADIUS = self.S(14)

        defaults = [self.S(round(110 * fs)), self.S(round(78 * fs)), self.S(round(72 * fs))]
        saved = self.cfg.get("col_w")
        if isinstance(saved, (list, tuple)) and len(saved) == 3:
            try:
                defaults = [int(v) for v in saved]
            except Exception:
                pass
        self.col_w = self._clamp_cols(defaults, self.W - 2)
        self.COL_NODE_W, self.COL_DOWN_W, self.COL_UP_W = self.col_w

        self.n_rows = 10 if self.cfg["rows"] == "all" else max(3, int(self.cfg["rows"]))

    def _clamp_cols(self, cols, avail):
        mn = self.S(36)
        host_min = self.S(96)
        n, d, u = [max(mn, int(v)) for v in cols]
        limit = max(mn * 3, avail - host_min)
        total = n + d + u
        if total > limit:
            k = limit / float(total)
            n, d, u = (max(mn, int(n * k)), max(mn, int(d * k)), max(mn, int(u * k)))
            while n + d + u > limit and min(n, d, u) > mn:
                if u > mn:
                    u -= 1
                elif d > mn:
                    d -= 1
                elif n > mn:
                    n -= 1
                else:
                    break
        return [n, d, u]

    def _avail_w(self):
        return max(self.S(220), self.W - 2)

    def _host_w(self):
        return max(self.S(60), self._avail_w() - sum(self.col_w))

    def _top_h(self):
        return self.HEAD_H + (self.SPARK_H if self.cfg["style"] == "dash" else 0) \
            + (self.SEARCH_H if self.search_open else 0) + self.TABS_H

    def _win_h(self):
        if self.cfg["collapsed"]:
            return self.HEAD_H
        if self.cfg.get("mini"):
            return self.HEAD_H + self.MINI_H
        top = self._top_h()
        if self.cfg["rows"] == "all":
            h = self.cfg.get("win_h")
            if not isinstance(h, (int, float)) or h < top + self.HEADER_H + self.ROW_H * 3:
                h = top + self.HEADER_H + self.ROW_H * 10 + self.S(2)
            return int(min(h, self.root.winfo_screenheight() * 0.92))
        return top + self.HEADER_H + self.n_rows * self.ROW_H + self.S(2)

    # ------------------------------------------------------------ 布局
    def _build(self):
        c, S = self.c, self.S
        self.outer = tk.Frame(self.root, bg=c["bg"], highlightthickness=1,
                              highlightbackground=c["border"])
        self.outer.pack(fill="both", expand=True)

        head = tk.Frame(self.outer, bg=c["bg"], height=self.HEAD_H)
        head.pack(fill="x")
        head.pack_propagate(False)
        self.head = head

        self.lbl_dot = tk.Label(head, text="●", bg=c["bg"], fg=c["wait"], font=self.f_small)
        self.lbl_dot.pack(side="left", padx=(S(10), S(1)))
        self.lbl_dot.bind("<Button-1>", lambda e: self._show_error())

        self.lbl_title = tk.Label(head, text=self.t("app"), bg=c["bg"], fg=c["title"],
                                  font=self.f_title)
        self.lbl_title.pack(side="left")

        self.btn_close = tk.Label(head, text="✕", bg=c["bg"], fg=c["sub"], font=self.f_ui,
                                  width=2, cursor="hand2")
        if not self.native:
            self.btn_close.pack(side="right", padx=(0, S(3)))
        self.btn_close.bind("<Button-1>", lambda e: self.on_close())
        self.btn_close.bind("<Enter>", lambda e: self.btn_close.configure(fg=c["err"]))
        self.btn_close.bind("<Leave>", lambda e: self.btn_close.configure(fg=c["sub"]))

        self.btn_set = tk.Label(head, text="⚙", bg=c["bg"], fg=c["sub"], font=self.f_ui,
                                width=2, cursor="hand2")
        self.btn_set.pack(side="right", padx=(0, S(2)))
        self.btn_set.bind("<Button-1>", lambda e: self.open_settings())
        self.btn_set.bind("<Enter>", lambda e: self.btn_set.configure(fg=c["title"]))
        self.btn_set.bind("<Leave>", lambda e: self.btn_set.configure(fg=c["sub"]))

        self.btn_min = tk.Label(head, text="—", bg=c["bg"], fg=c["sub"], font=self.f_ui,
                                width=2, cursor="hand2")
        if not self.native:
            self.btn_min.pack(side="right")
        self.btn_min.bind("<Button-1>", lambda e: self.toggle_collapse())
        self.btn_min.bind("<Enter>", lambda e: self.btn_min.configure(fg=c["title"]))
        self.btn_min.bind("<Leave>", lambda e: self.btn_min.configure(fg=c["sub"]))

        self.lbl_up = tk.Label(head, text="↑ 0/s", bg=c["bg"], fg=c["up"], font=self.f_num)
        self.lbl_up.pack(side="right", padx=(S(7), S(6)))
        self.lbl_down = tk.Label(head, text="↓ 0/s", bg=c["bg"], fg=c["down"], font=self.f_num)
        self.lbl_down.pack(side="right")

        self.lbl_count = tk.Label(head, text=self.t("starting"), bg=c["bg"], fg=c["sub"],
                                  font=self.f_small)
        self.lbl_count.pack(side="left", padx=(S(8), S(4)))

        self.lbl_ip = tk.Label(head, text=self._ip_text(), bg=c["chip_bg"], fg=c["chip_fg"],
                               font=self.f_chip, cursor="hand2", padx=S(7), pady=S(2))
        self.lbl_ip.pack(side="left", padx=(S(2), S(4)))
        self.lbl_ip.bind("<Button-1>", self._show_ip_menu)
        self.lbl_ip.bind("<Enter>", lambda e: self.lbl_ip.configure(bg=c["chip_hover"]))
        self.lbl_ip.bind("<Leave>", lambda e: self.lbl_ip.configure(bg=c["chip_bg"]))

        self.lbl_prof = tk.Label(head, text=self._prof_text(), bg=c["chip_bg"], fg=c["chip_fg"],
                                 font=self.f_chip, cursor="hand2", padx=S(7), pady=S(2))
        self.lbl_prof.pack(side="left", padx=(0, S(4)))
        self.lbl_prof.bind("<Button-1>", self._show_profile_menu)
        self.lbl_prof.bind("<Enter>", lambda e: self.lbl_prof.configure(bg=c["chip_hover"]))
        self.lbl_prof.bind("<Leave>", lambda e: self.lbl_prof.configure(bg=c["chip_bg"]))

        # 曲线（仪表盘风格）
        self.spark = None
        if self.cfg["style"] == "dash":
            self.spark = tk.Canvas(self.outer, height=self.SPARK_H, bg=c["head_bg"],
                                   highlightthickness=0, bd=0)
            self.spark.pack(fill="x")
            self.spark.bind("<Button-1>", lambda e: self.cycle_curve())

        # 视图切换
        self.tabs = tk.Frame(self.outer, bg=c["bg"], height=self.TABS_H)
        self._build_tabs()

        # 迷你模式
        self.mini_frame = tk.Frame(self.outer, bg=c["bg"])
        self.mini_box = tk.Frame(self.mini_frame, bg=c["bg"])
        self.mini_box.pack(fill="both", expand=True, padx=self.PAD_L, pady=self.S(8))
        self.mini_down = tk.Label(self.mini_box, text="↓ 0 B/s", bg=c["bg"], fg=c["down"],
                                  font=self.f_h2, anchor="w")
        self.mini_down.pack(anchor="w")
        self.mini_up = tk.Label(self.mini_box, text="↑ 0 B/s", bg=c["bg"], fg=c["up"],
                                font=self.f_ui, anchor="w")
        self.mini_up.pack(anchor="w")
        self.mini_info = tk.Label(self.mini_box, text="", bg=c["bg"], fg=c["sub"],
                                  font=self.f_small, anchor="w")
        self.mini_info.pack(anchor="w", pady=(self.S(2), 0))

        # 搜索栏
        self.search_bar = tk.Frame(self.outer, bg=c["bg"], height=self.SEARCH_H)
        self.search_var = tk.StringVar(master=self.root, value="")
        self.search_entry = tk.Entry(self.search_bar, textvariable=self.search_var,
                                     font=self.f_ui, bg=c["input_bg"], fg=c["title"],
                                     insertbackground=c["title"], relief="flat",
                                     highlightthickness=1, highlightbackground=c["border"],
                                     highlightcolor=c["accent"])
        self.search_entry.pack(fill="x", padx=self.PAD_L, pady=self.S(4))
        self.search_var.trace_add("write", lambda *a: self._on_search())
        self.search_entry.bind("<Escape>", lambda e: self.toggle_search(False))

        # 表格
        self.table = tk.Canvas(self.outer, bg=c["bg"], highlightthickness=0, bd=0)
        self.table.pack(fill="both", expand=True)
        self.table.bind("<Configure>", lambda e: self._redraw())
        self.table.bind("<Motion>", self._on_motion)
        self.table.bind("<Leave>", self._on_leave)
        self.table.bind("<Button-1>", self._on_press)
        self.table.bind("<B1-Motion>", self._on_drag)
        self.table.bind("<ButtonRelease-1>", self._on_release)
        self.table.bind("<Double-Button-1>", self._on_double)
        self.table.bind("<Button-3>", self._on_menu)
        self.table.bind("<MouseWheel>", self._on_wheel)

        for w in (head, self.lbl_dot, self.lbl_title, self.lbl_count, self.lbl_down,
                  self.lbl_up, self.outer):
            w.bind("<Button-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)
            w.bind("<ButtonRelease-1>", self._drag_end)
            w.bind("<Button-3>", self._on_menu)
        self.lbl_title.bind("<Double-Button-1>", lambda e: self.toggle_collapse())
        self.root.bind("<Button-3>", self._on_menu)

        self._create_grips()
        if getattr(self, "native", False):
            self.root.bind("<Configure>", self._on_configure)
        self._menu = None
        self.root.after(30, self._layout_header)

    # ------------------------------------------------------------ 视图 / 迷你
    def _build_tabs(self):
        c = self.c
        for w in self.tabs.winfo_children():
            w.destroy()
        self.tab_labels = {}
        box = tk.Frame(self.tabs, bg=c["bg"])
        box.pack(side="left", padx=self.S(6))
        for key in ("conn", "node", "device"):
            sel = self.cfg["view"] == key
            lb = tk.Label(box, text=self.t("tab_" + key), font=self.f_small,
                          cursor="hand2", padx=self.S(9), pady=self.S(2),
                          bg=c["chip_on_bg"] if sel else c["chip_bg"],
                          fg=c["chip_on_fg"] if sel else c["chip_fg"])
            lb.pack(side="left", padx=(0, self.S(4)))
            lb.bind("<Button-1>", lambda e, k=key: self.set_view(k))
            self.tab_labels[key] = lb

        btn = tk.Label(self.tabs, text=self.t("search_btn"), font=self.f_ui,
                       bg=c["chip_on_bg"] if self.search_open else c["chip_bg"],
                       fg=c["chip_on_fg"] if self.search_open else c["chip_fg"],
                       cursor="hand2", padx=self.S(10), pady=self.S(1))
        btn.pack(side="right", padx=(0, self.S(8)), pady=self.S(2))
        btn.bind("<Button-1>", lambda e: self.toggle_search())
        btn.bind("<Enter>", lambda e: btn.configure(bg=c["chip_hover"]))
        btn.bind("<Leave>", lambda e: btn.configure(
            bg=c["chip_on_bg"] if self.search_open else c["chip_bg"]))
        self.btn_search = btn

    def set_view(self, key):
        if key not in ("conn", "node", "device"):
            return
        self.cfg["view"] = key
        self.scroll = 0
        self._build_tabs()
        self._persist()
        self._update_counts()
        self._redraw()

    def toggle_mini(self):
        self.cfg["mini"] = not self.cfg.get("mini")
        self._apply_collapsed()
        self._persist()

    def cycle_curve(self):
        order = ["60", "300", "1800"]
        cur = self.cfg.get("curve", "60")
        i = order.index(cur) if cur in order else 0
        self.cfg["curve"] = order[(i + 1) % 3]
        self._persist()
        self._draw_spark()

    def set_col_visible(self, key, flag):
        self.cfg["show_cols"][key] = bool(flag)
        self._persist()
        self._redraw()
        self._refresh_settings()

    def _update_mini(self):
        if not self.cfg.get("mini"):
            return
        d = self.data or {}
        self.rows_visible = self._visible_rows()
        self.mini_down.configure(text="↓ " + fmt_bytes(d.get("down", 0)))
        self.mini_up.configure(text="↑ " + fmt_bytes(d.get("up", 0)))
        info = self.t("mini_hint", n=len(self.rows_visible), a=d.get("active", 0))
        if self.rows_visible:
            info += "  ·  " + fit_text(self.rows_visible[0]["host"], self.f_small,
                                       self.W - self.S(40))
        self.mini_info.configure(text=info)

    def _autofit_col(self, which):
        rows = self.rows_visible[:80]
        if which == 0:
            texts = [(self.t("direct") if r["direct"] else r["node"]) for r in rows]
            f = self.f_small
        else:
            texts = [fmt_short(r["down"] if which == 1 else r["up"]) for r in rows]
            f = self.f_num
        need = max([f.measure(x) for x in texts] + [self.S(40)])
        w = max(self.S(44), min(self.S(320), need + self.S(20)))
        cols = list(self.col_w)
        cols[which] = w
        self.col_w = self._clamp_cols(cols, self._avail_w())
        self.COL_NODE_W, self.COL_DOWN_W, self.COL_UP_W = self.col_w
        self.cfg["col_w"] = list(self.col_w)
        self._persist()
        self._redraw()

    # ------------------------------------------------------------ 行菜单
    def _row_menu(self, e, row):
        m = tk.Menu(self.root, **self._menu_colors())
        m.add_command(label=self.t("copy"), command=lambda: self._to_clipboard(row["host"]))
        m.add_command(label=self.t("copy_row"), command=lambda: self._to_clipboard(
            "\t".join([row["host"], row["node"] or self.t("direct"),
                       fmt_short(row["down"]), fmt_short(row["up"]),
                       row["src"], row.get("rule", ""), row.get("net", "")])))
        m.add_separator()
        if row.get("src"):
            m.add_command(label=self.t("only_ip"),
                          command=lambda: (self.set_filter(row["src"]),
                                           self.toggle_search(False)))
        if row.get("node"):
            m.add_command(label=self.t("only_node"),
                          command=lambda: (self.toggle_search(True),
                                           self.search_var.set(row["node"])))
        self._row_menu_ref = m
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def _create_grips(self):
        self._grips = []
        if getattr(self, "native", False):
            return
        for side in ("left", "right"):
            g = tk.Frame(self.root, bg=self.c["bg"], cursor="sb_h_double_arrow")
            g.bind("<Button-1>", lambda e, s=side: self._start_resize(e, s))
            g.bind("<B1-Motion>", self._resize_win)
            g.bind("<ButtonRelease-1>", self._end_resize)
            g.bind("<Enter>", lambda e, w=g: w.configure(bg=self.c["chip_hover"]))
            g.bind("<Leave>", lambda e, w=g: w.configure(bg=self.c["bg"]))
            self._grips.append((side, g))
        gb = tk.Frame(self.root, bg=self.c["bg"], cursor="sb_v_double_arrow")
        gb.bind("<Button-1>", self._start_hresize)
        gb.bind("<B1-Motion>", self._resize_h)
        gb.bind("<ButtonRelease-1>", self._end_hresize)
        gb.bind("<Enter>", lambda e, w=gb: w.configure(bg=self.c["chip_hover"]))
        gb.bind("<Leave>", lambda e, w=gb: w.configure(bg=self.c["bg"]))
        self._grips.append(("bottom", gb))
        self._place_grips()

    def _place_grips(self):
        if not getattr(self, "_grips", None):
            return
        h = self._win_h()
        gw = self.S(4)
        for side, g in self._grips:
            if side == "bottom":
                if self.cfg["collapsed"] or self.cfg.get("mini"):
                    g.place_forget()
                else:
                    g.place(x=self.S(8), y=max(1, h - gw - 1),
                            width=max(10, self.W - self.S(16)), height=gw)
                    g.lift()
                continue
            x = 1 if side == "left" else max(1, self.W - gw - 1)
            g.place(x=x, y=1, width=gw, height=max(4, h - 2))
            g.lift()

    def _start_hresize(self, e):
        if self.cfg["rows"] != "all":
            self.cfg["rows"] = "all"
            self.cfg["win_h"] = int(self.root.winfo_height())
            self._refresh_settings()
        self._hresz = {"y": e.y_root, "h": self.root.winfo_height()}
        return "break"

    def _resize_h(self, e):
        d = getattr(self, "_hresz", None)
        if not d:
            return "break"
        top = self._top_h()
        min_h = top + self.HEADER_H + self.ROW_H * 3
        max_h = int(self.root.winfo_screenheight() * 0.92)
        h = max(min_h, min(d["h"] + (e.y_root - d["y"]), max_h))
        self.cfg["win_h"] = int(h)
        self.root.geometry(f"{self.W}x{h}+{self.root.winfo_x()}+{self.root.winfo_y()}")
        self._place_grips()
        self._redraw()
        return "break"

    def _end_hresize(self, e):
        if getattr(self, "_hresz", None):
            self._hresz = None
            self._persist()
            self._refresh_settings()
        return "break"

    def _place_window(self):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x = self.cfg.get("x")
        y = self.cfg.get("y")
        if x is None:
            x = sw - self.W - self.S(30)
        if y is None:
            y = self.S(90)
        x = max(-self.W + self.S(90), min(int(x), sw - self.S(60)))
        y = max(self.S(4), min(int(y), sh - self.HEAD_H - self.S(40)))
        self.root.geometry(f"{self.W}x{self._win_h()}+{x}+{y}")

    def _apply_geometry(self):
        self.root.geometry(f"{self.W}x{self._win_h()}")
        self._place_grips()
        self._layout_header()
        self.root.after(20, self._round_corners)

    def _layout_header(self):
        """窗口较窄时依次隐藏：计数 → 配置档；IP 胶囊有筛选时永不隐藏。"""
        try:
            avail = self.head.winfo_width() - 4
        except Exception:
            return
        if avail <= 1:
            return
        for w in (self.lbl_count, self.lbl_ip, self.lbl_prof):
            w.pack(side="left")
        need = lambda: sum(w.winfo_reqwidth() for w in
                           (self.lbl_dot, self.lbl_title, self.lbl_count, self.lbl_ip,
                            self.lbl_prof, self.lbl_down, self.lbl_up, self.btn_min,
                            self.btn_set, self.btn_close))
        filtering = bool(self.cfg.get("filter_ip"))
        order = ([self.lbl_prof, self.lbl_count] if filtering
                 else [self.lbl_count, self.lbl_prof, self.lbl_ip])
        for w in order:
            if need() + self.S(40) <= avail:
                break
            w.pack_forget()
        if filtering and need() + self.S(20) > avail:
            self.lbl_title.pack_forget()
        else:
            self.lbl_title.pack(side="left")

    # ------------------------------------------------------------ 绘制
    def _extra_keys(self):
        if self.cfg.get("view", "conn") != "conn":
            return []
        sc = self.cfg.get("show_cols") or {}
        return [k for k in ("rule", "src", "net") if sc.get(k)]

    def _extra_w(self):
        return sum(self.EXTRA_W[k] for k in self._extra_keys())

    def _cols(self):
        w = self.table.winfo_width() or self.W
        host = max(self.S(50), w - self.PAD_L - self.PAD_R - sum(self.col_w)
                   - self._extra_w())
        x_node = self.PAD_L + host
        x_down = x_node + self.COL_NODE_W
        x_up = x_down + self.COL_DOWN_W
        return host, x_node, x_down, x_up

    def _visible_rows(self):
        rows = self.rows
        ip = self.cfg.get("filter_ip") or ""
        q = (self.search_var.get() if self.search_open else "").strip().lower()
        if ip:
            rows = [r for r in rows if r["src"] == ip]
        if q:
            rows = [r for r in rows if q in r["host"].lower() or q in r["node"].lower()]
        view = self.cfg.get("view", "conn")
        if view in ("node", "device"):
            agg = {}
            for r in rows:
                key = ((r["node"] or self.t("direct")) if view == "node"
                       else (r["src"] or "—"))
                a = agg.get(key)
                if a is None:
                    a = agg[key] = {
                        "id": key, "host": key, "node": "", "direct": True,
                        "agg": True, "count": 0, "up": 0.0, "down": 0.0,
                        "up_total": 0.0, "down_total": 0.0, "src": r["src"],
                        "rule": "", "net": "", "sport": "", "chain": "",
                        "start": "", "hot": 0.0,
                    }
                a["count"] += 1
                a["up"] += r["up"]
                a["down"] += r["down"]
                a["up_total"] += r["up_total"]
                a["down_total"] += r["down_total"]
                a["hot"] = max(a["hot"], r["hot"])
            rows = list(agg.values())
            if q:
                rows = [r for r in rows if q in r["host"].lower()]
            if self.cfg.get("sort") == "host":
                rows.sort(key=lambda r: r["host"].lower(),
                          reverse=self.cfg.get("sort_desc", True))
            else:
                rows.sort(key=lambda r: (-(r["down"] + r["up"]), -r["hot"]))
            return rows
        mode = self.cfg.get("sort", "speed")
        desc = self.cfg.get("sort_desc", True)
        if mode == "host":
            rows = sorted(rows, key=lambda r: r["host"].lower(), reverse=desc)
        elif mode == "node":
            rows = sorted(rows, key=lambda r: (r["node"] or " ").lower(), reverse=desc)
        elif mode == "time":
            rows = sorted(rows, key=lambda r: r["start"], reverse=desc)
        return rows

    def _redraw(self):
        if self.cfg["collapsed"]:
            return
        cv = self.table
        try:
            w, h = cv.winfo_width(), cv.winfo_height()
        except Exception:
            return
        if w <= 4 or h <= 4:
            return
        cv.delete("all")
        self.rows_visible = self._visible_rows()
        self._draw_header(w)
        body_top = self.HEADER_H
        vis = max(0, (h - body_top) // self.ROW_H)
        max_scroll = max(0, len(self.rows_visible) - vis)
        if self.scroll > max_scroll:
            self.scroll = max_scroll
        c = self.c
        host_w, x_node, x_down, x_up = self._cols()
        max_rate = max([r["down"] + r["up"] for r in self.rows_visible] or [1.0]) or 1.0

        if not self.rows_visible:
            if self.error:
                kind = self.error.get("kind", "other")
                detail = self.error.get("detail", "")
                txt = self.t(f"diag_{kind}", msg=detail, code=detail)
                txt = txt + "\n" + self.t("retry_hint")
            else:
                key = "no_ip" if self.cfg.get("filter_ip") else (
                    "no_match" if (self.search_open and self.search_var.get().strip())
                    else "empty")
                if not self.data:
                    key = "starting"
                txt = self.t(key)
            cv.create_text(w // 2, body_top + (h - body_top) // 2, text=txt,
                           fill=c["sub"], font=self.f_ui, justify="center")
        else:
            for i in range(vis):
                idx = self.scroll + i
                if idx >= len(self.rows_visible):
                    break
                self._draw_row(self.rows_visible[idx], idx,
                               body_top + i * self.ROW_H, w, host_w, x_node, x_down,
                               x_up, max_rate)
        self._draw_scrollbar(w, h, vis, len(self.rows_visible))
        if self.data:
            self._draw_spark()

    def _draw_header(self, w):
        c = self.c
        cv = self.table
        cv.create_rectangle(0, 0, w, self.HEADER_H, fill=c["head_bg"] if
                            self.cfg["style"] == "dash" else c["bg"], outline="")
        cv.create_rectangle(0, 0, w, max(1, self.S(1)), fill=c["accent"], outline="")
        host_w, x_node, x_down, x_up = self._cols()
        y = self.HEADER_H // 2
        fs = self.f_chip
        view = self.cfg.get("view", "conn")
        if view == "conn":
            h0, h1 = self.t("col_host"), self.t("col_node")
        elif view == "node":
            h0, h1 = self.t("tab_node"), self.t("tab_conn")
        else:
            h0, h1 = self.t("tab_device"), self.t("tab_conn")
        cv.create_text(self.PAD_L, y, text=h0, fill=c["colhdr"], font=fs, anchor="w")
        cv.create_text(x_node, y, text=h1, fill=c["colhdr"], font=fs, anchor="w")
        cv.create_text(x_down + self.COL_DOWN_W - self.S(4), y,
                       text=self.t("col_down"), fill=c["colhdr"], font=fs, anchor="e")
        cv.create_text(x_up + self.COL_UP_W - self.S(4), y,
                       text=self.t("col_up"), fill=c["colhdr"], font=fs, anchor="e")
        # 附加列
        x = x_up + self.COL_UP_W
        for k in self._extra_keys():
            cv.create_text(x + self.S(6), y, text=self.t("c_" + k), fill=c["colhdr"],
                           font=fs, anchor="w")
            x += self.EXTRA_W[k]
            cv.create_line(x, self.S(4), x, self.HEADER_H - self.S(4), fill=c["border"])
        # 排序列提示
        arrow = "▼" if self.cfg.get("sort_desc", True) else "▲"
        pos = {"host": (self.PAD_L, "w"), "node": (x_node, "w")}.get(
            self.cfg.get("sort", "speed"))
        if pos:
            cv.create_text(pos[0] + self.S(34), y, text=arrow, fill=c["accent"],
                           font=self.f_small, anchor="w")
        for xx in (x_node, x_down, x_up):
            cv.create_line(xx, self.S(4), xx, self.HEADER_H - self.S(4),
                           fill=c["border"])
        cv.create_line(0, self.HEADER_H - 1, w, self.HEADER_H - 1, fill=c["border"])

    def _draw_row(self, r, idx, y, w, host_w, x_node, x_down, x_up, max_rate):
        c, cv = self.c, self.table
        row_h = self.ROW_H
        base = c["row_alt"] if idx % 2 else c["row"]
        if self.hover == idx:
            base = c["hover"]
        cv.create_rectangle(0, y, w, y + row_h, fill=base, outline="")
        idle = (r["down"] + r["up"]) < ACTIVE_MIN_BPS
        if not idle:
            cv.create_rectangle(0, y, self.BAR, y + row_h, fill=c["accent"], outline="")
        # 下行占比条
        rate = r["down"] + r["up"]
        if rate > 0:
            bw = int(self.COL_DOWN_W * min(1.0, rate / max_rate))
            if bw > 2:
                cv.create_rectangle(x_down, y + row_h - self.BAR, x_down + bw,
                                    y + row_h, fill=blend(base, c["down"], 0.45),
                                    outline="")
        host_fg = c["host_idle"] if idle else c["host"]
        cv.create_text(self.PAD_L, y + row_h // 2,
                       text=fit_text(r["host"], self.f_ui, host_w - self.S(10)),
                       fill=host_fg, font=self.f_ui, anchor="w")
        if r.get("agg"):
            cv.create_text(x_node, y + row_h // 2,
                           text=f'{r["count"]} ×', fill=c["direct"],
                           font=self.f_small, anchor="w")
        else:
            # 节点 + 色点
            node_txt = self.t("direct") if r["direct"] else r["node"]
            dot = c["zero"] if r["direct"] else c["dots"][abs(hash(r["node"] or "d")) % len(c["dots"])]
            cv.create_oval(x_node - self.S(9), y + row_h // 2 - self.S(2),
                           x_node - self.S(5), y + row_h // 2 + self.S(2),
                           fill=dot, outline="")
            cv.create_text(x_node, y + row_h // 2,
                           text=fit_text(node_txt, self.f_small,
                                         self.COL_NODE_W - self.S(10)),
                           fill=(c["node_idle"] if idle else c["node"]) if not r["direct"]
                           else c["direct"], font=self.f_small, anchor="w")
        d, u = r["down"], r["up"]
        cv.create_text(x_down + self.COL_DOWN_W - self.S(4), y + row_h // 2,
                       text=fmt_short(d) if d >= 1 else ("—" if idle else ""),
                       fill=c["down"] if d >= 1 else c["zero"], font=self.f_num, anchor="e")
        cv.create_text(x_up + self.COL_UP_W - self.S(4), y + row_h // 2,
                       text=fmt_short(u) if u >= 1 else ("—" if idle else ""),
                       fill=c["up"] if u >= 1 else c["zero"], font=self.f_num, anchor="e")
        # 附加列
        if not r.get("agg"):
            x = x_up + self.COL_UP_W
            for k in self._extra_keys():
                val = {"rule": r.get("rule", ""), "src": r.get("src", ""),
                       "net": r.get("net", "")}.get(k, "")
                if k == "src" and r.get("sport"):
                    val = f'{val}:{r["sport"]}'
                cv.create_text(x + self.S(6), y + row_h // 2,
                               text=fit_text(str(val), self.f_small,
                                             self.EXTRA_W[k] - self.S(10)),
                               fill=c["sub"], font=self.f_small, anchor="w")
                x += self.EXTRA_W[k]

    def _draw_scrollbar(self, w, h, vis, n):
        if self.cfg["rows"] != "all" or n <= vis:
            return
        c = self.c
        if not (self.sb_hover or self.sb_drag):
            return
        track_x = w - self.S(6)
        top = self.HEADER_H + self.S(2)
        bottom = h - self.S(2)
        self.table.create_rectangle(track_x, top, track_x + self.S(4), bottom,
                                    fill=c["bar_track"], outline="")
        span = max(1, bottom - top)
        th = max(self.S(24), int(span * vis / float(n)))
        pos = int(span * self.scroll / float(max(1, n - vis)))
        self.table.create_rectangle(track_x, top + pos, track_x + self.S(4),
                                    top + pos + th, fill=c["chip_fg"], outline="")

    def _draw_spark(self):
        cv = self.spark
        if not cv:
            return
        cv.delete("all")
        c = self.c
        w = cv.winfo_width()
        h = self.SPARK_H
        if w <= 4 or h <= 8:
            return
        cv.create_rectangle(0, 0, w, h, fill=c["head_bg"], outline="")
        key = self.cfg.get("curve", "60")
        hist = ((self.data or {}).get("hist") or {})
        series = hist.get(key) or [] if isinstance(hist, dict) else []
        label = {"60": "60s", "300": "5m", "1800": "30m"}.get(key, "60s")
        cv.create_text(w - self.S(6), self.S(7), text=label + " ▾", anchor="e",
                       fill=c["colhdr"], font=self.f_small)
        if len(series) < 2:
            return
        down = [x[2] for x in series]
        up = [x[1] for x in series]
        top = max(max(down), max(up)) or 1.0
        n = len(series)
        pad = self.S(4)
        pts_d, pts_u = [], []
        for i in range(n):
            x = pad + (w - 2 * pad) * i / float(n - 1)
            pts_d.append((x, h - pad - (h - 2 * pad) * (down[i] / top)))
            pts_u.append((x, h - pad - (h - 2 * pad) * (up[i] / top)))
        poly = [(pad, h - pad)] + pts_d + [(w - pad, h - pad)]
        cv.create_polygon([v for p in poly for v in p],
                          fill=blend(c["head_bg"], c["down"], 0.22), outline="")
        lw = max(1, self.S(1.3))
        cv.create_line([v for p in pts_d for v in p], fill=c["down"], width=lw)
        cv.create_line([v for p in pts_u for v in p], fill=c["up"], width=lw)

    def _refresh_view(self):
        if self.cfg["collapsed"]:
            return
        self._redraw()

    # ------------------------------------------------------------ 交互
    def _row_at(self, y):
        if y < self.HEADER_H:
            return -1
        idx = (y - self.HEADER_H) // self.ROW_H + self.scroll
        return idx if 0 <= idx < len(self.rows_visible) else -1

    def _on_motion(self, e):
        idx = self._row_at(e.y)
        w = self.table.winfo_width()
        on_sb = (self.cfg["rows"] == "all" and e.x >= w - self.S(8))
        changed = False
        if on_sb != self.sb_hover:
            self.sb_hover = on_sb
            changed = True
        if idx != self.hover:
            self.hover = idx
            changed = True
        # 列边界光标
        if e.y < self.HEADER_H:
            if self._col_boundary(e.x) is not None:
                self.table.configure(cursor="sb_h_double_arrow")
            else:
                self.table.configure(cursor="")
        else:
            self.table.configure(cursor="")
        if changed:
            self._redraw()

    def _on_leave(self, e):
        if self.hover != -1 or self.sb_hover:
            self.hover = -1
            self.sb_hover = False
            self._redraw()

    def _col_boundary(self, x):
        host_w, x_node, x_down, x_up = self._cols()
        for b in (x_node, x_down, x_up):
            if abs(x - b) <= self.S(5):
                return b
        return None

    def _on_press(self, e):
        w = self.table.winfo_width()
        if self.cfg["rows"] == "all" and e.x >= w - self.S(8) and e.y > self.HEADER_H:
            self.sb_drag = e.y
            self._scroll_to_y(e.y, dragging=True)
            return
        if e.y < self.HEADER_H:
            b = self._col_boundary(e.x)
            if b is not None:
                self._cdrag = {"x": e.x_root, "w": list(self.col_w),
                               "which": (self._cols()[1:].index(b))}
                return
            # 表头点击排序
            host_w, x_node, x_down, x_up = self._cols()
            key = None
            if e.x < x_node:
                key = "host"
            elif e.x < x_down:
                key = "node"
            elif e.x < x_up:
                key = "speed"
            if key:
                self._set_sort(key)
            return
        self.press = {"x": e.x_root, "y": e.y_root, "wx": self.root.winfo_x(),
                      "wy": self.root.winfo_y(), "row": self._row_at(e.y),
                      "moved": False, "x0": e.x, "y0": e.y}

    def _on_drag(self, e):
        if self.sb_drag is not None:
            self._scroll_to_y(e.y, dragging=True)
            return
        if self._cdrag:
            self._drag_col(e)
            return
        p = self.press
        if not p:
            return
        dx, dy = e.x_root - p["x"], e.y_root - p["y"]
        if abs(dx) > 3 or abs(dy) > 3:
            p["moved"] = True
        self.root.geometry(f"+{p['wx'] + dx}+{p['wy'] + dy}")

    def _on_release(self, e):
        if self.sb_drag is not None:
            self.sb_drag = None
            self._redraw()
            return
        if self._cdrag:
            self._end_col_drag()
            return
        p = self.press
        self.press = None
        if p and not p["moved"]:
            idx = self._row_at(e.y)
            if idx >= 0:
                self._show_details(self.rows_visible[idx])
        elif p and p["moved"]:
            self._persist()

    def _on_double(self, e):
        if e.y < self.HEADER_H:
            b = self._col_boundary(e.x)
            if b is not None:
                which = (self._cols()[1:]).index(b)
                self._autofit_col(which)
            return
        idx = self._row_at(e.y)
        if idx >= 0:
            self._to_clipboard(self.rows_visible[idx]["host"])

    def _on_wheel(self, e):
        if self.cfg["rows"] != "all":
            return
        vis = max(1, (self.table.winfo_height() - self.HEADER_H) // self.ROW_H)
        max_scroll = max(0, len(self.rows_visible) - vis)
        self.scroll = max(0, min(max_scroll, self.scroll - (e.delta // 120) * 3))
        self._redraw()

    def _scroll_to_y(self, y, dragging=False):
        h = self.table.winfo_height()
        top, bottom = self.HEADER_H, h - self.S(2)
        span = max(1, bottom - top)
        vis = max(1, (h - self.HEADER_H) // self.ROW_H)
        n = len(self.rows_visible)
        frac = (y - top) / float(span)
        self.scroll = max(0, min(max(0, n - vis), int(frac * max(0, n - vis) + 0.5)))
        self._redraw()

    def _set_sort(self, key):
        if self.cfg.get("sort") == key:
            self.cfg["sort_desc"] = not self.cfg.get("sort_desc", True)
        else:
            self.cfg["sort"] = key
            self.cfg["sort_desc"] = key not in ("host", "node")
        self.scroll = 0
        self._persist()
        self._redraw()

    # ------------------------------------------------------------ 列宽拖动
    def _drag_col(self, e):
        d = self._cdrag
        dx = e.x_root - d["x"]
        n, dn, u = d["w"]
        avail = self._avail_w()
        mn, host_min = self.S(36), self.S(96)
        which = d["which"]
        if which == 0:
            n = max(mn, min(n + dx, avail - host_min - dn - u))
        elif which == 1:
            dx = max(mn - n, min(dx, dn - mn))
            n, dn = n + dx, dn - dx
        else:
            dx = max(mn - dn, min(dx, u - mn))
            dn, u = dn + dx, u - dx
        self.col_w = [n, dn, u]
        self.COL_NODE_W, self.COL_DOWN_W, self.COL_UP_W = self.col_w
        self._redraw()

    def _end_col_drag(self):
        if not self._cdrag:
            return
        self._cdrag = None
        self.cfg["col_w"] = [int(v) for v in self.col_w]
        self._persist()
        self._refresh_settings()

    # ------------------------------------------------------------ 宽度
    def _start_resize(self, e, side):
        self._rsz = {"side": side, "x": e.x_root, "w": self.W,
                     "wx": self.root.winfo_x()}
        return "break"

    def _resize_win(self, e):
        d = self._rsz
        if not d:
            return "break"
        dx = e.x_root - d["x"]
        min_w = max(self.S(340), self.S(96) + sum(self.col_w) + self.S(24))
        max_w = int(self.root.winfo_screenwidth() * 0.92)
        if d["side"] == "right":
            w, x = max(min_w, min(d["w"] + dx, max_w)), d["wx"]
        else:
            w = max(min_w, min(d["w"] - dx, max_w))
            x = d["wx"] + (d["w"] - w)
        self._apply_width(w, x)
        return "break"

    def _end_resize(self, e):
        if self._rsz:
            self._rsz = None
            self.cfg["win_w"] = int(self.W)
            self._persist()
            self._refresh_settings()
        return "break"

    def _apply_width(self, w, x=None):
        self.W = max(self.S(340), int(w))
        rx = self.root.winfo_x() if x is None else int(x)
        self.root.geometry(f"{self.W}x{self._win_h()}+{rx}+{self.root.winfo_y()}")
        self.col_w = self._clamp_cols(self.col_w, self._avail_w())
        self.COL_NODE_W, self.COL_DOWN_W, self.COL_UP_W = self.col_w
        self._place_grips()
        self._redraw()
        self._round_corners()

    # ------------------------------------------------------------ 窗口拖动
    def _drag_start(self, e):
        if getattr(e, "widget", None) in (self.btn_close, self.btn_set, self.btn_min,
                                          self.btn_search, self.lbl_ip, self.lbl_prof):
            return
        self.press = {"x": e.x_root, "y": e.y_root, "wx": self.root.winfo_x(),
                      "wy": self.root.winfo_y(), "row": -1, "moved": False}

    def _drag_move(self, e):
        p = self.press
        if not p:
            return
        dx, dy = e.x_root - p["x"], e.y_root - p["y"]
        if abs(dx) > 3 or abs(dy) > 3:
            p["moved"] = True
        self.root.geometry(f"+{p['wx'] + dx}+{p['wy'] + dy}")

    def _drag_end(self, e):
        if self.press and self.press.get("moved"):
            self._persist()
        self.press = None

    # ------------------------------------------------------------ 菜单
    def _menu_colors(self):
        c = self.c
        return dict(tearoff=0, bg=c["menu_bg"], fg=c["menu_fg"],
                    activebackground=c["menu_sel"], activeforeground=c["menu_fg"],
                    bd=0, font=self.f_ui)

    def _on_menu(self, e):
        c = self.c
        if getattr(e, "widget", None) is self.table and e.y >= self.HEADER_H:
            idx = self._row_at(e.y)
            if 0 <= idx < len(self.rows_visible):
                self._row_menu(e, self.rows_visible[idx])
                return
        m = tk.Menu(self.root, **self._menu_colors())
        m.add_command(label=self.t("menu_open"), command=self.open_panel)
        m.add_command(label=self.t("menu_copy"), command=self.copy_hosts)
        m.add_command(label=self.t("copy_tsv"), command=self.copy_rows_tsv)
        m.add_command(label=self.t("menu_search"), command=self.toggle_search)
        m.add_separator()
        m.add_command(label=self.t("menu_top") + (" ✓" if self.cfg["topmost"] else ""),
                      command=self.toggle_topmost)
        m.add_command(label=self.t("menu_collapse"), command=self.toggle_collapse)
        m.add_command(label=self.t("mini") + (" ✓" if self.cfg.get("mini") else ""),
                      command=self.toggle_mini)
        m.add_command(label=self.t("menu_colw"), command=self.reset_cols)
        m.add_command(label=self.t("menu_winw"), command=self.reset_width)
        sub = tk.Menu(m, **self._menu_colors())
        for v in (0.5, 1.0, 2.0):
            sub.add_command(label=self.t("sec", v=v),
                            command=lambda v=v: self.set_interval(v))
        m.add_cascade(label=self.t("menu_interval"), menu=sub)
        m.add_separator()
        m.add_command(label=self.t("menu_settings"), command=self.open_settings)
        m.add_command(label=self.t("menu_quit"), command=self.quit_app)
        self._row_menu = m
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def _ip_text(self):
        ip = self.cfg.get("filter_ip") or ""
        return f"{ip} ▾" if ip else f'{self.t("all_ip")} ▾'

    def _prof_text(self):
        name = self.prof()["name"] or "?"
        return fit_text(name, self.f_chip, self.S(96)) + " ▾"

    def _show_ip_menu(self, e):
        m = tk.Menu(self.root, **self._menu_colors())
        cur = self.cfg.get("filter_ip") or ""
        total = (self.data or {}).get("count", 0)
        m.add_command(label=("✓ " if not cur else "   ") + f'{self.t("all_ip")} ({total})',
                      command=lambda: self.set_filter(""))
        ips = (self.data or {}).get("ips") or []
        if ips:
            m.add_separator()
        for ip, n in ips:
            m.add_command(label=("✓ " if ip == cur else "   ") + f"{ip}  ({n})",
                          command=lambda i=ip: self.set_filter(i))
        self._row_menu = m
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def _show_profile_menu(self, e):
        m = tk.Menu(self.root, **self._menu_colors())
        for i, p in enumerate(self.cfg["profiles"]):
            mark = "✓ " if i == self.cfg["active"] else "   "
            m.add_command(label=f'{mark}{p["name"]}',
                          command=lambda i=i: self.set_profile(i))
        m.add_separator()
        m.add_command(label=self.t("menu_settings"), command=self.open_settings)
        self._row_menu = m
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    # ------------------------------------------------------------ 动作
    def set_filter(self, ip):
        self.cfg["filter_ip"] = ip or ""
        self.lbl_ip.configure(text=self._ip_text())
        self.scroll = 0
        self._layout_header()
        self._persist()
        self._update_counts()
        self._redraw()

    def set_profile(self, idx):
        if 0 <= idx < len(self.cfg["profiles"]):
            self.cfg["active"] = idx
            p = self.prof()
            self.poller.set_endpoint(p["api"], p["secret"])
            self.data = None
            self.rows = []
            self.scroll = 0
            self.lbl_prof.configure(text=self._prof_text())
            self._layout_header()
            self._persist()
            self._redraw()

    def set_interval(self, v):
        self.cfg["interval"] = float(v)
        self.poller.set_interval(v)
        self._persist()
        self._refresh_settings()

    def set_rows(self, v):
        cur_h = self.root.winfo_height()
        self.cfg["rows"] = v
        if v == "all" and cur_h > 100:
            self.cfg["win_h"] = int(cur_h)      # 切到「不限」不改窗口高度，改为可滚动
        self.scroll = 0
        self._apply_geometry()
        self._persist()
        self._refresh_settings()

    def set_style(self, v):
        self.cfg["style"] = v
        self.rebuild()
        self._persist()
        self._refresh_settings()

    def set_theme(self, v):
        self.cfg["theme"] = v
        self.rebuild()
        self._persist()
        self._refresh_settings()

    def _open_url(self, url):
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass

    def _open_update(self):
        if getattr(self, "_update_url", None):
            self._open_url(self._update_url)

    @staticmethod
    def _version_gt(a: str, b: str) -> bool:
        def nums(v):
            out = []
            for part in re.split(r"[^0-9]+", v.strip().lstrip("vV")):
                if part:
                    out.append(int(part))
            return out
        try:
            return nums(a) > nums(b)
        except Exception:
            return False

    def check_update(self):
        if not hasattr(self, "update_lbl"):
            return
        self._update_url = None
        self.update_lbl.configure(text=self.t("checking"), fg=self.c["sub"])

        def work():
            url = f"https://api.github.com/repos/{APP_REPO}/releases/latest"
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": f"ClashConnWidget/{VERSION}",
                                  "Accept": "application/vnd.github+json"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    data = json.loads(r.read().decode("utf-8", "replace"))
                tag = str(data.get("tag_name") or "").lstrip("vV")
                html = data.get("html_url") or f"https://github.com/{APP_REPO}/releases"
                if self._version_gt(tag, VERSION):
                    self._update_url = html
                    self.root.after(0, lambda: self.update_lbl.configure(
                        text=self.t("update_new", v=tag), fg=self.c["ok"]))
                else:
                    self.root.after(0, lambda: self.update_lbl.configure(
                        text=self.t("update_latest", v=VERSION), fg=self.c["sub"]))
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    self.root.after(0, lambda: self.update_lbl.configure(
                        text=self.t("update_none"), fg=self.c["sub"]))
                else:
                    self.root.after(0, lambda: self.update_lbl.configure(
                        text=self.t("update_err", msg=f"HTTP {exc.code}"), fg=self.c["err"]))
            except Exception as exc:
                self.root.after(0, lambda: self.update_lbl.configure(
                    text=self.t("update_err", msg=str(exc)[:60]), fg=self.c["err"]))

        threading.Thread(target=work, daemon=True).start()

    def set_native(self, flag: bool):
        flag = bool(flag)
        if flag == bool(self.cfg.get("native")):
            return
        x, y = self.root.winfo_rootx(), self.root.winfo_rooty()
        self.cfg["native"] = flag
        self.native = flag
        self.root.withdraw()
        self.root.overrideredirect(not flag)
        self.rebuild()
        self.root.geometry(f"+{x}+{y}")
        self.root.deiconify()
        self._persist()
        self._refresh_settings()

    def set_accent(self, color: str):
        self.cfg["accent"] = (color or "").strip()
        self.rebuild()
        self._persist()
        self._refresh_settings()

    def pick_accent(self):
        cur = self.cfg.get("accent") or self.c["accent"]
        try:
            _rgb, hx = colorchooser.askcolor(color=cur, title=self.t("accent"),
                                             parent=self._set_win or self.root)
        except Exception:
            hx = None
        if hx:
            self.set_accent(hx)

    def _watch_system_theme(self):
        try:
            if self.cfg.get("theme") == "auto":
                name = self._resolved_theme()
                if name != self.theme_name:
                    self.rebuild()
                    self._refresh_settings()
        except Exception:
            pass
        self.root.after(3000, self._watch_system_theme)

    def set_lang(self, v):
        self.cfg["lang"] = v
        self.rebuild()
        self._persist()
        self._refresh_settings()

    def set_font_scale(self, v):
        self.cfg["font_scale"] = float(v)
        self.rebuild()
        self._persist()
        self._refresh_settings()

    def set_opacity(self, v):
        self.cfg["opacity"] = float(v)
        try:
            self.root.attributes("-alpha", float(v))
        except Exception:
            pass
        self._persist_later()

    def set_topmost(self, v):
        self.cfg["topmost"] = bool(v)
        self.root.attributes("-topmost", bool(v))
        self._persist()
        self._refresh_settings()

    def set_bool(self, key, v):
        self.cfg[key] = bool(v)
        if key == "autostart":
            set_autostart(bool(v))
        self._persist()
        self._refresh_settings()

    def reset_cols(self):
        self.cfg["col_w"] = None
        defaults = [self.S(round(110 * self.fs)), self.S(round(78 * self.fs)),
                    self.S(round(72 * self.fs))]
        self.col_w = self._clamp_cols(defaults, self._avail_w())
        self.COL_NODE_W, self.COL_DOWN_W, self.COL_UP_W = self.col_w
        self._redraw()
        self._persist()
        self._refresh_settings()

    def reset_width(self):
        self.cfg["win_w"] = None
        base = self.S(round((500 if self.cfg["style"] == "dash" else 490)
                            * (1 + (self.fs - 1) * 0.75)))
        self._apply_width(base)
        self._persist()
        self._refresh_settings()

    def toggle_collapse(self):
        self.cfg["collapsed"] = not self.cfg["collapsed"]
        self._apply_collapsed()
        self._persist()

    def toggle_topmost(self):
        self.set_topmost(not self.cfg["topmost"])

    def _apply_collapsed(self):
        for w in (self.spark, self.search_bar, self.tabs, self.table,
                  getattr(self, "mini_frame", None)):
            if w is not None:
                w.pack_forget()
        if self.cfg["collapsed"]:
            self.root.geometry(f"{self.W}x{self.HEAD_H}")
        elif self.cfg.get("mini"):
            self.mini_frame.pack(fill="both", expand=True)
            self.root.geometry(f"{self.W}x{self._win_h()}")
            self._update_mini()
        else:
            if self.spark:
                self.spark.pack(fill="x")
            if self.search_open:
                self.search_bar.pack(fill="x")
            self.tabs.pack(fill="x")
            self.table.pack(fill="both", expand=True)
            self.root.geometry(f"{self.W}x{self._win_h()}")
            self._redraw()
        self.root.after(20, self._round_corners)
        self.root.after(30, self._place_grips)
        self.root.after(40, self._layout_header)

    def toggle_search(self, force=None):
        want = (not self.search_open) if force is None else bool(force)
        if want == self.search_open:
            return
        if want and self.cfg["collapsed"]:
            self.cfg["collapsed"] = False
            self._apply_collapsed()
        self.search_open = want
        if want:
            self.search_bar.pack(fill="x", after=(self.spark if self.spark and
                                                  self.spark.winfo_ismapped() else self.head))
            self.root.geometry(f"{self.W}x{self._win_h()}")
            self.search_entry.focus_set()
        else:
            self.search_bar.pack_forget()
            self.search_var.set("")
            self.root.geometry(f"{self.W}x{self._win_h()}")
        self.root.after(20, self._redraw)

    def _on_search(self):
        self.scroll = 0
        self._update_counts()
        self._redraw()

    def _update_counts(self):
        try:
            if self.data:
                self.lbl_count.configure(
                    text=self.t("count", n=len(self._visible_rows()),
                                a=self.data.get("active", 0)), fg=self.c["sub"])
        except Exception:
            pass

    def _on_escape(self):
        if self.search_open:
            self.toggle_search(False)
        elif self.cfg["collapsed"]:
            self.toggle_collapse()

    def open_panel(self):
        import webbrowser
        webbrowser.open(self.prof()["api"].rstrip("/") + "/ui/#/connections")

    def copy_hosts(self):
        self._to_clipboard("\n".join(r["host"] for r in self.rows_visible))

    def copy_rows_tsv(self):
        lines = []
        for r in self.rows_visible:
            lines.append("\t".join([r["host"], r.get("node") or self.t("direct"),
                                    fmt_short(r["down"]), fmt_short(r["up"]),
                                    r.get("src", ""), r.get("rule", ""),
                                    r.get("net", "")]))
        self._to_clipboard("\n".join(lines))

    def _to_clipboard(self, txt):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(txt or "")
        except Exception:
            pass

    def _show_error(self):
        if not self.error:
            return
        kind = self.error.get("kind", "other")
        msg = self.t(f"diag_{kind}", msg=self.error.get("detail", ""),
                     code=self.error.get("detail", ""))
        self._toast(msg)

    def _toast(self, text):
        try:
            self.lbl_count.configure(text=text[:60], fg=self.c["err"])
        except Exception:
            pass

    # ------------------------------------------------------------ 详情
    def _show_details(self, row):
        c = self.c
        if self.details_win and self.details_win.winfo_exists():
            self.details_win.destroy()
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.configure(bg=c["bg"])
        win.attributes("-topmost", True)
        self.details_win = win
        frame = tk.Frame(win, bg=c["bg"], highlightthickness=1,
                         highlightbackground=c["border"])
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text=self.t("details_title"), bg=c["bg"], fg=c["title"],
                 font=self.f_h2).pack(anchor="w", padx=self.S(14), pady=(self.S(10), self.S(4)))
        rows = [
            (self.t("d_host"), row["host"]),
            (self.t("d_node"), self.t("direct") if row["direct"] else row["node"]),
            (self.t("d_chain"), row.get("chain") or "—"),
            (self.t("d_rule"), row.get("rule") or "—"),
            (self.t("d_src"), f'{row["src"]}:{row["sport"]}' if row["src"] else "—"),
            (self.t("d_net"), row.get("net") or "—"),
            (self.t("d_data"), f'↓{fmt_short(row["down_total"])}  ↑{fmt_short(row["up_total"])}'),
        ]
        for k, v in rows:
            line = tk.Frame(frame, bg=c["bg"])
            line.pack(fill="x", padx=self.S(14), pady=self.S(1))
            tk.Label(line, text=k, bg=c["bg"], fg=c["sub"], font=self.f_small,
                     width=6, anchor="w").pack(side="left")
            tk.Label(line, text=fit_text(str(v), self.f_ui, self.S(260)), bg=c["bg"],
                     fg=c["host"], font=self.f_ui, anchor="w").pack(side="left")
        foot = tk.Frame(frame, bg=c["bg"])
        foot.pack(fill="x", padx=self.S(14), pady=(self.S(8), self.S(10)))
        for txt, cmd in ((self.t("copy"), lambda: self._to_clipboard(row["host"])),
                         (self.t("close"), win.destroy)):
            lb = tk.Label(foot, text=txt, bg=c["chip_bg"], fg=c["chip_fg"],
                          font=self.f_small, padx=self.S(10), pady=self.S(3),
                          cursor="hand2")
            lb.pack(side="right", padx=(self.S(6), 0))
            lb.bind("<Button-1>", lambda e, f=cmd: f())
        win.update_idletasks()
        x = self.root.winfo_pointerx() + self.S(12)
        y = self.root.winfo_pointery() + self.S(10)
        x = min(x, self.root.winfo_screenwidth() - win.winfo_reqwidth() - self.S(8))
        y = min(y, self.root.winfo_screenheight() - win.winfo_reqheight() - self.S(8))
        win.geometry(f"+{max(8, x)}+{max(8, y)}")
        win.bind("<Escape>", lambda e: win.destroy())
        win.after(20, lambda: self._round_win(win))

    # ------------------------------------------------------------ 状态
    def _persist(self):
        self.cfg["x"], self.cfg["y"] = self.root.winfo_x(), self.root.winfo_y()
        self.cfg["win_w"] = int(self.W)
        save_cfg(self.cfg)

    def _persist_later(self):
        try:
            if self._save_job:
                self.root.after_cancel(self._save_job)
        except Exception:
            pass
        self._save_job = self.root.after(350, self._persist_now)

    def _persist_now(self):
        self._save_job = None
        self._persist()

    def _on_configure(self, e):
        """原生窗口模式下拖动/缩放后记住位置。"""
        if getattr(e, "widget", None) is not self.root:
            return
        try:
            if self._save_job:
                self.root.after_cancel(self._save_job)
        except Exception:
            pass
        self._save_job = self.root.after(700, self._persist_now)

    def _apply_mica(self):
        try:
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            dark = ctypes.c_int(1 if self.theme_name != "light" else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), 4)
            mica = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(mica), 4)
            corner = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner), 4)
        except Exception:
            pass

    def _round_corners(self):
        if getattr(self, "native", False):
            self._apply_mica()
            return
        try:
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            w = self.root.winfo_width() + 1
            h = self.root.winfo_height() + 1
            r = self.RADIUS * 2
            rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, w, h, r, r)
            ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)
            dark = ctypes.c_int(1 if self.theme_name != "light" else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), 4)
        except Exception:
            pass

    def rebuild(self):
        collapsed = self.cfg["collapsed"]
        x, y = self.root.winfo_x(), self.root.winfo_y()
        self.theme_name = self._resolved_theme()
        self.c = self._palette()
        self.st = STYLES[self.cfg["style"]]
        self.fs = float(self.cfg["font_scale"])
        self.root.configure(bg=self.c["bg"])
        self._fonts()
        self._metrics()
        for w in self.root.winfo_children():
            if isinstance(w, tk.Toplevel):
                continue
            w.destroy()
        if self.details_win and self.details_win.winfo_exists():
            self.details_win.destroy()
        self._build()
        self.cfg["collapsed"] = collapsed
        self.root.geometry(f"{self.W}x{self._win_h()}+{x}+{y}")
        self._apply_collapsed()
        self._refresh_view()
        if self._set_win and self._set_win.winfo_exists():
            self._set_win.lift()

    # ------------------------------------------------------------ 数据
    def _drain(self):
        latest = None
        try:
            while True:
                latest = self.q.get_nowait()
        except queue.Empty:
            pass
        if latest is not None:
            self._on_data(latest)
        self.root.after(150, self._drain)

    def _on_data(self, d):
        c = self.c
        if d.get("ok"):
            self.error = None
            self.data = d
            self.rows = d.get("rows") or []
            self.kernel = d.get("kernel", "?")
            self.lbl_dot.configure(fg=c["ok"])
            self.lbl_title.configure(fg=c["title"])
            count = len(self._visible_rows())
            self.lbl_count.configure(
                text=self.t("count", n=count, a=d.get("active", 0)), fg=c["sub"])
            self.lbl_down.configure(text="↓ " + fmt_short(d.get("down", 0)) + "/s")
            self.lbl_up.configure(text="↑ " + fmt_short(d.get("up", 0)) + "/s")
            if getattr(self, "native", False):
                try:
                    self.root.title(f'↓{fmt_short(d.get("down", 0))}/s '
                                    f'↑{fmt_short(d.get("up", 0))}/s · {APP_NAME}')
                except Exception:
                    pass
        else:
            self.error = {"kind": d.get("kind", "other"), "detail": d.get("detail", "")}
            self.rows = []
            self.lbl_dot.configure(fg=c["err"])
            self.lbl_title.configure(fg=c["sub"])
            self.lbl_count.configure(text=self.t("offline"), fg=c["err"])
            self.lbl_down.configure(text="↓ --")
            self.lbl_up.configure(text="↑ --")
        if self.cfg.get("mini"):
            self._update_mini()
        self._layout_header()
        self._redraw()

    # ------------------------------------------------------------ 设置
    def open_settings(self):
        if self._set_win and self._set_win.winfo_exists():
            self._set_win.lift()
            self._set_win.focus_force()
            return
        win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=self.c["bg"])
        self._set_win = win
        self._load_profile_vars()
        self._set_build()
        win.deiconify()
        win.update_idletasks()
        px = self.root.winfo_x() - win.winfo_width() - self.S(10)
        if px < self.S(8):
            px = self.root.winfo_x() + self.W + self.S(10)
        py = max(self.S(8), self.root.winfo_y())
        py = min(py, self.root.winfo_screenheight() - win.winfo_height() - self.S(8))
        win.geometry(f"+{max(self.S(8), px)}+{max(self.S(8), py)}")
        win.lift()
        win.bind("<Escape>", lambda e: self.close_settings())
        win.after(30, lambda: self._round_win(win))

    def _load_profile_vars(self):
        p = self.prof()
        self.p_name.set(p["name"])
        self.p_api.set(p["api"])
        self.p_secret.set(p["secret"])

    def close_settings(self):
        try:
            self._persist()
        except Exception:
            pass
        if self._set_win and self._set_win.winfo_exists():
            self._set_win.destroy()
        self._set_win = None

    def _refresh_settings(self):
        if self._set_win and self._set_win.winfo_exists():
            self._set_build()
            self._set_win.lift()

    def _round_win(self, win):
        try:
            win.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
            w, h = win.winfo_width() + 1, win.winfo_height() + 1
            r = self.RADIUS * 2
            rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, w, h, r, r)
            ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)
        except Exception:
            pass

    def _chips(self, parent, options, current, on_pick):
        c = self.c
        box = tk.Frame(parent, bg=c["bg"])
        for val, label in options:
            sel = (val == current)
            lb = tk.Label(box, text=label, font=self.f_small, cursor="hand2",
                          padx=self.S(8), pady=self.S(2),
                          bg=c["chip_on_bg"] if sel else c["chip_bg"],
                          fg=c["chip_on_fg"] if sel else c["chip_fg"])
            lb.pack(side="left", padx=(0, self.S(5)))
            if not sel:
                lb.bind("<Enter>", lambda e, w=lb: w.configure(bg=c["chip_hover"]))
                lb.bind("<Leave>", lambda e, w=lb: w.configure(bg=c["chip_bg"]))
            lb.bind("<Button-1>", lambda e, v=val: on_pick(v))
        return box

    def _button(self, parent, text, cmd, primary=False):
        c = self.c
        lb = tk.Label(parent, text=text, font=self.f_small, cursor="hand2",
                      padx=self.S(11), pady=self.S(3),
                      bg=c["chip_on_bg"] if primary else c["chip_bg"],
                      fg=c["chip_on_fg"] if primary else c["chip_fg"])
        lb.bind("<Button-1>", lambda e: cmd())
        return lb

    def _srow(self, parent, label, builder):
        c = self.c
        row = tk.Frame(parent, bg=c["bg"])
        row.pack(fill="x", pady=self.S(2))
        tk.Label(row, text=label, bg=c["bg"], fg=c["title"], font=self.f_ui,
                 anchor="w").pack(side="left")
        builder(row).pack(side="right")
        return row

    def _section(self, parent, text):
        c = self.c
        tk.Label(parent, text=text, bg=c["bg"], fg=c["sub"], font=self.f_small,
                 anchor="w").pack(fill="x", pady=(self.S(12), self.S(3)))

    def _entry(self, parent, var):
        c = self.c
        return tk.Entry(parent, textvariable=var, font=self.f_ui, bg=c["input_bg"],
                        fg=c["title"], insertbackground=c["title"], relief="flat",
                        highlightthickness=1, highlightbackground=c["border"],
                        highlightcolor=c["accent"])

    def _set_build(self):
        win = self._set_win
        if not win or not win.winfo_exists():
            return
        c, S = self.c, self.S
        for w in win.winfo_children():
            w.destroy()
        win.configure(bg=c["bg"])
        outer = tk.Frame(win, bg=c["bg"], highlightthickness=1,
                         highlightbackground=c["border"])
        outer.pack(fill="both", expand=True)
        head = tk.Frame(outer, bg=c["bg"], height=S(34))
        head.pack(fill="x")
        head.pack_propagate(False)
        title = tk.Label(head, text=self.t("set_title"), bg=c["bg"], fg=c["title"],
                         font=self.f_h2)
        title.pack(side="left", padx=(S(16), 0))
        close = tk.Label(head, text="✕", bg=c["bg"], fg=c["sub"], font=self.f_ui,
                         width=2, cursor="hand2")
        close.pack(side="right", padx=(0, S(6)))
        close.bind("<Button-1>", lambda e: self.close_settings())
        close.bind("<Enter>", lambda e: close.configure(fg=c["err"]))
        close.bind("<Leave>", lambda e: close.configure(fg=c["sub"]))
        for w in (head, title):
            w.bind("<Button-1>", self._set_drag_start)
            w.bind("<B1-Motion>", self._set_drag)

        body = tk.Frame(outer, bg=c["bg"])
        body.pack(fill="both", expand=True, padx=S(16), pady=(0, S(12)))
        body.grid_columnconfigure(0, weight=1, minsize=S(320))
        body.grid_columnconfigure(1, weight=1, minsize=S(280))
        left = tk.Frame(body, bg=c["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, S(18)))
        right = tk.Frame(body, bg=c["bg"])
        right.grid(row=0, column=1, sticky="nsew")

        lang = self.cfg["lang"]

        # ---------- 后台连接
        self._section(left, self.t("set_conn"))
        prof_box = tk.Frame(left, bg=c["bg"])
        prof_box.pack(fill="x")
        for i, p in enumerate(self.cfg["profiles"]):
            sel = (i == self.cfg["active"])
            lb = tk.Label(prof_box, text=fit_text(p["name"], self.f_small, S(80)),
                          font=self.f_small, cursor="hand2", padx=S(8), pady=S(2),
                          bg=c["chip_on_bg"] if sel else c["chip_bg"],
                          fg=c["chip_on_fg"] if sel else c["chip_fg"])
            lb.pack(side="left", padx=(0, S(5)))
            lb.bind("<Button-1>", lambda e, i=i: self._pick_profile(i))
        add = tk.Label(prof_box, text="＋", font=self.f_small, cursor="hand2",
                       padx=S(8), pady=S(2), bg=c["chip_bg"], fg=c["chip_fg"])
        add.pack(side="left")
        add.bind("<Button-1>", lambda e: self._add_profile())

        for lbl, var in ((self.t("p_name"), self.p_name),
                         (self.t("p_api"), self.p_api),
                         (self.t("p_secret"), self.p_secret)):
            frow = tk.Frame(left, bg=c["bg"])
            frow.pack(fill="x", pady=S(2))
            tk.Label(frow, text=lbl, bg=c["bg"], fg=c["sub"], font=self.f_small,
                     width=6, anchor="w").pack(side="left")
            self._entry(frow, var).pack(side="left", fill="x", expand=True, ipady=S(3))
        btn_row = tk.Frame(left, bg=c["bg"])
        btn_row.pack(fill="x", pady=(S(6), 0))
        self._button(btn_row, self.t("test"), self._test_profile).pack(side="left")
        self._button(btn_row, self.t("auto_detect"), self._auto_detect).pack(side="left",
                                                                             padx=(S(5), 0))
        self._button(btn_row, self.t("del_profile"), self._del_profile).pack(side="left",
                                                                            padx=(S(5), 0))
        self._button(btn_row, self.t("save"), self._save_profile, primary=True).pack(side="right")
        self.test_lbl = tk.Label(left, text="", bg=c["bg"], fg=c["sub"],
                                 font=self.f_small, anchor="w")
        self.test_lbl.pack(fill="x", pady=(S(4), 0))

        # ---------- 外观
        self._section(left, self.t("set_appearance"))
        themes = []
        for k in THEME_ORDER:
            themes.append((k, self.t("theme_auto") if k == "auto"
                           else THEMES[k][lang if lang in ("zh", "en") else "zh"]))
        self._srow(left, self.t("theme"),
                   lambda p: self._chips(p, themes, self.cfg["theme"], self.set_theme))

        # 强调色
        tk.Label(left, text=self.t("accent"), bg=c["bg"], fg=c["title"],
                 font=self.f_ui, anchor="w").pack(fill="x", pady=(S(4), S(2)))
        acc_row = tk.Frame(left, bg=c["bg"])
        acc_row.pack(fill="x")
        cur_acc = (self.cfg.get("accent") or "").lower()
        swatches = list(ACCENTS[:6])
        if cur_acc and cur_acc not in swatches:
            swatches.append(cur_acc)
        for col in swatches:
            sel = (cur_acc == col)
            sw = tk.Frame(acc_row, bg=col, width=S(18), height=S(18), cursor="hand2",
                          highlightthickness=2,
                          highlightbackground=(c["title"] if sel else c["bg"]))
            sw.pack(side="left", padx=(0, S(4)))
            sw.pack_propagate(False)
            sw.bind("<Button-1>", lambda e, cc=col: self.set_accent(cc))
        self._button(acc_row, self.t("custom"), self.pick_accent).pack(side="left",
                                                                      padx=(S(6), 0))
        self._button(acc_row, self.t("default"),
                     lambda: self.set_accent("")).pack(side="left", padx=(S(4), 0))
        styles = [(k, self.t(k)) for k in STYLE_ORDER]
        self._srow(left, self.t("style"),
                   lambda p: self._chips(p, styles, self.cfg["style"], self.set_style))
        shells = [("borderless", self.t("shell_borderless")),
                  ("native", self.t("shell_native"))]
        self._srow(left, self.t("shell"),
                   lambda p: self._chips(
                       p, shells, "native" if self.cfg.get("native") else "borderless",
                       lambda v: self.set_native(v == "native")))
        fonts = [(0.9, self.t("small")), (1.0, self.t("normal")), (1.15, self.t("large"))]
        self._srow(left, self.t("font"),
                   lambda p: self._chips(p, fonts, float(self.cfg["font_scale"]),
                                         self.set_font_scale))
        ops = [(0.6, "60%"), (0.75, "75%"), (0.85, "85%"), (0.95, "95%"), (1.0, "100%")]
        self._srow(left, self.t("opacity"),
                   lambda p: self._chips(p, ops, float(self.cfg["opacity"]),
                                         self.set_opacity))
        wrow = tk.Frame(left, bg=c["bg"])
        wrow.pack(fill="x", pady=(S(4), 0))
        self._button(wrow, self.t("reset_winw"), self.reset_width).pack(side="left")
        self._button(wrow, self.t("reset_colw"), self.reset_cols).pack(side="left",
                                                                       padx=(S(6), 0))

        # ---------- 列表
        self._section(right, self.t("set_list"))
        rows_opts = [(6, self.t("rows_n", n=6)), (8, self.t("rows_n", n=8)),
                     (10, self.t("rows_n", n=10)), (12, self.t("rows_n", n=12)),
                     ("all", self.t("rows_all"))]
        self._srow(right, self.t("rows"),
                   lambda p: self._chips(p, rows_opts, self.cfg["rows"], self.set_rows))
        ivs = [(0.5, self.t("sec", v=0.5)), (1.0, self.t("sec", v=1)),
               (2.0, self.t("sec", v=2))]
        self._srow(right, self.t("interval"),
                   lambda p: self._chips(p, ivs, float(self.cfg["interval"]), self.set_interval))
        toggles = [(True, self.t("on")), (False, self.t("off"))]
        for key in ("rule", "src", "net"):
            self._srow(right, self.t("c_" + key),
                       lambda p, k=key: self._chips(
                           p, toggles, bool(self.cfg["show_cols"].get(k)),
                           lambda v, kk=k: self.set_col_visible(kk, v)))

        # ---------- 行为
        self._section(right, self.t("set_behavior"))
        self._srow(right, self.t("topmost"),
                   lambda p: self._chips(p, toggles, bool(self.cfg["topmost"]),
                                         lambda v: self.set_topmost(v)))
        self._srow(right, self.t("collapse_start"),
                   lambda p: self._chips(p, toggles, bool(self.cfg["collapse_start"]),
                                         lambda v: self.set_bool("collapse_start", v)))
        self._srow(right, self.t("close_to_tray"),
                   lambda p: self._chips(p, toggles, bool(self.cfg["close_to_tray"]),
                                         lambda v: self.set_bool("close_to_tray", v)))
        self._srow(right, self.t("autostart"),
                   lambda p: self._chips(p, toggles, bool(self.cfg["autostart"]),
                                         lambda v: self.set_bool("autostart", v)))

        # ---------- 语言
        self._section(right, self.t("set_lang"))
        self._chips(right, [("zh", "中文"), ("en", "English")], self.cfg["lang"],
                    self.set_lang).pack(anchor="w")

        # ---------- 关于
        self._section(right, self.t("set_about"))
        p = self.prof()
        tk.Label(right, text=f"{APP_NAME}  ·  v{VERSION}", bg=c["bg"], fg=c["title"],
                 font=self.f_ui, anchor="w").pack(fill="x")
        link = tk.Label(right, text=f"github.com/{APP_REPO}", bg=c["bg"], fg=c["accent"],
                        font=self.f_small, anchor="w", cursor="hand2")
        link.pack(fill="x")
        link.bind("<Button-1>", lambda e: self._open_url(f"https://github.com/{APP_REPO}"))
        tk.Label(right, text=self.t("about_author", a=APP_AUTHOR), bg=c["bg"], fg=c["sub"],
                 font=self.f_small, anchor="w").pack(fill="x")
        tk.Label(right, text=self.t("about_version", v=VERSION), bg=c["bg"], fg=c["sub"],
                 font=self.f_small, anchor="w").pack(fill="x")
        tk.Label(right, text=self.t("about_line", api=p["api"] or "-", k=self.kernel),
                 bg=c["bg"], fg=c["sub"], font=self.f_small, anchor="w", justify="left",
                 wraplength=S(268)).pack(fill="x")
        tk.Label(right, text=f"Python {sys.version.split()[0]} · Tk {tk.TkVersion}",
                 bg=c["bg"], fg=c["colhdr"], font=self.f_small, anchor="w").pack(fill="x")
        up_row = tk.Frame(right, bg=c["bg"])
        up_row.pack(fill="x", pady=(S(6), 0))
        self._button(up_row, self.t("check_update"), self.check_update).pack(side="left")
        self.update_lbl = tk.Label(right, text="", bg=c["bg"], fg=c["sub"],
                                   font=self.f_small, anchor="w", justify="left",
                                   wraplength=S(268), cursor="hand2")
        self.update_lbl.pack(fill="x", pady=(S(4), 0))
        self.update_lbl.bind("<Button-1>", lambda e: self._open_update())
        self._update_url = None

        foot = tk.Frame(body, bg=c["bg"])
        foot.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(S(12), 0))
        self._button(foot, self.t("reset"), self.reset_settings).pack(side="left")
        self._button(foot, self.t("close"), self.close_settings).pack(side="right")

        win.update_idletasks()
        mapped = win.winfo_ismapped()
        x, y = (win.winfo_x(), win.winfo_y()) if mapped else (0, 0)
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        win.geometry(f"{w}x{h}+{x}+{y}" if mapped else f"{w}x{h}")
        win.after(20, lambda: self._round_win(win))

    def _pick_profile(self, i):
        self.cfg["active"] = i
        self._load_profile_vars()
        p = self.prof()
        self.poller.set_endpoint(p["api"], p["secret"])
        self.data = None
        self.rows = []
        self.lbl_prof.configure(text=self._prof_text())
        self._persist()
        self._refresh_settings()
        self._redraw()

    def _add_profile(self):
        self.cfg["profiles"].append({"name": f"配置 {len(self.cfg['profiles']) + 1}",
                                     "api": "", "secret": ""})
        self.cfg["active"] = len(self.cfg["profiles"]) - 1
        self._load_profile_vars()
        p = self.prof()
        self.poller.set_endpoint(p["api"] or self.cfg["profiles"][0]["api"], p["secret"])
        self.lbl_prof.configure(text=self._prof_text())
        self._persist()
        self._refresh_settings()
        self._redraw()

    def _del_profile(self):
        if len(self.cfg["profiles"]) <= 1:
            return
        self.cfg["profiles"].pop(self.cfg["active"])
        self.cfg["active"] = max(0, self.cfg["active"] - 1)
        self._load_profile_vars()
        p = self.prof()
        self.poller.set_endpoint(p["api"], p["secret"])
        self.lbl_prof.configure(text=self._prof_text())
        self._persist()
        self._refresh_settings()
        self._redraw()

    def _save_profile(self):
        p = self.prof()
        p["name"] = (self.p_name.get() or "配置").strip()[:24]
        p["api"] = norm_api(self.p_api.get())
        p["secret"] = self.p_secret.get().strip()
        self.lbl_prof.configure(text=self._prof_text())
        self.poller.set_endpoint(p["api"], p["secret"])
        self.data = None
        self.rows = []
        self._persist()
        self._refresh_settings()
        self._redraw()

    def _test_profile(self):
        if not hasattr(self, "test_lbl"):
            return
        api = norm_api(self.p_api.get())
        secret = self.p_secret.get().strip()
        self.test_lbl.configure(text=self.t("testing"), fg=self.c["sub"])

        def work():
            r = probe_api(api, secret, 3.0)
            if r:
                self.root.after(0, lambda: self.test_lbl.configure(
                    text=self.t("test_ok", ver=r[1]), fg=self.c["ok"]))
            else:
                self.root.after(0, lambda: self.test_lbl.configure(
                    text=self.t("test_fail", msg=api or "-"), fg=self.c["err"]))

        threading.Thread(target=work, daemon=True).start()

    def _auto_detect(self):
        if not hasattr(self, "test_lbl"):
            return
        self.test_lbl.configure(text=self.t("detecting"), fg=self.c["sub"])

        def work():
            found = discover_backends()
            if found:
                api, ver = found[0]
                self.root.after(0, lambda: (self.p_api.set(api),
                                            self.test_lbl.configure(
                                                text=self.t("found", url=api, ver=ver),
                                                fg=self.c["ok"])))
            else:
                self.root.after(0, lambda: self.test_lbl.configure(
                    text=self.t("not_found"), fg=self.c["err"]))

        threading.Thread(target=work, daemon=True).start()

    def reset_settings(self):
        keep = {k: self.cfg.get(k) for k in ("x", "y", "profiles", "active")}
        self.cfg.update(json.loads(json.dumps(DEFAULT_CFG)))
        self.cfg.update(keep)
        self.root.attributes("-topmost", bool(self.cfg["topmost"]))
        self.root.attributes("-alpha", float(self.cfg["opacity"]))
        set_autostart(bool(self.cfg["autostart"]))
        self.rebuild()
        self._persist()
        self._refresh_settings()

    def _set_drag_start(self, e):
        win = self._set_win
        if win and win.winfo_exists():
            self._sdrag = {"x": e.x_root, "y": e.y_root,
                           "wx": win.winfo_x(), "wy": win.winfo_y()}

    def _set_drag(self, e):
        win, d = self._set_win, self._sdrag
        if win and win.winfo_exists() and d:
            win.geometry(f"+{d['wx'] + e.x_root - d['x']}+{d['wy'] + e.y_root - d['y']}")

    # ------------------------------------------------------------ 首启引导
    def show_wizard(self):
        if self._wizard and self._wizard.winfo_exists():
            self._wizard.lift()
            return
        c = self.c
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=c["bg"])
        self._wizard = win
        frame = tk.Frame(win, bg=c["bg"], highlightthickness=1,
                         highlightbackground=c["border"])
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text=self.t("wizard_title"), bg=c["bg"], fg=c["title"],
                 font=self.f_h2).pack(anchor="w", padx=self.S(18), pady=(self.S(14), self.S(6)))
        tk.Label(frame, text=self.t("wizard_desc"), bg=c["bg"], fg=c["sub"],
                 font=self.f_ui, justify="left").pack(anchor="w", padx=self.S(18))
        var = tk.StringVar(master=win, value=self.prof()["api"])
        entry = self._entry(frame, var)
        entry.pack(fill="x", padx=self.S(18), pady=(self.S(10), self.S(6)), ipady=self.S(4))
        status = tk.Label(frame, text="", bg=c["bg"], fg=c["sub"], font=self.f_small,
                          anchor="w")
        status.pack(fill="x", padx=self.S(18))
        btns = tk.Frame(frame, bg=c["bg"])
        btns.pack(fill="x", padx=self.S(18), pady=(self.S(8), self.S(14)))

        def use():
            api = norm_api(var.get())
            if not api:
                return
            self.prof()["api"] = api
            self.poller.set_endpoint(api, self.prof()["secret"])
            self.cfg["first_run_done"] = True
            self._persist()
            win.destroy()

        def detect():
            status.configure(text=self.t("detecting"), fg=self.c["sub"])

            def work():
                found = discover_backends()
                if found:
                    self.root.after(0, lambda: (var.set(found[0][0]),
                                                status.configure(
                                                    text=self.t("found", url=found[0][0],
                                                                ver=found[0][1]),
                                                    fg=self.c["ok"])))
                else:
                    self.root.after(0, lambda: status.configure(
                        text=self.t("not_found"), fg=self.c["err"]))
            threading.Thread(target=work, daemon=True).start()

        self._button(btns, self.t("auto_detect"), detect).pack(side="left")
        self._button(btns, self.t("wizard_skip"),
                     lambda: (self.cfg.update({"first_run_done": True}), self._persist(),
                              win.destroy())).pack(side="left", padx=(self.S(6), 0))
        self._button(btns, self.t("wizard_start"), use, primary=True).pack(side="right")
        win.update_idletasks()
        x = self.root.winfo_x() + (self.W - win.winfo_width()) // 2
        y = self.root.winfo_y() + self.S(70)
        win.geometry(f"+{max(8, x)}+{max(8, y)}")
        entry.focus_set()
        entry.bind("<Return>", lambda e: use())
        win.after(30, lambda: self._round_win(win))

    # ------------------------------------------------------------ 托盘
    def _init_tray(self):
        try:
            self.tray = TrayIcon(self.root, res_path("app.ico"),
                                 self._tray_toggle, self._tray_menu)
            self.tray.on_maximize = self.toggle_collapse
            try:
                self.tray.register_hotkey(self._tray_toggle)
            except Exception:
                pass
        except Exception:
            self.tray = None

    def _tray_toggle(self):
        if self.root.state() == "withdrawn":
            self.show_window()
        else:
            self.root.withdraw()

    def _tray_menu(self):
        c = self.c
        m = tk.Menu(self.root, **self._menu_colors())
        hidden = self.root.state() == "withdrawn"
        m.add_command(label=self.t("tray_show") if hidden else self.t("tray_hide"),
                      command=self._tray_toggle)
        m.add_command(label=self.t("menu_settings"), command=self._tray_settings)
        m.add_command(label=self.t("menu_open"), command=self.open_panel)
        m.add_separator()
        m.add_command(label=self.t("tray_quit"), command=self.quit_app)
        try:
            m.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally:
            m.grab_release()

    def _tray_settings(self):
        self.show_window()
        self.open_settings()

    def show_window(self):
        self.root.deiconify()
        self.root.attributes("-topmost", bool(self.cfg["topmost"]))
        self.root.lift()

    # ------------------------------------------------------------ 关闭
    def on_close(self):
        if self.cfg.get("close_to_tray") and self.tray and self.tray.ok:
            self.root.withdraw()
            return
        self.quit_app()

    def quit_app(self):
        try:
            self._persist()
        except Exception:
            pass
        try:
            if self.tray:
                self.tray.remove()
        except Exception:
            pass
        try:
            self.poller.stop()
        except Exception:
            pass
        for w in (self._set_win, self._wizard, self.details_win):
            try:
                if w and w.winfo_exists():
                    w.destroy()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.deiconify()
        self._init_tray()
        self.root.mainloop()


# ---------------------------------------------------------------- 入口
_mutex = None


def single_instance():
    global _mutex
    try:
        k = ctypes.windll.kernel32
        _mutex = k.CreateMutexW(None, False, "Local\\ClashConnWidget_v2")
        return k.GetLastError() != 183
    except Exception:
        return True


def main():
    ap = argparse.ArgumentParser(description="Clash 桌面实时连接小窗")
    ap.add_argument("--api", default=None)
    ap.add_argument("--secret", default=None)
    ap.add_argument("--interval", type=float, default=None)
    args = ap.parse_args()

    if not single_instance():
        # 已有实例：把它叫到前台
        try:
            hwnd = ctypes.windll.user32.FindWindowW(None, APP_NAME)
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 5)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
        return

    cfg = load_cfg()
    if args.api:
        cfg["profiles"][cfg["active"]]["api"] = norm_api(args.api)
    if args.secret is not None:
        cfg["profiles"][cfg["active"]]["secret"] = args.secret
    if args.interval:
        cfg["interval"] = args.interval
    if cfg.get("collapse_start"):
        cfg["collapsed"] = True

    w = ConnWidget(cfg)
    try:
        w.run()
    except KeyboardInterrupt:
        w.quit_app()


if __name__ == "__main__":
    main()
