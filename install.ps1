param([string]$Prefix = (Join-Path $env:LOCALAPPDATA 'TPlus'), [string]$SourceDir = $PSScriptRoot, [switch]$NoPath)
$ErrorActionPreference = 'Stop'
$source = $SourceDir
$Prefix = [IO.Path]::GetFullPath($Prefix)
$python = $null
foreach ($candidate in @('python', 'python3', 'py')) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $probe = & $candidate -c "import sys; print(sys.executable); sys.exit(sys.version_info < (3,11))" 2>$null
        if ($LASTEXITCODE -eq 0) { $python = [string]($probe | Select-Object -Last 1); break }
    }
}
if (-not $python) { throw 'Install Python 3.11 or newer from https://www.python.org/downloads/windows/ and try again.' }
$bin = Join-Path $Prefix 'bin'
$launcher = Join-Path $bin 'teka.cmd'
$required = @('teka.py','python_style.py','standard_modules.py','project_tools.py','updater.py','TPLUS_HANDBOOK.md')
foreach ($name in $required) {
    if (-not (Test-Path (Join-Path $source $name) -PathType Leaf)) { throw "Incomplete T+ folder: missing $name" }
}
$version = & $python -c 'import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); from updater import current_version; print(current_version(Path(sys.argv[1])))' $source
if ($LASTEXITCODE -ne 0 -or $version -notmatch '^\d+\.\d+\.\d+$') { throw 'Cannot determine compiler version. Nothing was installed.' }
$destination = Join-Path $Prefix $version
$installed = @($required + @('install.ps1','README.md','LICENSE','PRIVACY.md') | Where-Object { Test-Path (Join-Path $source $_) -PathType Leaf })
$owned = @($installed + @('launcher.py','launcher.json','.tplus-install'))
& $python (Join-Path $source 'project_tools.py') preflight --root $destination --layout windows --files $owned
if ($LASTEXITCODE -ne 0) { throw 'Installation preflight failed. Existing files were not changed.' }
if ((Test-Path $destination) -and -not (Test-Path (Join-Path $destination '.tplus-install'))) {
    throw "$destination is not marked as a T+ installation. Choose another -Prefix."
}
if ((Test-Path $launcher) -and -not ((Get-Content $launcher -Raw) -match 'TPlus launcher')) {
    throw "Another command already exists at $launcher. Choose another -Prefix."
}
New-Item -ItemType Directory -Force -Path $destination, $bin | Out-Null
foreach ($name in $installed) {
    $file = Join-Path $source $name
    if ((Test-Path $file) -and ([IO.Path]::GetFullPath($file) -ne [IO.Path]::GetFullPath((Join-Path $destination $name)))) {
        Copy-Item $file (Join-Path $destination $name) -Force
    }
}
$utf8 = New-Object Text.UTF8Encoding($false)
$entry = Join-Path $destination 'launcher.py'
$code = @'
from pathlib import Path
import json
import runpy
import sys
root = Path(__file__).resolve().parent
args = sys.argv[1:]
target = "teka.py"
if args and args[0] == "update":
    target = "updater.py"
    args = args[1:]
sys.path.insert(0, str(root))
sys.argv = [str(root / target)] + args
runpy.run_path(str(root / target), run_name="__main__")
'@
[IO.File]::WriteAllText($entry, $code, $utf8)
$q = [char]34
$nl = [Environment]::NewLine
$batch = '@echo off' + $nl + 'rem TPlus launcher' + $nl + $q + $python.Replace('%','%%') + $q + ' ' + $q + $entry.Replace('%','%%') + $q + ' %*' + $nl
[IO.File]::WriteAllText($launcher, $batch, $utf8)
[IO.File]::WriteAllText((Join-Path $destination '.tplus-install'), "T+ $version", $utf8)
$manifest = @{ python = $python; launcher = $entry } | ConvertTo-Json
[IO.File]::WriteAllText((Join-Path $destination 'launcher.json'), $manifest, $utf8)
# A stable location lets editor tooling follow the selected version.
[IO.File]::WriteAllText((Join-Path $bin 'launcher.json'), $manifest, $utf8)
& $python (Join-Path $source 'project_tools.py') record --root $destination --layout windows --files $owned
if ($LASTEXITCODE -ne 0) { throw 'Could not record installation ownership. Installation may be incomplete.' }
if (-not $NoPath) {
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($null -eq $userPath) { $userPath = '' }
    if (-not (($userPath -split ';') -contains $bin)) {
        $newPath = ($userPath.TrimEnd(';') + ';' + $bin).TrimStart(';')
        [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    }
    $env:Path = $bin + ';' + $env:Path
}
Write-Host "T+ $version installed in $destination"
Write-Host 'Open a new Terminal, then run: teka --version'
if (-not (Get-Command g++ -ErrorAction SilentlyContinue) -and -not (Get-Command clang++ -ErrorAction SilentlyContinue)) {
    Write-Host 'A C++17 compiler is needed to run and build programs. See the Windows compiler setup in README.md.'
}
