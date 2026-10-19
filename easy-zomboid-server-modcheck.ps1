param([string]$BaseDir, [string]$ServerName)

$ini = Join-Path $BaseDir "Zomboid/Server/$ServerName.ini"
if (-not (Test-Path -LiteralPath $ini)) { exit 0 }

function Split-List([string]$text) {
    @($text.Replace('\', '').Split(';') | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
}

$mods = @(); $items = @()
foreach ($line in [IO.File]::ReadAllLines($ini)) {
    if ($line.StartsWith('Mods=')) { $mods = Split-List $line.Substring(5) }
    if ($line.StartsWith('WorkshopItems=')) { $items = Split-List $line.Substring(14) }
}

$content = Join-Path $BaseDir 'steamapps/workshop/content/108600'
$allIds = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
$wanted = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
foreach ($m in $mods) { [void]$wanted.Add($m) }
$notDownloaded = @()
$warnings = @()

foreach ($item in $items) {
    $dir = Join-Path $content $item
    if (-not (Test-Path -LiteralPath $dir)) { $notDownloaded += $item; continue }
    $infos = @(Get-ChildItem -LiteralPath (Join-Path $dir 'mods') -Directory -ErrorAction SilentlyContinue |
        ForEach-Object { Get-ChildItem -LiteralPath $_.FullName -Directory -ErrorAction SilentlyContinue } |
        Where-Object { $_.Name -eq 'common' -or $_.Name -match '^42(\..*)?$' } |
        ForEach-Object { Join-Path $_.FullName 'mod.info' } | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
    $ids = @($infos | ForEach-Object { [Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($_)) -split "`r?`n" } |
        Where-Object { $_ -cmatch '^id=(.+)$' } | ForEach-Object { $Matches[1].Trim() } | Where-Object { $_ -ne '' } | Sort-Object -Unique)
    foreach ($id in $ids) { [void]$allIds.Add($id) }
    if ($ids.Count -gt 0 -and -not ($ids | Where-Object { $wanted.Contains($_) })) {
        $warnings += "Workshop item $item is listed, but none of its mods are in Mods. Its mod IDs: $($ids -join ', ')."
    }
}

foreach ($m in $mods) {
    if (-not $allIds.Contains($m)) {
        if ($notDownloaded.Count -gt 0) {
            $warnings += "Mod ID '$m' was not found in the downloaded Workshop items. It may be in one not downloaded yet."
        } else {
            $warnings += "Mod ID '$m' is not in any listed Workshop item. Check its Workshop number is in Workshop items and the ID is spelled exactly as on its Workshop page."
        }
    }
}

Write-Output "[Mod check] $($mods.Count) mod IDs and $($items.Count) Workshop items listed."
if ($notDownloaded.Count -gt 0) {
    Write-Output "[Mod check] Not downloaded yet, normal before the first start with them: $($notDownloaded -join ', ')."
}
if ($warnings.Count -eq 0) {
    Write-Output '[Mod check] Mods and Workshop items match.'
} else {
    foreach ($w in $warnings) { Write-Output "[Mod check] $w" }
}
exit 0
