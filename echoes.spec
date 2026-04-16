# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Echoes of the Terminal 단일 실행 파일 빌드."""

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("scenarios.json", "."),
        ("argos_taunts.json", "."),
        ("boss_phase_pack.json", "."),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="EchoesOfTheTerminal",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
