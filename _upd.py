p = "conn_widget.py"
s = open(p, encoding="utf-8").read()
n0 = len(s)

# 版本与仓库常量
s = s.replace('VERSION = "2.0.0"\nAPP_NAME = "Clash 连接小窗"',
              'VERSION = "3.0.0"\nAPP_REPO = "Bin-1011/clash-desktop-widget"\nAPP_AUTHOR = "Bin-1011"\nAPP_NAME = "Clash 连接小窗"')

# i18n
s = s.replace('"about_line": "v{v} · 数据源 {api} · 内核 {k}",',
'''"about_line": "数据源 {api} · 内核 {k}",
        "about_version": "版本 v{v} · MIT License",
        "about_author": "作者 {a}",
        "check_update": "检查更新", "checking": "检查中…",
        "update_latest": "已是最新版本 v{v}",
        "update_new": "发现新版本 v{v}，点击这里打开下载页",
        "update_none": "仓库还没有发布 Release",
        "update_err": "检查失败：{msg}",''')
s = s.replace('"about_line": "v{v} · source {api} · kernel {k}",',
'''"about_line": "source {api} · kernel {k}",
        "about_version": "Version v{v} · MIT License",
        "about_author": "Author {a}",
        "check_update": "Check for updates", "checking": "Checking…",
        "update_latest": "Up to date (v{v})",
        "update_new": "v{v} available — click to open",
        "update_none": "No releases published yet",
        "update_err": "Check failed: {msg}",''')

# 关于区块
old_about = '''        self._section(right, self.t("set_about"))
        p = self.prof()
        tk.Label(right, text=self.t("about_line", v=VERSION, api=p["api"] or "-",
                                    k=self.kernel), bg=c["bg"], fg=c["sub"],
                 font=self.f_small, anchor="w", justify="left",
                 wraplength=S(270)).pack(fill="x")'''
assert old_about in s
new_about = '''        self._section(right, self.t("set_about"))
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
        self._update_url = None'''
s = s.replace(old_about, new_about)

# 方法：打开链接 / 检查更新 / 版本比较
old_m = '''    def set_native(self, flag: bool):'''
new_m = '''    def _open_url(self, url):
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

    def set_native(self, flag: bool):'''
s = s.replace(old_m, new_m)
open(p, "w", encoding="utf-8").write(s)
print("patched", n0, "->", len(s))
