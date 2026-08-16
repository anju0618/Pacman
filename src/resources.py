"""
同梱リソース(画像・設定ファイル)の在り処を解決するモジュール。

ソースから直接実行する場合と、PyInstallerで1つの実行ファイルに
まとめた「パッケージ版」とでは、リソースの置き場所が変わる。

- ソース実行時: リポジトリのルート直下(このファイルの2つ上)。
- パッケージ実行時: PyInstallerが実行時に展開する一時ディレクトリ。
  そのパスは`sys._MEIPASS`に入る。

呼び出し側がこの違いを意識しなくて済むよう、リソース解決を
ここへ一本化する。
"""
from pathlib import Path
import sys


def is_frozen() -> bool:
    """PyInstallerでパッケージ化された実行ファイルとして動いているか。"""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def resource_root() -> Path:
    """同梱リソースを探す基準ディレクトリを返す。"""
    if is_frozen():
        # PyInstallerが展開した一時ディレクトリ。mypyは_MEIPASSを
        # 知らないのでgetattrで取り出す。
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[1]


def resource_path(*parts: str) -> Path:
    """基準ディレクトリからの相対パスを、実行形態に応じて解決する。

    Args:
        *parts: "assets", "sprites", "wall.png" のようなパス構成要素。

    Returns:
        実際に読み込めるフルパス。
    """
    return resource_root().joinpath(*parts)
