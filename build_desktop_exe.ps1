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

$pyargs = @(
    '-m', 'PyInstaller',
    '--noconfirm',
    '--clean',
    '--onefile',
    '--noupx',
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
    $pyargs += @(
        '--hidden-import', 'webview.platforms.edgechromium',
        '--hidden-import', 'webview.platforms.winforms',
        '--hidden-import', 'webview.platforms.cef'
    )
}

if ($hasPyQtWebEngine) {
    $pyargs += @(
        '--hidden-import', 'PyQt6.QtWebEngineWidgets',
        '--hidden-import', 'PyQt6.QtWebEngineCore'
    )
}

if (Test-Path 'service_account.json') {
    $pyargs += @('--add-data', 'service_account.json;.')
    Write-Host 'Incluyendo service_account.json dentro del exe.'
}

# --- FFmpeg bundling for AV sync fix ---
$ffmpegPath = $null
if ($env:FFMPEG_PATH -and (Test-Path $env:FFMPEG_PATH)) {
    $ffmpegPath = $env:FFMPEG_PATH
}
if (-not $ffmpegPath) {
    $ffmpegCmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($ffmpegCmd) { $ffmpegPath = $ffmpegCmd.Source }
}
if (-not $ffmpegPath) {
    @('C:\Ffmpeg\bin\ffmpeg.exe', 'C:\ffmpeg\bin\ffmpeg.exe', 'C:\Program Files\ffmpeg\bin\ffmpeg.exe') | ForEach-Object {
        if (-not $ffmpegPath -and (Test-Path $_)) { $ffmpegPath = $_ }
    }
}
if ($ffmpegPath) {
    $pyargs += @('--add-binary', "$ffmpegPath;.")
    Write-Host "Incluyendo ffmpeg en el exe: $ffmpegPath"
} else {
    Write-Host '[WARN] ffmpeg.exe no encontrado. El fix de sync A/V no funcionara en el .exe.'
    Write-Host '       Instala ffmpeg o define FFMPEG_PATH para incluirlo.'
}

Write-Host "Compilando app de escritorio en un unico .exe..."

& $python @pyargs

Write-Host ""
Write-Host "[OK] Listo: dist/PlatziViewerDesktop.exe"
Write-Host "[INFO] Puedes ejecutar ese .exe directamente; abrirá ventana nativa de Windows (sin navegador)."

function Resolve-SignToolPath {
    param([string]$PreferredPath)

    if ($PreferredPath -and (Test-Path $PreferredPath)) {
        return (Resolve-Path $PreferredPath).Path
    }

    $byCommand = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($byCommand -and $byCommand.Source -and (Test-Path $byCommand.Source)) {
        return $byCommand.Source
    }

    $windowsKitRoots = @(
        "$env:ProgramFiles(x86)\Windows Kits\10\bin",
        "$env:ProgramFiles\Windows Kits\10\bin"
    )

    foreach ($root in $windowsKitRoots) {
        if (-not (Test-Path $root)) { continue }
        $candidate = Get-ChildItem -Path $root -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($candidate) {
            return $candidate.FullName
        }
    }

    return $null
}

function Build-SignArgs {
    param(
        [string]$CertPath,
        [string]$CertPassword,
        [string]$CertThumbprint,
        [string]$CertStore,
        [string]$CertStoreLocation,
        [string]$TimestampUrl,
        [string]$TargetExe
    )

    $timestamp = if ($TimestampUrl) { $TimestampUrl } else { 'http://timestamp.digicert.com' }
    $args = @('sign', '/tr', $timestamp, '/td', 'SHA256', '/fd', 'SHA256')

    if ($CertPath) {
        $args += @('/f', $CertPath)
        if ($CertPassword) {
            $args += @('/p', $CertPassword)
        }
    } elseif ($CertThumbprint) {
        $normalizedThumbprint = ($CertThumbprint -replace '\s+', '').ToUpperInvariant()
        $storeName = if ($CertStore) { $CertStore } else { 'My' }
        $location = if ($CertStoreLocation) { $CertStoreLocation } else { 'CurrentUser' }
        $storePath = "Cert:\$location\$storeName\$normalizedThumbprint"
        if (-not (Test-Path $storePath)) {
            Write-Warning "No se encontró el certificado en $storePath. Se omitirá la firma."
            return $null
        }

        $args += @('/sha1', $normalizedThumbprint, '/s', $storeName)
        if ($location -eq 'LocalMachine') {
            $args += @('/sm')
        }
    } else {
        return $null
    }

    $args += @($TargetExe)
    return $args
}

$targetExe = Join-Path $projectRoot 'dist\PlatziViewerDesktop.exe'
$signtool = Resolve-SignToolPath -PreferredPath $env:PLATZI_SIGNTOOL_PATH
$certPath = $env:PLATZI_CERT_PATH
$certPassword = $env:PLATZI_CERT_PASSWORD
$certThumbprint = $env:PLATZI_CERT_THUMBPRINT
$certStore = $env:PLATZI_CERT_STORE
$certStoreLocation = $env:PLATZI_CERT_STORE_LOCATION
$timestampUrl = $env:PLATZI_TIMESTAMP_URL

$signArgs = Build-SignArgs -CertPath $certPath -CertPassword $certPassword -CertThumbprint $certThumbprint -CertStore $certStore -CertStoreLocation $certStoreLocation -TimestampUrl $timestampUrl -TargetExe $targetExe

if ($signtool -and $signArgs) {
    Write-Host ""
    Write-Host "Firmando el ejecutable con certificado..."
    & $signtool @signArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Falló la firma del ejecutable (exit code: $LASTEXITCODE)."
    }

    & $signtool verify /pa /v $targetExe | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "La verificación de firma falló (exit code: $LASTEXITCODE)."
    }

    Write-Host "[OK] Ejecutable firmado y verificado: dist/PlatziViewerDesktop.exe"
} else {
    Write-Host ""
    if (-not $signtool) {
        Write-Host "[INFO] Firma digital omitida: no se encontró signtool.exe."
        Write-Host "       Instala Windows SDK o define PLATZI_SIGNTOOL_PATH."
    } else {
        Write-Host "[INFO] Firma digital omitida: faltan credenciales de certificado válidas."
    }
    Write-Host ""
    Write-Host "Para firmar con archivo .pfx:"
    Write-Host "  `$env:PLATZI_CERT_PATH='C:\ruta\certificado.pfx'"
    Write-Host "  `$env:PLATZI_CERT_PASSWORD='tu_password'"
    Write-Host ""
    Write-Host "Para firmar con certificado instalado en Windows (recomendado):"
    Write-Host "  `$env:PLATZI_CERT_THUMBPRINT='ABCDEF1234567890...'"
    Write-Host "  `$env:PLATZI_CERT_STORE='My'                  # opcional"
    Write-Host "  `$env:PLATZI_CERT_STORE_LOCATION='CurrentUser' # opcional"
}
