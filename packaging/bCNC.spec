# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for bCNC (onefile, Windows) -> single bCNC.exe.
# Build with:  pyinstaller packaging/bCNC.spec --noconfirm

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
root = os.path.abspath(".")

# Controllers are loaded at runtime via glob+__import__ (Sender.py). They ship
# as data .py files (see datas below) but we also list them as hidden imports
# so PyInstaller bundles any statically-referenced ones as a safety net.
CONTROLLERS = [
    "G2Core",
    "GRBL0",
    "GRBL1",
    "SMOOTHIE",
    "_GenericController",
    "_GenericGRBL",
]

# bCNC.lib submodules may be reached dynamically; collect them all.
LIB_SUBMODULES = []
lib_dir = os.path.join(root, "bCNC", "lib")
if os.path.isdir(lib_dir):
    try:
        LIB_SUBMODULES = collect_submodules("bCNC.lib")
    except Exception:
        LIB_SUBMODULES = []

datas = [
    # (source, dest_relative_to_bundle_root)
    # plugins/controllers are plain dirs of .py loaded by name at runtime.
    (os.path.join(root, "bCNC", "plugins"), "plugins"),
    (os.path.join(root, "bCNC", "controllers"), "controllers"),
    # icons/ and images/ are read by Utils.loadIcons() via prgpath globs.
    (os.path.join(root, "bCNC", "icons"), "icons"),
    (os.path.join(root, "bCNC", "images"), "images"),
    # Window icon (bmain.py: PhotoImage(file=prgpath/bCNC.png)) and the
    # system ini are read from prgpath root, so dest = bundle root.
    (os.path.join(root, "bCNC", "bCNC.png"), "."),
    (os.path.join(root, "bCNC", "bCNC.ini"), "."),
]

a = Analysis(
    [os.path.join(root, "packaging", "frozen_launcher.py")],
    pathex=[
        root,
        os.path.join(root, "bCNC"),
        lib_dir,  # so `import tkExtra` etc. resolve during analysis
    ],
    binaries=[],
    datas=datas,
    hiddenimports=(
        CONTROLLERS
        + LIB_SUBMODULES
        + [
            "tkinter",
            "tkinter.filedialog",
            "tkinter.font",
            "tkinter.messagebox",
            "tkinter.simpledialog",
            "tkinter.ttk",
            "queue",
            "shutil",
        ]
    ),
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # Test/dev-only deps; trimming these shrinks the bundle.
        "pytest",
        "pyautogui",
        "imageio",
        "requests",
        "tests",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

icon_path = os.path.join(root, "packaging", "bCNC.ico")
if not os.path.exists(icon_path):
    icon_path = None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,      # onefile: fold all binaries/data into the single exe
    a.zipfiles,
    a.datas,
    [],
    name="bCNC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,  # extract to system temp (%TEMP%), not beside the exe
    console=False,  # GUI app: no console window
    icon=icon_path,
)
