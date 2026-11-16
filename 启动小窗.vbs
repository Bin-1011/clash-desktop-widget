' 无控制台启动 Clash 连接小窗
' 优先使用同目录的 ClashConnWidget.exe（打包版），否则回退到 pythonw + conn_widget.py
Option Explicit
Dim fso, sh, dir, exePath, pyw, script
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

dir = fso.GetParentFolderName(WScript.ScriptFullName)
exePath = dir & "\ClashConnWidget.exe"
script = dir & "\conn_widget.py"

sh.CurrentDirectory = dir
If fso.FileExists(exePath) Then
    sh.Run """" & exePath & """", 0, False
Else
    pyw = "C:\Python314\pythonw.exe"
    If Not fso.FileExists(pyw) Then pyw = "pythonw.exe"
    sh.Run """" & pyw & """ """ & script & """", 0, False
End If
