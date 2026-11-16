p = "README.md"
s = open(p, encoding="utf-8").read()
s = s.replace("- **关于**：版本、数据源、内核版本",
              "- **关于**：版本、仓库地址（可点击）、作者、运行环境、数据源与内核版本，以及「检查更新」")
s = s.replace("## License", """## 版本与更新

当前版本 **v3.0.0**。发布版本在 [Releases](https://github.com/Bin-1011/clash-desktop-widget/releases)，
程序里「设置 → 关于 → 检查更新」会读取 GitHub 最新 Release 并对比版本号。

## License""")
open(p, "w", encoding="utf-8").write(s)
print("readme ok")
