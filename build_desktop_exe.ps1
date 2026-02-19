$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$python = "H:/Mi unidad/platzi-viewer/.venv/Scripts/python.exe"
if (-not (Test-Path $python)) {
    throw "No se encontró el entorno virtual en .venv."
}

Write-Host "Limpiando builds anteriores..."
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist/PlatziViewerDesktop.exe") { Remove-Item "dist/PlatziViewerDesktop.exe" -Force }
if (Test-Path "PlatziViewerDesktop.spec") { Remove-Item "PlatziViewerDesktop.spec" -Force }

$args = @(
    '-m', 'PyInstaller',
    '--noconfirm',
    '--clean',
    '--onefile',
    '--windowed',
    '--name', 'PlatziViewerDesktop',
    '--icon', 'favicon.ico',
    '--add-data', 'index.html;.',
    '--add-data', 'styles.css;.',
    '--add-data', 'favicon.ico;.',
    '--add-data', 'favicon.svg;.',
    '--add-data', 'js;js',
    '--add-data', 'courses_cache.json;.',
    '--hidden-import', 'webview.platforms.edgechromium',
    '--hidden-import', 'webview.platforms.winforms',
    '--hidden-import', 'webview.platforms.cef',
    'desktop_app.py'
)

if (Test-Path 'service_account.json') {
    $args += @('--add-data', 'service_account.json;.')
    Write-Host 'Incluyendo service_account.json dentro del exe.'
}

Write-Host "Compilando app de escritorio en un único .exe..."
& $python @args

Write-Host ""
Write-Host "✅ Listo: dist/PlatziViewerDesktop.exe"
Write-Host "ℹ️ Puedes ejecutar ese .exe directamente; abrirá ventana nativa de Windows (sin navegador)."

$signtool = $env:PLATZI_SIGNTOOL_PATH
$certPath = $env:PLATZI_CERT_PATH
$certPassword = $env:PLATZI_CERT_PASSWORD

if ($signtool -and $certPath -and (Test-Path $signtool) -and (Test-Path $certPath)) {
    Write-Host ""
    Write-Host "Firmando el ejecutable con certificado..."
    & $signtool sign /f $certPath /p $certPassword /tr "http://timestamp.digicert.com" /td SHA256 /fd SHA256 "dist/PlatziViewerDesktop.exe"
    Write-Host "✅ Ejecutable firmado: dist/PlatziViewerDesktop.exe"
} else {
    Write-Host ""
    Write-Host "ℹ️ Firma digital omitida (define PLATZI_SIGNTOOL_PATH, PLATZI_CERT_PATH y PLATZI_CERT_PASSWORD para firmar)."
}
