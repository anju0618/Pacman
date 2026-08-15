"""Persistent high-score management."""

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import tempfile
from typing import TypeGuard


MAX_HIGH_SCORES = 10
_NAME_PATTERN = re.compile(r"[A-Za-z0-9 ]{1,10}")


@dataclass(frozen=True)
class HighScoreEntry:
    """One validated high-score entry."""

    name: str
    score: int


class HighScoreSystem:
    """Load, rank, and persist the ten best scores."""

    def __init__(self, filename: str) -> None:
        self.path = Path(filename)
        self.entries: list[HighScoreEntry] = []

    @staticmethod
    def normalize_name(name: str) -> str:
        """Remove insignificant whitespace around a player name."""
        return name.strip()

    @classmethod
    def is_valid_name(cls, name: str) -> bool:
        """Return whether a name meets the configured input rules."""
        normalized = cls.normalize_name(name)
        return _NAME_PATTERN.fullmatch(normalized) is not None

    @staticmethod
    def is_valid_score(score: object) -> TypeGuard[int]:
        """Return whether a score is a non-negative integer."""
        return type(score) is int and score >= 0

    @staticmethod
    def _rank(entries: list[HighScoreEntry]) -> list[HighScoreEntry]:
        # Python's sort is stable, so an earlier entry wins a tie.
        return sorted(entries, key=lambda entry: entry.score, reverse=True)

    def load(self) -> list[HighScoreEntry]:
        """Load valid entries, falling back to an empty list on file errors."""
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            self.entries = []
            return []
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as error:
            print(f"Could not load high scores from '{self.path}': {error}")
            self.entries = []
            return []

        if not isinstance(data, list):
            print(
                f"Invalid high-score format in '{self.path}': "
                "expected a list"
            )
            self.entries = []
            return []

        valid_entries: list[HighScoreEntry] = []
        for index, item in enumerate(data):
            entry = self._parse_entry(item)
            if entry is None:
                print(
                    f"Ignoring invalid high-score entry {index} "
                    f"in '{self.path}'"
                )
                continue
            valid_entries.append(entry)

        self.entries = self._rank(valid_entries)[:MAX_HIGH_SCORES]
        return list(self.entries)

    @classmethod
    def _parse_entry(cls, item: object) -> HighScoreEntry | None:
        if not isinstance(item, dict):
            return None

        name = item.get("name")
        score = item.get("score")
        if not isinstance(name, str) or not cls.is_valid_name(name):
            return None
        if not cls.is_valid_score(score):
            return None

        return HighScoreEntry(cls.normalize_name(name), score)

    def add(self, name: str, score: int) -> bool:
        """Add a score and return whether it remains in the top ten."""
        if not self.is_valid_name(name):
            raise ValueError(
                "Name must be 1-10 ASCII letters, digits, or spaces"
            )
        if not self.is_valid_score(score):
            raise ValueError("Score must be a non-negative integer")

        normalized = self.normalize_name(name)
        candidate = HighScoreEntry(normalized, score)
        ranked = self._rank([*self.entries, candidate])
        self.entries = ranked[:MAX_HIGH_SCORES]
        return any(entry is candidate for entry in self.entries)

    def save(self) -> bool:
        """Atomically save entries, returning False instead of crashing."""
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
                delete=False,
            ) as file:
                temporary_path = Path(file.name)
                json.dump(
                    [asdict(entry) for entry in self.entries],
                    file,
                    ensure_ascii=True,
                    indent=2,
                )
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.path)
        except OSError as error:
            print(f"Could not save high scores to '{self.path}': {error}")
            return False
        finally:
            if temporary_path is not None and temporary_path.exists():
                try:
                    temporary_path.unlink()
                except OSError:
                    pass

        return True
