from pathlib import Path

import pytest

from src.parse import Config, Parsing


def test_config_pads_levels_to_ten() -> None:
    config = Config(level=[{"id": 1, "width": 19, "height": 19}])

    assert len(config.level) == 10
    assert config.level[0] == {"id": 1, "width": 19, "height": 19}
    assert config.level[1] == {"id": 2, "width": 10, "height": 10}
    assert config.level[-1] == {"id": 10, "width": 11, "height": 11}


def test_parser_only_removes_hash_comment_lines(tmp_path: Path) -> None:
    filename = tmp_path / "config.json"
    filename.write_text(
        "  # this entire line is a comment\n"
        "{\n"
        '  "highscore_filename": "scores/*keep*/#keep//data.json"\n'
        "}\n",
        encoding="utf-8",
    )

    config = Parsing.parse_file(str(filename))

    assert (
        config.highscore_filename
        == "scores/*keep*/#keep//data.json"
    )


def test_parser_falls_back_for_non_utf8_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    filename = tmp_path / "config.json"
    filename.write_bytes(b"\xff")

    config = Parsing.parse_file(str(filename))

    assert config.model_dump() == Config().model_dump()
    assert "Config file is not valid UTF-8" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("payload", "field", "expected"),
    [
        ('{"seed": true}', "seed", 42),
        ('{"lives": true}', "lives", 3),
        ('{"level_max_time": true}', "level_max_time", 90),
        ('{"points_per_pacgum": true}', "points_per_pacgum", 10),
        (
            '{"points_per_super_pacgum": true}',
            "points_per_super_pacgum",
            50,
        ),
        ('{"points_per_ghost": true}', "points_per_ghost", 200),
        (
            '{"level": [{"id": true, "width": 9, "height": 9}]}',
            "level",
            Config().level,
        ),
        (
            '{"level": [{"id": 1, "width": true, "height": 9}]}',
            "level",
            Config().level,
        ),
        (
            '{"level": [{"id": 1, "width": 9, "height": true}]}',
            "level",
            Config().level,
        ),
    ],
)
def test_parser_falls_back_for_boolean_integer_values(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    payload: str,
    field: str,
    expected: object,
) -> None:
    filename = tmp_path / "config.json"
    filename.write_text(payload, encoding="utf-8")

    config = Parsing.parse_file(str(filename))

    assert getattr(config, field) == expected
    assert f"Invalid value for '{field}'" in capsys.readouterr().out
