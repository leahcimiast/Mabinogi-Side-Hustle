param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
& $Python -m PyInstaller --noconfirm --clean --windowed --onedir --name MabinogiAssistant --add-data 'app/default_whitelist.json;app' --add-data 'scripts/ocr.ps1;scripts' --exclude-module pandas --exclude-module scipy --exclude-module matplotlib --exclude-module IPython --exclude-module pytest main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
Copy-Item README.md,AGENTS.md,VALIDATION.md dist/MabinogiAssistant/
$zip = 'dist/MabinogiAssistant-milestone1-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.zip'
Compress-Archive -Path dist/MabinogiAssistant -DestinationPath $zip
Write-Output $zip
