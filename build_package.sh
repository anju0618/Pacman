#!/bin/sh
# Pac-Manを配布用の単一実行ファイルにビルドするスクリプト。
#
# 課題要件(VII)により、パッケージングスクリプトはリポジトリの
# ルートに置く必要がある。ピアレビュー中にパッケージの再生成を
# 求められる可能性があるため、このスクリプト1本で完結させる。
#
# 使い方:
#     ./build_package.sh
#     make package        (同じことをMakefile経由で行う)
#
# 生成物:
#     dist/pacman         起動可能な単一実行ファイル
#
# 生成した実行ファイルは、Itch.io であれば dist/pacman を zip に
# まとめてアップロードすれば配布できる(Steamの場合はSteamworks
# のビルドへ同じ実行ファイルを登録する)。

set -eu

echo "==> Installing build dependencies (PyInstaller)"
uv sync --group package

echo "==> Building the standalone executable"
uv run pyinstaller pacman.spec --noconfirm --clean

echo ""
echo "==> Done. The packaged game is at: dist/pacman"
echo "    Run it with:            ./dist/pacman"
echo "    Run it in cheat mode:   ./dist/pacman --cheat"
