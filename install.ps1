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
$destination = & $python (Join-Path $source 'project_tools.py') install --source $source --prefix $Prefix --layout windows
if ($LASTEXITCODE -ne 0) { throw 'T+ installation failed. Re-run the installer to recover any interrupted transaction.' }
if (-not $NoPath) {
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($null -eq $userPath) { $userPath = '' }
    if (-not (($userPath -split ';') -contains $bin)) {
        $newPath = ($userPath.TrimEnd(';') + ';' + $bin).TrimStart(';')
        [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    }
    $env:Path = $bin + ';' + $env:Path
}
Write-Host "T+ installed in $destination"
Write-Host 'Open a new Terminal, then run: teka --version'
if (-not (Get-Command g++ -ErrorAction SilentlyContinue) -and -not (Get-Command clang++ -ErrorAction SilentlyContinue)) {
    Write-Host 'A C++17 compiler is needed to run and build programs. See the Windows compiler setup in README.md.'
}
