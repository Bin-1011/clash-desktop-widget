# 重新打包单文件 exe（需先: python -m pip install pyinstaller）
$ErrorActionPreference = 'Stop'
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $dir

python -m PyInstaller --noconfirm --onefile --noconsole --name ClashConnWidget `
    --icon app.ico --add-data "app.ico;." conn_widget.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 失败" }

Copy-Item (Join-Path $dir 'dist\ClashConnWidget.exe') (Join-Path $dir 'ClashConnWidget.exe') -Force
Write-Host "已生成: $(Join-Path $dir 'ClashConnWidget.exe')" -ForegroundColor Green
