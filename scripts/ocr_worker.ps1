# One local OCR engine per scan. Requests/results are JSON lines over standard I/O.
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$init = [Diagnostics.Stopwatch]::StartNew()
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
    $null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation,ContentType=WindowsRuntime]
    $null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
    $null = [Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime]
    $asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
    function Await($operation, $type) {
        $task = $asTask.MakeGenericMethod($type).Invoke($null, @($operation))
        if (-not $task.Wait(10000)) { throw 'Windows OCR operation timed out' }
        $task.Result
    }
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('zh-Hant-TW'))
    if ($null -eq $engine) { throw 'Install Windows Traditional Chinese OCR support (zh-Hant-TW).' }
    [Console]::WriteLine((@{ready=$true; init_ms=$init.Elapsed.TotalMilliseconds} | ConvertTo-Json -Compress))
    while ($null -ne ($line = [Console]::ReadLine())) {
        $request = ConvertFrom-Json $line
        if ($request.stop) { break }
        if (@($request.paths).Count -gt 12 -or @($request.paths).Count -lt 1) { throw 'Invalid OCR batch size' }
        $items = @()
        foreach ($path in $request.paths) {
            $clock = [Diagnostics.Stopwatch]::StartNew()
            $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync([string]$path)) ([Windows.Storage.StorageFile])
            $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
            try {
                $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
                $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
                try {
                    $decodeMs = $clock.Elapsed.TotalMilliseconds
                    $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
                    $recognitionMs = $clock.Elapsed.TotalMilliseconds - $decodeMs
                    $words = @($result.Lines | ForEach-Object { $_.Words | ForEach-Object {
                        @{text=$_.Text; x=$_.BoundingRect.X; y=$_.BoundingRect.Y; w=$_.BoundingRect.Width; h=$_.BoundingRect.Height}
                    } })
                    $items += @{words=$words; decode_ms=$decodeMs; recognition_ms=$recognitionMs}
                } finally { $bitmap.Dispose() }
            } finally { $stream.Dispose() }
        }
        [Console]::WriteLine((@{items=$items} | ConvertTo-Json -Depth 6 -Compress))
    }
} catch {
    [Console]::WriteLine((@{error=$_.Exception.Message} | ConvertTo-Json -Compress))
    exit 1
}
