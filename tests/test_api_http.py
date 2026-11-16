# -*- coding: utf-8 -*-
"""组 C（H-8）Clash API 请求绕过系统代理的单元测试。

只用标准库；本地起 HTTP 服务，不启动 Tk mainloop。
"""

import http.server
import inspect
import json
import os
import queue
import threading
import unittest
from unittest import mock

import conn_widget


class _ApiHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/version":
            body = json.dumps({"version": "v1.2.3"}).encode("utf-8")
        elif self.path == "/connections":
            body = json.dumps({"connections": [], "downloadTotal": 0}).encode("utf-8")
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


class ApiOpenerTests(unittest.TestCase):
    def setUp(self):
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _ApiHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def _proxy_env(self):
        # 指向一个必然不可达的代理；请求若走环境代理就会失败。
        proxy = "http://127.0.0.1:1"
        return {
            "HTTP_PROXY": proxy,
            "HTTPS_PROXY": proxy,
            "http_proxy": proxy,
            "https_proxy": proxy,
            "ALL_PROXY": proxy,
            "all_proxy": proxy,
            "NO_PROXY": "",
            "no_proxy": "",
        }

    def test_api_opener_has_no_environment_proxy_handler(self):
        # Python 的 OpenerDirector.add_handler 会忽略没有任何 open_* 方法的
        # ProxyHandler({})（空代理表不会注册代理协议），所以这里可能为空；
        # 关键是不存在带非空 proxies 的代理 handler。
        handlers = [
            h for h in conn_widget.API_OPENER.handlers
            if isinstance(h, conn_widget.urllib.request.ProxyHandler)
        ]
        for handler in handlers:
            self.assertEqual(handler.proxies, {})
        self.assertFalse(
            any(getattr(h, "proxies", {}) for h in conn_widget.API_OPENER.handlers),
            "API opener 不应带有任何环境代理配置",
        )

    def test_probe_api_ignores_unreachable_environment_proxy(self):
        with mock.patch.dict(os.environ, self._proxy_env(), clear=False):
            result = conn_widget.probe_api(self.base, "", timeout=2.0)
        self.assertIsNotNone(result, "probe_api 不应被不可达的系统代理影响")
        self.assertEqual(result[0], self.base)
        self.assertEqual(result[1], "v1.2.3")

    def test_poller_get_uses_api_opener_and_ignores_proxy(self):
        poller = conn_widget.Poller(self.base, "secret", 1.0, queue.Queue())
        with mock.patch.dict(os.environ, self._proxy_env(), clear=False), \
                mock.patch.object(conn_widget.urllib.request, "urlopen",
                                  side_effect=AssertionError("不应使用默认 urlopen")):
            data = poller._get("/connections", timeout=2.0)
        self.assertEqual(data["connections"], [])


class CheckUpdateProxyTests(unittest.TestCase):
    def test_check_update_still_uses_default_urlopen_for_github(self):
        source = inspect.getsource(conn_widget.ConnWidget.check_update)
        self.assertIn("urllib.request.urlopen", source)
        self.assertNotIn("API_OPENER", source)
        self.assertNotIn("api_urlopen", source)


if __name__ == "__main__":
    unittest.main()
