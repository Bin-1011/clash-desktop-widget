# 在桌面创建「Clash 连接小窗」快捷方式（优先指向打包好的 exe）
$ErrorActionPreference = 'Stop'
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $dir 'ClashConnWidget.exe'

$desktop = [Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desktop 'Clash 连接小窗.lnk'

$sh = New-Object -ComObject WScript.Shell
$lnk = $sh.CreateShortcut($lnkPath)
if (Test-Path $exe) {
    $lnk.TargetPath = $exe
    $lnk.Arguments = ''
} else {
    $pyw = 'C:\Python314\pythonw.exe'
    if (-not (Test-Path $pyw)) { $pyw = (Get-Command pythonw.exe).Source }
    $lnk.TargetPath = $pyw
    $lnk.Arguments = '"' + (Join-Path $dir 'conn_widget.py') + '"'
}
$lnk.WorkingDirectory = $dir
$lnk.WindowStyle = 7
$lnk.Description = 'Clash / Mihomo 实时连接小窗'
$icon = Join-Path $dir 'app.ico'
if (Test-Path $icon) { $lnk.IconLocation = $icon + ',0' }
$lnk.Save()

Write-Host "已创建: $lnkPath" -ForegroundColor Green
Write-Host "双击桌面图标即可启动（默认收进托盘，托盘右键可退出）。"
