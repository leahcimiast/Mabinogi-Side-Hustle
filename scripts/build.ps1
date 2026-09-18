param([string]$Python = 'python', [string]$Version = '')
$ErrorActionPreference = 'Stop'
if ($Version -and $Version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+$') { throw 'Version must be numeric major.minor.patch' }
$sourceVersion = & $Python -c 'from app.version import APP_VERSION; print(APP_VERSION)'
if ($LASTEXITCODE -ne 0) { throw 'Cannot read app version' }
if (-not $Version) { $Version = $sourceVersion }
if ($Version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+$') { throw 'Source version must be numeric major.minor.patch' }
if ($Version -ne $sourceVersion) { throw 'Build version must match app/version.py' }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$destination = "dist/$Version-$stamp"
$work = "build/$Version-$stamp"
if (Test-Path -LiteralPath $destination) { throw 'Output already exists; retry with a new timestamp' }
New-Item -ItemType Directory -Path $work | Out-Null
$versionTuple = ($Version -replace '\.', ',') + ',0'
$versionFile = Join-Path (Join-Path (Get-Location) $work) 'version_info.txt'
@"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($versionTuple), prodvers=($versionTuple), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0,0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('FileDescription', 'Mabinogi Mobile Quest Assistant'),
    StringStruct('FileVersion', '$Version'),
    StringStruct('ProductName', 'MabinogiAssistant'),
    StringStruct('ProductVersion', '$Version'),
    StringStruct('OriginalFilename', 'MabinogiAssistant.exe')
  ])]), VarFileInfo([VarStruct('Translation', [1033,1200])])]
)
"@ | Set-Content -LiteralPath $versionFile -Encoding UTF8
$whitelistData = (Join-Path (Get-Location) 'app/default_whitelist.json') + ';app'
$ocrData = (Join-Path (Get-Location) 'scripts/ocr.ps1') + ';scripts'
$workerData = (Join-Path (Get-Location) 'scripts/ocr_worker.ps1') + ';scripts'
$iconPath = Join-Path (Get-Location) 'assets/app.ico'
$iconData = $iconPath + ';assets'
& $Python -m PyInstaller --noconfirm --windowed --onefile --name MabinogiAssistant --distpath "$destination/MabinogiAssistant" --workpath $work --specpath $work --add-data $whitelistData --add-data $ocrData --add-data $workerData --add-data $iconData --icon $iconPath --version-file $versionFile --exclude-module pandas --exclude-module scipy --exclude-module matplotlib --exclude-module IPython --exclude-module pytest main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
Copy-Item README.md,CHANGELOG.md "$destination/MabinogiAssistant/"
$zip = "dist/MabinogiAssistant-$Version-single-exe-$stamp.zip"
Compress-Archive -Path "$destination/MabinogiAssistant" -DestinationPath $zip
$checksum = "$zip.sha256"
$hash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $(Split-Path -Leaf $zip)" | Set-Content -LiteralPath $checksum -Encoding ASCII
Write-Output $zip
Write-Output $checksum
