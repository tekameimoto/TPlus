$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$temp = Join-Path ([IO.Path]::GetTempPath()) ('teka-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $temp | Out-Null
try {
    $release = 'https://github.com/tekameimoto/TPlus/releases/download/v0.9.0'
    Write-Host 'Downloading T+ 0.9.0...'
    $zip = Join-Path $temp 'TPlus-v0.9.0.zip'
    Invoke-WebRequest -UseBasicParsing "$release/TPlus-v0.9.0.zip" -OutFile $zip
    Invoke-WebRequest -UseBasicParsing "$release/SHA256SUMS.txt" -OutFile (Join-Path $temp 'SHA256SUMS.txt')
    $lines = @(Get-Content (Join-Path $temp 'SHA256SUMS.txt') | Where-Object { $_ -match '^([0-9a-fA-F]{64})\s+\*?TPlus-v0\.9\.0\.zip$' })
    if ($lines.Count -ne 1) { throw 'Release checksum is missing or ambiguous. Nothing was installed.' }
    $expected = ($lines[0] -split '\s+')[0]
    if ((Get-FileHash $zip -Algorithm SHA256).Hash -ne $expected) { throw 'Release checksum did not match. Nothing was installed.' }
    Expand-Archive -Path $zip -DestinationPath $temp
    $installer = Join-Path $temp 'compiler/install.ps1'
    if (-not (Test-Path $installer)) { throw 'This release does not contain the Windows installer.' }
    & ([scriptblock]::Create([IO.File]::ReadAllText($installer))) -SourceDir (Split-Path $installer)
} finally {
    Remove-Item $temp -Recurse -Force
}
