param([string]$Python = 'python', [string]$Version = '0.2.2')
$ErrorActionPreference = 'Stop'
if ($Version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+$') { throw 'Version must be numeric major.minor.patch' }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$destination = "dist/$Version-$stamp"
$work = "build/$Version-$stamp"
if (Test-Path -LiteralPath $destination) { throw 'Output already exists; retry with a new timestamp' }
$whitelistData = (Join-Path (Get-Location) 'app/default_whitelist.json') + ';app'
$ocrData = (Join-Path (Get-Location) 'scripts/ocr.ps1') + ';scripts'
$workerData = (Join-Path (Get-Location) 'scripts/ocr_worker.ps1') + ';scripts'
& $Python -m PyInstaller --noconfirm --windowed --onedir --name MabinogiAssistant --distpath $destination --workpath $work --specpath $work --add-data $whitelistData --add-data $ocrData --add-data $workerData --exclude-module pandas --exclude-module scipy --exclude-module matplotlib --exclude-module IPython --exclude-module pytest main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
Copy-Item README.md,AGENTS.md,VALIDATION.md "$destination/MabinogiAssistant/"
$zip = "dist/MabinogiAssistant-$Version-$stamp.zip"
Compress-Archive -Path "$destination/MabinogiAssistant" -DestinationPath $zip
Write-Output $zip
