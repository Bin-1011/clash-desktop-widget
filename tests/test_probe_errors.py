# -*- coding: utf-8 -*-
"""组 F（M-3 / QA）探测失败分类与测试连接文案的单元测试。

只使用标准库；本地起 HTTP 服务或 mock urlopen，不启动 Tk mainloop。
"""

import http.server
import json
import threading
import unittest
import urllib.error
from unittest import mock

import conn_widget


class _ProbeHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/version":
            self.send_error(404)
            return
        status = getattr(self.server, "probe_status", 200)
        if status == 200:
            body = json.dumps({"version": "v9.9.9"}).encode("utf-8")
        else:
            body = b"{}"
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


class ProbeErrorTests(unittest.TestCase):
    def _serve(self, status):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _ProbeHandler)
        server.probe_status = status
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_port}"

    def test_401_is_classified_as_auth_and_formatted_with_diag_auth(self):
        base = self._serve(401)
        result = conn_widget.probe_api(base, "wrong-secret", timeout=2.0)

        self.assertIsNone(result[0])
        self.assertEqual(result[1], "auth")
        text = conn_widget.format_probe_result(result, "zh")
        self.assertIn("Secret", text)
        self.assertIn("401", text)
        self.assertNotIn(base, text)
        self.assertNotIn("失败：", text)

    def test_404_is_classified_as_not_clash_and_formatted_with_diag_not_clash(self):
        base = self._serve(404)
        result = conn_widget.probe_api(base, "", timeout=2.0)

        self.assertIsNone(result[0])
        self.assertEqual(result[1], "not_clash")
        text = conn_widget.format_probe_result(result, "zh")
        self.assertIn("不是 Clash", text)
        self.assertIn("404", text)
        self.assertNotIn(base, text)

    def test_success_still_returns_api_and_version(self):
        base = self._serve(200)
        result = conn_widget.probe_api(base, "", timeout=2.0)

        self.assertEqual(result, (base, "v9.9.9"))
        self.assertEqual(
            conn_widget.format_probe_result(result, "zh"),
            conn_widget.I18N["zh"]["test_ok"].format(ver="v9.9.9"),
        )
        self.assertEqual(
            conn_widget.format_probe_result(result, "en"),
            conn_widget.I18N["en"]["test_ok"].format(ver="v9.9.9"),
        )

    def test_timeout_and_refused_have_distinct_kinds(self):
        with mock.patch.object(conn_widget, "api_urlopen",
                               side_effect=TimeoutError("timed out")):
            timeout = conn_widget.probe_api("http://127.0.0.1:1", "", timeout=0.1)
        self.assertEqual(timeout[1], "timeout")
        self.assertIn("超时", conn_widget.format_probe_result(timeout, "zh"))

        refused_exc = urllib.error.URLError(
            ConnectionRefusedError(111, "Connection refused"))
        with mock.patch.object(conn_widget, "api_urlopen", side_effect=refused_exc):
            refused = conn_widget.probe_api("http://127.0.0.1:1", "", timeout=0.1)
        self.assertEqual(refused[1], "refused")
        self.assertIn("拒绝", conn_widget.format_probe_result(refused, "zh"))

    def test_empty_address_is_badurl_without_network_call(self):
        with mock.patch.object(conn_widget, "api_urlopen") as opener:
            result = conn_widget.probe_api("   ", "", timeout=0.1)
        opener.assert_not_called()
        self.assertIsNone(result[0])
        self.assertEqual(result[1], "badurl")
        self.assertIn("地址无效", conn_widget.format_probe_result(result, "zh"))

    def test_discover_backends_does_not_treat_401_as_available(self):
        with mock.patch.object(conn_widget, "gateway_ip", return_value=""), \
                mock.patch.object(conn_widget, "probe_api",
                                  return_value=(None, "auth", "401")):
            self.assertEqual(conn_widget.discover_backends(), [])

    def test_discover_backends_keeps_real_success(self):
        with mock.patch.object(conn_widget, "gateway_ip", return_value=""), \
                mock.patch.object(conn_widget, "probe_api",
                                  return_value=("http://127.0.0.1:9090", "v1")):
            found = conn_widget.discover_backends()
        self.assertEqual(found, [("http://127.0.0.1:9090", "v1")])


class ClassifyHttpDetailTests(unittest.TestCase):
    def _http_error(self, code):
        return urllib.error.HTTPError(
            "http://127.0.0.1:9090/version", code, "error", None, None)

    def test_http_detail_is_just_status_code(self):
        for code in (400, 401, 404, 502):
            kind, detail = conn_widget.classify_http_error(self._http_error(code))
            self.assertNotIn("HTTP", detail)
            self.assertEqual(detail, str(code))
            self.assertIn(kind, ("auth", "not_clash", "http"))

    def test_poller_classify_uses_same_classifier(self):
        exc = self._http_error(502)
        self.assertEqual(conn_widget.Poller._classify(exc),
                         conn_widget.classify_http_error(exc))

    def test_diag_http_template_has_no_duplicated_prefix(self):
        kind, detail = conn_widget.classify_http_error(self._http_error(502))
        self.assertEqual(kind, "http")
        for lang in ("zh", "en"):
            text = conn_widget.I18N[lang]["diag_http"].format(code=detail)
            self.assertNotIn("HTTP HTTP", text)
            self.assertIn("502", text)

    def test_auth_and_not_clash_templates_have_no_duplicated_prefix(self):
        for code, kind in ((401, "auth"), (404, "not_clash")):
            _kind, detail = conn_widget.classify_http_error(self._http_error(code))
            for lang in ("zh", "en"):
                text = conn_widget.I18N[lang][f"diag_{kind}"].format(
                    code=detail, msg=detail)
                self.assertNotIn("HTTP HTTP", text)


if __name__ == "__main__":
    unittest.main()
