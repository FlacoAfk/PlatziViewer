$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$python = "H:/Mi unidad/platzi-viewer/.venv/Scripts/python.exe"
if (-not (Test-Path $python)) {
    throw "No se encontró el entorno virtual en .venv."
}

Write-Host "Limpiando builds anteriores..."
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist/PlatziViewer") { Remove-Item "dist/PlatziViewer" -Recurse -Force }
if (Test-Path "PlatziViewer.spec") { Remove-Item "PlatziViewer.spec" -Force }

Write-Host "Compilando .exe portable con icono..."
& $python -m PyInstaller `
  --noconfirm `
  --clean `
  --onedir `
  --name "PlatziViewer" `
  --icon "favicon.ico" `
  "app_launcher.py"

$distDir = Join-Path $projectRoot "dist/PlatziViewer"

Write-Host "Copiando recursos web y datos..."
Copy-Item "index.html" $distDir -Force
Copy-Item "styles.css" $distDir -Force
Copy-Item "favicon.ico" $distDir -Force
Copy-Item "favicon.svg" $distDir -Force
Copy-Item "js" $distDir -Recurse -Force

if (Test-Path "courses_cache.json") { Copy-Item "courses_cache.json" $distDir -Force }
if (Test-Path "progress.json") { Copy-Item "progress.json" $distDir -Force }
if (Test-Path ".env") { Copy-Item ".env" $distDir -Force }

Write-Host ""
Write-Host "✅ Listo. Ejecutable portable en: dist/PlatziViewer/PlatziViewer.exe"
Write-Host "ℹ️ Si no existe service_account.json dentro de dist/PlatziViewer, copia uno allí antes de ejecutar."
