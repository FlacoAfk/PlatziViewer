# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['desktop_app.py'],
    pathex=[],
    binaries=[('C:\\Ffmpeg\\bin\\ffmpeg.exe', '.')],
    datas=[('index.html', '.'), ('css', 'css'), ('favicon.ico', '.'), ('favicon.svg', '.'), ('js', 'js'), ('courses_cache.json', '.'), ('service_account.json', '.')],
    hiddenimports=['drive_service', 'google.oauth2.service_account', 'googleapiclient.discovery', 'google.auth.transport.requests', 'requests', 'webview.platforms.edgechromium', 'webview.platforms.winforms', 'webview.platforms.cef'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PlatziViewerDesktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['favicon.ico'],
)
