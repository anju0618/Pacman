# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: Pac-Manを単一実行ファイルにまとめる。

課題要件(VII)により、Steam / Itch.io のようなパブリックプラット
フォームから起動できるパッケージを作成し、そのパッケージング
スクリプト/specをリポジトリのルートに置く必要がある。

ビルド方法:
    make package          (推奨。依存関係の導入も含めて実行する)
    uv run pyinstaller pacman.spec --noconfirm

生成物:
    dist/pacman           起動可能な単一実行ファイル

同梱するもの:
    assets/sprites/*.png        ゲームの全グラフィック
    assets/sprites_horror/*.png --horror用のグロテスク版グラフィック
    config.json                 既定の設定ファイル(引数なし起動時に使う)
    INSTRUCTIONS.txt             操作方法・オプション・設定の説明
"""

block_cipher = None


analysis = Analysis(
    ['pac-man.py'],
    pathex=[],
    binaries=[],
    # (コピー元, 展開先ディレクトリ) の組。実行時はsys._MEIPASS以下に
    # この構造で展開され、src/resources.pyがそのパスを解決する。
    datas=[
        ('assets/sprites', 'assets/sprites'),
        ('assets/sprites_horror', 'assets/sprites_horror'),
        ('config.json', '.'),
        ('INSTRUCTIONS.txt', '.'),
    ],
    hiddenimports=['mazegenerator'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'mypy', 'flake8'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)

executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    [],
    name='pacman',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    # ゲームなのでコンソールウィンドウは出さない。エラーは
    # Display側で画面/標準出力へ出す。
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
