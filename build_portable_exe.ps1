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

Write-Host "Limpiando builds anteriores..."
if (Test-Path "build") { Remove-Item "build" -Recurse -Force -ErrorAction SilentlyContinue }
if (Test-Path "dist/PlatziViewer") { Remove-Item "dist/PlatziViewer" -Recurse -Force -ErrorAction SilentlyContinue }
if (Test-Path "PlatziViewer.spec") { Remove-Item "PlatziViewer.spec" -Force -ErrorAction SilentlyContinue }

Write-Host "Compilando .exe portable con icono..."
& $python -m PyInstaller `
  --noconfirm `
  --clean `
  --onedir `
  --name "PlatziViewer" `
  --icon "favicon.ico" `
  --hidden-import "drive_service" `
  --hidden-import "google.oauth2.service_account" `
  --hidden-import "googleapiclient.discovery" `
  --hidden-import "google.auth.transport.requests" `
  --hidden-import "requests" `
  "app_launcher.py"

$distDir = Join-Path $projectRoot "dist/PlatziViewer"

Write-Host "Copiando recursos web y datos..."
Copy-Item "index.html" $distDir -Force
Copy-Item "css" $distDir -Recurse -Force
Copy-Item "favicon.ico" $distDir -Force
Copy-Item "favicon.svg" $distDir -Force
Copy-Item "js" $distDir -Recurse -Force

if (Test-Path "courses_cache.json") { Copy-Item "courses_cache.json" $distDir -Force }
if (Test-Path "progress.json") { Copy-Item "progress.json" $distDir -Force }
if (Test-Path ".env") { Copy-Item ".env" $distDir -Force }
if (Test-Path "service_account.json") {
  Copy-Item "service_account.json" $distDir -Force
  Write-Host "Incluyendo service_account.json en el portable."
} else {
  Write-Host "[WARN] No se encontró service_account.json. El portable no podrá leer Drive hasta que lo agregues."
}

Write-Host ""
Write-Host "[OK] Listo. Ejecutable portable en: dist/PlatziViewer/PlatziViewer.exe"
Write-Host "[INFO] El ejecutable incluye backend + frontend. Inicia todo al abrir PlatziViewer.exe."
