import json
from pathlib import Path

import pytest

from src.highscore import HighScoreEntry, HighScoreSystem, MAX_HIGH_SCORES


def test_missing_file_loads_empty_ranking(tmp_path: Path) -> None:
    system = HighScoreSystem(str(tmp_path / "missing.json"))

    assert system.load() == []
    assert system.entries == []


def test_add_sorts_scores_and_keeps_earlier_entry_on_tie(
    tmp_path: Path,
) -> None:
    system = HighScoreSystem(str(tmp_path / "highscores.json"))

    assert system.add("FIRST", 100)
    assert system.add("SECOND", 100)
    assert system.add("TOP", 200)

    assert system.entries == [
        HighScoreEntry("TOP", 200),
        HighScoreEntry("FIRST", 100),
        HighScoreEntry("SECOND", 100),
    ]


def test_add_keeps_only_top_ten(tmp_path: Path) -> None:
    system = HighScoreSystem(str(tmp_path / "highscores.json"))

    for score in range(MAX_HIGH_SCORES):
        assert system.add(f"P{score}", score)

    assert not system.add("LOW", 0)
    assert len(system.entries) == MAX_HIGH_SCORES
    assert system.entries[0].score == 9
    assert system.entries[-1].name == "P0"


@pytest.mark.parametrize(
    "name",
    ["", "   ", "TOO-LONG-NAME", "PAC!", "パックマン"],
)
def test_add_rejects_invalid_name(tmp_path: Path, name: str) -> None:
    system = HighScoreSystem(str(tmp_path / "highscores.json"))

    with pytest.raises(ValueError):
        system.add(name, 100)


def test_add_rejects_invalid_score(tmp_path: Path) -> None:
    system = HighScoreSystem(str(tmp_path / "highscores.json"))

    with pytest.raises(ValueError):
        system.add("PLAYER", -1)

    with pytest.raises(ValueError):
        system.add("PLAYER", True)


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    filename = tmp_path / "highscores.json"
    system = HighScoreSystem(str(filename))
    system.add(" Player 1 ", 420)

    assert system.save()

    loaded = HighScoreSystem(str(filename))
    assert loaded.load() == [HighScoreEntry("Player 1", 420)]
    data = json.loads(filename.read_text(encoding="utf-8"))
    assert data == [{"name": "Player 1", "score": 420}]


def test_load_ignores_invalid_entries(tmp_path: Path) -> None:
    filename = tmp_path / "highscores.json"
    filename.write_text(
        json.dumps(
            [
                {"name": "VALID", "score": 20},
                {"name": "BAD!", "score": 50},
                {"name": "NEGATIVE", "score": -1},
                {"name": "BOOLEAN", "score": True},
                "not an object",
            ]
        ),
        encoding="utf-8",
    )
    system = HighScoreSystem(str(filename))

    assert system.load() == [HighScoreEntry("VALID", 20)]


def test_corrupt_file_loads_empty_ranking(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    filename = tmp_path / "highscores.json"
    filename.write_text("not json", encoding="utf-8")
    system = HighScoreSystem(str(filename))

    assert system.load() == []
    assert "Could not load high scores" in capsys.readouterr().out


def test_oversized_integer_file_loads_empty_ranking(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    filename = tmp_path / "highscores.json"
    filename.write_text(
        '[{"name": "PLAYER", "score": '
        + "9" * 5000
        + "}]",
        encoding="utf-8",
    )
    system = HighScoreSystem(str(filename))

    assert system.load() == []
    assert "Could not load high scores" in capsys.readouterr().out


def test_invalid_filename_load_and_save_do_not_raise(
    capsys: pytest.CaptureFixture[str],
) -> None:
    system = HighScoreSystem("\x00")

    assert system.load() == []
    system.add("PLAYER", 100)
    assert not system.save()

    output = capsys.readouterr().out
    assert "Could not load high scores" in output
    assert "Could not save high scores" in output


def test_save_error_does_not_raise(tmp_path: Path) -> None:
    system = HighScoreSystem(str(tmp_path / "missing" / "highscores.json"))
    system.add("PLAYER", 100)

    assert not system.save()
