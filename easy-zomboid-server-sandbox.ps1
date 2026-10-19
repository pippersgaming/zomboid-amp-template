param([string]$BaseDir, [string]$ServerName, [string]$Mode)

$dir = Join-Path $BaseDir 'Zomboid/Server'
$sandbox = Join-Path $dir "${ServerName}_SandboxVars.lua"
$amp = Join-Path $dir "${ServerName}_AMPSandbox.lua"
$last = Join-Path $dir "${ServerName}_AMPSandbox.last.lua"
$import = Join-Path $dir "${ServerName}_SandboxImport.ini"
$guard = Join-Path $dir "${ServerName}_AMPSandbox.guard.ini"
$importName = "${ServerName}_SandboxImport.ini"
$sandBin = Join-Path $BaseDir "Zomboid/Saves/Multiplayer/$ServerName/map_sand.bin"
if (Test-Path -LiteralPath $sandBin) { Write-Output "[Sandbox] Warning: this world has a map_sand.bin file in its save folder, which single player saves make. The game reads sandbox settings from that file instead of the sandbox file, so AMP's boxes and uploaded settings will not change this world. To switch to the sandbox file: make sure it holds the settings you want, stop the server, and rename map_sand.bin to map_sand.bin.old." }
if (-not (Test-Path -LiteralPath $sandbox)) { exit 0 }
if (-not (Test-Path -LiteralPath $amp)) { exit 0 }

$isWorld = @([IO.File]::ReadAllLines($sandbox) | Where-Object { $_ -match '^    ZombieLore = \{' }).Count -gt 0

function Clean-Value([string]$v) {
    if ($v.Length -ge 2 -and $v.StartsWith('"') -and $v.EndsWith('"')) {
        $v = $v.Substring(1, $v.Length - 2).Replace('\"', '"').Replace('\\', '\')
    } elseif ($v.Length -ge 8 -and $v.StartsWith('[==[') -and $v.EndsWith(']==]')) {
        $v = $v.Substring(4, $v.Length - 8)
    }
    return $v
}

function Write-Import {
    $known = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
    foreach ($x in [IO.File]::ReadAllLines($amp)) {
        if ($x -match '^SandboxVars\.(\w+)(?:\.(\w+))? = (?!SandboxVars)') {
            if ($Matches[2]) { [void]$known.Add("SV_$($Matches[1])_$($Matches[2])") } else { [void]$known.Add("SV_$($Matches[1])") }
        }
    }
    $values = New-Object System.Collections.Specialized.OrderedDictionary
    $table = ''
    foreach ($line in [IO.File]::ReadAllLines($sandbox)) {
        if ($line -match '^    (\w+) = \{\s*$') { $table = $Matches[1]; continue }
        if ($line -match '^    \},?\s*$') { $table = ''; continue }
        $key = $null
        if ($line -match '^SandboxVars\.(\w+)(?:\.(\w+))? = (?!SandboxVars)(.*?)\s*$') {
            if ($Matches[2]) { $key = "SV_$($Matches[1])_$($Matches[2])" } else { $key = "SV_$($Matches[1])" }
            $value = $Matches[3]
        }
        elseif ($table -eq '' -and $line -match '^    (\w+) = (.*?),\s*$') { $key = "SV_$($Matches[1])"; $value = $Matches[2] }
        elseif ($table -ne '' -and $line -match '^        (\w+) = (.*?),\s*$') { $key = "SV_${table}_$($Matches[1])"; $value = $Matches[2] }
        if ($key -and $known.Contains($key)) { $values[$key] = Clean-Value $value }
    }
    $out = New-Object 'System.Collections.Generic.List[string]'
    foreach ($k in $values.Keys) { $out.Add("$k=$($values[$k])") }
    [IO.File]::WriteAllLines($import, $out)
    [IO.File]::WriteAllLines($guard, $out)
}

if ($isWorld -and -not (Test-Path -LiteralPath $last)) {
    Copy-Item -LiteralPath $amp -Destination $last -Force
    Write-Import
    Write-Output "[Sandbox] Sandbox file from the game found (an existing world or uploaded settings), so its settings were kept and nothing from AMP was applied."
    Write-Output "[Sandbox] To show the world's settings in AMP: in the File Manager, right click Zomboid/Server/$importName and choose Import Configuration."
    exit 0
}

$ampLines = [IO.File]::ReadAllLines($amp)
if ($Mode -eq 'amp' -or -not (Test-Path -LiteralPath $last)) {
    $new = @($ampLines)
} else {
    $old = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
    foreach ($x in [IO.File]::ReadAllLines($last)) { [void]$old.Add($x) }
    $had = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
    if (Test-Path -LiteralPath $guard) { foreach ($x in [IO.File]::ReadAllLines($guard)) { [void]$had.Add($x) } }
    $new = @($ampLines | Where-Object {
        if ($old.Contains($_)) { return $false }
        if ($_ -match '^SandboxVars\.(\w+)(?:\.(\w+))? = (?!SandboxVars)(.*?)\s*$') {
            if ($Matches[2]) { $key = "SV_$($Matches[1])_$($Matches[2])" } else { $key = "SV_$($Matches[1])" }
            if ($had.Contains("$key=$(Clean-Value $Matches[3])")) { return $false }
        }
        return $true
    })
}
if ($new.Count -gt 0) {
    $nl = [Environment]::NewLine
    [IO.File]::AppendAllText($sandbox, $nl + ($new -join $nl) + $nl)
}
Copy-Item -LiteralPath $amp -Destination $last -Force
if ($isWorld) { Write-Import }
exit 0
