#!/usr/bin/env python3
"""本地假 mihomo 接口，用于截图/演示（不含任何真实数据）。

    python tools/mock_api.py [port]

提供 /version 与 /connections，数据每秒自然增长，域名均为示例。
"""

import json
import random
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 17890

HOSTS = [
    ("cdn.jsdelivr.net", "🇭🇰 香港 01", "192.168.1.10", 120_000, 20_000, "RuleSet", "site-cdn"),
    ("api.github.com", "🇭🇰 香港 01", "192.168.1.10", 60_000, 12_000, "RuleSet", "site-github"),
    ("fonts.gstatic.com", "DIRECT", "192.168.1.11", 30_000, 4_000, "RuleSet", "site-google"),
    ("www.youtube.com", "🇯🇵 东京 02", "192.168.1.11", 900_000, 40_000, "RuleSet", "site-youtube"),
    ("i.scdn.co", "🇸🇬 新加坡 01", "192.168.1.12", 180_000, 18_000, "RuleSet", "site-spotify"),
    ("registry.npmjs.org", "🇭🇰 香港 01", "192.168.1.10", 90_000, 9_000, "RuleSet", "site-npm"),
    ("telemetry.example.org", "DIRECT", "192.168.1.11", 2_000, 1_200, "Domain", "example.org"),
    ("intranet.example.net", "DIRECT", "192.168.1.12", 500, 300, "Domain", "example.net"),
    ("docs.example.com", "🇯🇵 东京 02", "192.168.1.10", 25_000, 3_000, "RuleSet", "site-docs"),
    ("static.example-cdn.com", "🇸🇬 新加坡 01", "192.168.1.11", 240_000, 15_000, "RuleSet", "site-static"),
    ("mail.example.com", "DIRECT", "192.168.1.12", 8_000, 6_000, "Domain", "example.com"),
    ("updates.example.io", "🇭🇰 香港 01", "192.168.1.10", 45_000, 5_000, "RuleSet", "site-updates"),
]

RULESET_GROUPS = ["🚀 节点选择", "⚡ 自动选择", "🐟 漏网之鱼"]
state = []


def init_state():
    now = time.time()
    for i, (host, node, ip, rd, ru, rule, payload) in enumerate(HOSTS):
        state.append({
            "id": f"demo-{i:03d}",
            "host": host, "node": node, "ip": ip, "rule": rule, "payload": payload,
            "down": random.uniform(50_000, 900_000),
            "up": random.uniform(5_000, 60_000),
            "last": now - random.uniform(5, 600),
            "rd": rd, "ru": ru,
        })


def snapshot():
    now = time.time()
    conns = []
    total_down = total_up = 0
    for st in state:
        dt = max(0.2, now - st["last"])
        st["last"] = now
        jitter = random.uniform(0.55, 1.45)
        st["down"] += st["rd"] * jitter * dt
        st["up"] += st["ru"] * jitter * dt
        total_down += st["down"]
        total_up += st["up"]
        node = st["node"]
        chains = [node] + [random.choice(RULESET_GROUPS)] if node != "DIRECT" else ["DIRECT", "🐟 漏网之鱼"]
        conns.append({
            "id": st["id"],
            "metadata": {
                "network": random.choice(["tcp", "tcp", "tcp", "udp"]),
                "type": "Redir",
                "sourceIP": st["ip"],
                "sourcePort": str(random.randint(30000, 65000)),
                "destinationIP": "",
                "destinationPort": "443",
                "inboundName": "DEFAULT-REDIR",
                "host": st["host"],
                "dnsMode": "fake-ip",
                "process": "",
                "specialRules": "",
                "remoteDestination": "203.0.113.7",
            },
            "upload": int(st["up"]),
            "download": int(st["down"]),
            "start": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(st["last"])),
            "chains": chains,
            "rule": st["rule"],
            "rulePayload": st["payload"],
        })
    return {
        "downloadTotal": int(total_down),
        "uploadTotal": int(total_up),
        "connections": conns,
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/version"):
            self._send({"version": "v1.19.34", "meta": True})
        elif self.path.startswith("/connections"):
            self._send(snapshot())
        else:
            self._send({"error": "not found"}, 404)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    init_state()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"mock mihomo api on http://127.0.0.1:{PORT}")
    srv.serve_forever()
