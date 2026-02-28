param()

$ErrorActionPreference = 'Stop'
Write-Host 'Looking up latest UB-Mannheim Tesseract release...'
$repo = 'UB-Mannheim/tesseract'
$apiUrl = "https://api.github.com/repos/$repo/releases/latest"
try {
    $release = Invoke-RestMethod -Headers @{ 'User-Agent' = 'powershell' } -Uri $apiUrl
} catch {
    Write-Error "Failed to query GitHub API: $_"
    exit 1
}

$asset = $release.assets | Where-Object { $_.name -match 'w64.*setup.*\.exe$' } | Select-Object -First 1
if (-not $asset) { $asset = $release.assets | Where-Object { $_.name -match 'setup.*\.exe$' } | Select-Object -First 1 }
if (-not $asset) { Write-Error 'No Windows installer asset found in latest release'; exit 1 }

$out = Join-Path $env:TEMP $asset.name
if (Test-Path $out) { Remove-Item $out -Force }

Write-Host "Downloading $($asset.name) to $out..."
try {
    Invoke-RestMethod -Headers @{ 'User-Agent' = 'powershell' } -Uri $asset.browser_download_url -OutFile $out
} catch {
    Write-Host 'Invoke-RestMethod failed, falling back to WebClient...'
    try {
        $wc = New-Object System.Net.WebClient
        $wc.Headers.Add('User-Agent','powershell')
        $wc.DownloadFile($asset.browser_download_url, $out)
    } catch {
        Write-Error "Download failed: $_"
        exit 1
    }
}

Write-Host 'Download complete - launching installer (UAC prompt expected)...'
Start-Process -FilePath $out -Verb RunAs
