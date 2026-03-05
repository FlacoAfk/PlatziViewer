$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $python = $pythonCmd.Source
    } else {
        throw "No se encontró .venv\\Scripts\\python.exe ni el comando 'python' en PATH."
    }
}

# Validate runtime dependencies required by drive_service.py
$requiredImports = @(
    'requests',
    'google.oauth2.service_account',
    'googleapiclient.discovery',
    'google.auth.transport.requests'
)
$missingImports = @()
foreach ($mod in $requiredImports) {
    cmd /c """$python"" -c ""import $mod"" >NUL 2>NUL"
    if ($LASTEXITCODE -ne 0) {
        $missingImports += $mod
    }
}
if ($missingImports.Count -gt 0) {
    throw ("Faltan dependencias Python para el build: " + ($missingImports -join ', ') + ". Ejecuta: pip install -r requirements.txt")
}

$hasWebview = $false
cmd /c """$python"" -c ""import webview"" >NUL 2>NUL"
if ($LASTEXITCODE -eq 0) { $hasWebview = $true }

$hasPyQtWebEngine = $false
cmd /c """$python"" -c ""from PyQt6.QtWebEngineWidgets import QWebEngineView"" >NUL 2>NUL"
if ($LASTEXITCODE -eq 0) { $hasPyQtWebEngine = $true }

if (-not $hasWebview -and -not $hasPyQtWebEngine) {
    throw "Falta backend de UI para desktop_app.py. Instala pywebview o PyQt6 + PyQt6-WebEngine."
}

Write-Host "Limpiando builds anteriores..."
if (Test-Path "build") { Remove-Item "build" -Recurse -Force -ErrorAction SilentlyContinue }
if (Test-Path "dist/PlatziViewerDesktop.exe") { Remove-Item "dist/PlatziViewerDesktop.exe" -Force -ErrorAction SilentlyContinue }
if (Test-Path "PlatziViewerDesktop.spec") { Remove-Item "PlatziViewerDesktop.spec" -Force -ErrorAction SilentlyContinue }

$args = @(
    '-m', 'PyInstaller',
    '--noconfirm',
    '--clean',
    '--onefile',
    '--windowed',
    '--name', 'PlatziViewerDesktop',
    '--icon', 'favicon.ico',
    '--add-data', 'index.html;.',
    '--add-data', 'css;css',
    '--add-data', 'favicon.ico;.',
    '--add-data', 'favicon.svg;.',
    '--add-data', 'js;js',
    '--add-data', 'courses_cache.json;.',
    '--hidden-import', 'drive_service',
    '--hidden-import', 'google.oauth2.service_account',
    '--hidden-import', 'googleapiclient.discovery',
    '--hidden-import', 'google.auth.transport.requests',
    '--hidden-import', 'requests',
    'desktop_app.py'
)

if ($hasWebview) {
    $args += @(
        '--hidden-import', 'webview.platforms.edgechromium',
        '--hidden-import', 'webview.platforms.winforms',
        '--hidden-import', 'webview.platforms.cef'
    )
}

if ($hasPyQtWebEngine) {
    $args += @(
        '--hidden-import', 'PyQt6.QtWebEngineWidgets',
        '--hidden-import', 'PyQt6.QtWebEngineCore'
    )
}

if (Test-Path 'service_account.json') {
    $args += @('--add-data', 'service_account.json;.')
    Write-Host 'Incluyendo service_account.json dentro del exe.'
}

Write-Host "Compilando app de escritorio en un único .exe..."
& $python @args

Write-Host ""
Write-Host "[OK] Listo: dist/PlatziViewerDesktop.exe"
Write-Host "[INFO] Puedes ejecutar ese .exe directamente; abrirá ventana nativa de Windows (sin navegador)."

$signtool = $env:PLATZI_SIGNTOOL_PATH
$certPath = $env:PLATZI_CERT_PATH
$certPassword = $env:PLATZI_CERT_PASSWORD

if ($signtool -and $certPath -and (Test-Path $signtool) -and (Test-Path $certPath)) {
    Write-Host ""
    Write-Host "Firmando el ejecutable con certificado..."
    & $signtool sign /f $certPath /p $certPassword /tr "http://timestamp.digicert.com" /td SHA256 /fd SHA256 "dist/PlatziViewerDesktop.exe"
    Write-Host "[OK] Ejecutable firmado: dist/PlatziViewerDesktop.exe"
} else {
    Write-Host ""
    Write-Host "[INFO] Firma digital omitida (define PLATZI_SIGNTOOL_PATH, PLATZI_CERT_PATH y PLATZI_CERT_PASSWORD para firmar)."
}
