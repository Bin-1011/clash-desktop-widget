# 生成 app.ico（多尺寸 PNG 压缩 ICO），仅需 PowerShell 7 + System.Drawing
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$outDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$icoPath = Join-Path $outDir 'app.ico'
$previewPath = Join-Path $outDir 'app_preview.png'

function New-RoundPath([single]$x, [single]$y, [single]$w, [single]$h, [single]$r) {
    $p = New-Object System.Drawing.Drawing2D.GraphicsPath
    $d = [single]($r * 2)
    $p.AddArc($x, $y, $d, $d, 180, 90)
    $p.AddArc($x + $w - $d, $y, $d, $d, 270, 90)
    $p.AddArc($x + $w - $d, $y + $h - $d, $d, $d, 0, 90)
    $p.AddArc($x, $y + $h - $d, $d, $d, 90, 90)
    $p.CloseFigure()
    return $p
}

function New-IconPng([int]$size) {
    $s = $size / 256.0
    $bmp = New-Object System.Drawing.Bitmap $size, $size
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.Clear([System.Drawing.Color]::Transparent)

    # 背景
    $path = New-RoundPath (6 * $s) (6 * $s) (244 * $s) (244 * $s) (56 * $s)
    $r0 = [int](244 * $s)
    $rect = New-Object System.Drawing.Rectangle (6 * $s), (6 * $s), $r0, $r0
    $brush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
        $rect,
        [System.Drawing.Color]::FromArgb(255, 22, 30, 43),
        [System.Drawing.Color]::FromArgb(255, 8, 11, 17),
        [System.Drawing.Drawing2D.LinearGradientMode]::Vertical)
    $g.FillPath($brush, $path)

    $border = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 48, 60, 80)), ([single](3 * $s))
    $g.DrawPath($border, $path)

    # 下行箭头（绿）
    $green = [System.Drawing.Color]::FromArgb(255, 52, 211, 153)
    $blue = [System.Drawing.Color]::FromArgb(255, 96, 165, 250)
    $pen = New-Object System.Drawing.Pen $green, ([single](20 * $s))
    $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $g.DrawLine($pen, [single](170 * $s), [single](64 * $s), [single](170 * $s), [single](150 * $s))
    $p1 = New-Object System.Drawing.Drawing2D.GraphicsPath
    $p1.AddPolygon([System.Drawing.PointF[]]@(
        (New-Object System.Drawing.PointF (138 * $s), (132 * $s)),
        (New-Object System.Drawing.PointF (202 * $s), (132 * $s)),
        (New-Object System.Drawing.PointF (170 * $s), (196 * $s))))
    $g.FillPath((New-Object System.Drawing.SolidBrush $green), $p1)

    # 上行箭头（蓝）
    $pen2 = New-Object System.Drawing.Pen $blue, ([single](20 * $s))
    $pen2.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen2.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $g.DrawLine($pen2, [single](86 * $s), [single](192 * $s), [single](86 * $s), [single](106 * $s))
    $p2 = New-Object System.Drawing.Drawing2D.GraphicsPath
    $p2.AddPolygon([System.Drawing.PointF[]]@(
        (New-Object System.Drawing.PointF (54 * $s), (124 * $s)),
        (New-Object System.Drawing.PointF (118 * $s), (124 * $s)),
        (New-Object System.Drawing.PointF (86 * $s), (60 * $s))))
    $g.FillPath((New-Object System.Drawing.SolidBrush $blue), $p2)

    $ms = New-Object System.IO.MemoryStream
    $g.Dispose()
    $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    return ,$ms.ToArray()
}

$sizes = @(16, 24, 32, 48, 64, 128, 256)
$images = @()
foreach ($sz in $sizes) { $images += ,(New-IconPng $sz) }

# 预览图
[System.IO.File]::WriteAllBytes($previewPath, $images[-1])

$fs = [System.IO.File]::Create($icoPath)
$bw = New-Object System.IO.BinaryWriter $fs
$bw.Write([uint16]0)          # reserved
$bw.Write([uint16]1)          # type = icon
$bw.Write([uint16]$sizes.Count)

$offset = 6 + 16 * $sizes.Count
for ($i = 0; $i -lt $sizes.Count; $i++) {
    $sz = $sizes[$i]
    $data = $images[$i]
    $bw.Write([byte]($(if ($sz -ge 256) { 0 } else { $sz })))   # width
    $bw.Write([byte]($(if ($sz -ge 256) { 0 } else { $sz })))   # height
    $bw.Write([byte]0)        # colors
    $bw.Write([byte]0)        # reserved
    $bw.Write([uint16]1)      # planes
    $bw.Write([uint16]32)     # bpp
    $bw.Write([uint32]$data.Length)
    $bw.Write([uint32]$offset)
    $offset += $data.Length
}
foreach ($data in $images) { $bw.Write($data) }
$bw.Flush(); $bw.Dispose(); $fs.Dispose()

"图标已生成: $icoPath ($([math]::Round((Get-Item $icoPath).Length / 1KB, 1)) KB)"
"预览: $previewPath"
