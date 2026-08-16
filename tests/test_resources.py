import sys
from pathlib import Path

import pytest

from src.resources import is_frozen, resource_path, resource_root


def test_source_checkout_resolves_to_the_repository_root() -> None:
    """ソースから実行している間は、リポジトリ直下を基準にする。"""
    assert not is_frozen()

    root = resource_root()
    assert (root / "assets" / "sprites").is_dir()
    assert (root / "pac-man.py").is_file()


def test_resource_path_joins_parts_under_the_root() -> None:
    assert resource_path("assets", "sprites") == (
        resource_root() / "assets" / "sprites"
    )


def test_frozen_build_resolves_to_the_pyinstaller_extraction_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """PyInstallerでパッケージ化された実行時は、展開先を基準にする。

    パッケージ版では実行ファイル内のリソースが`sys._MEIPASS`へ
    展開されるため、そちらを見に行かないと画像も設定も読めない。
    """
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert is_frozen()
    assert resource_root() == tmp_path
    assert resource_path("config.json") == tmp_path / "config.json"
