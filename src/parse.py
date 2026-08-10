import json
import re
from typing import Annotated, Self, TypedDict

from pydantic import BaseModel, Field, ValidationError, model_validator


class Level(TypedDict):
    id: Annotated[int, Field(ge=1)]
    width: Annotated[int, Field(ge=1)]
    height: Annotated[int, Field(ge=1)]


DEFAULT_LEVELS: tuple[Level, ...] = (
    {"id": 1, "width": 21, "height": 21},
    {"id": 2, "width": 25, "height": 25},
    {"id": 3, "width": 31, "height": 31},
    {"id": 4, "width": 31, "height": 31},
    {"id": 5, "width": 31, "height": 31},
    {"id": 6, "width": 31, "height": 31},
    {"id": 7, "width": 31, "height": 31},
    {"id": 8, "width": 31, "height": 31},
    {"id": 9, "width": 31, "height": 31},
    {"id": 10, "width": 31, "height": 31},
)


def _default_levels() -> list[Level]:
    return [level.copy() for level in DEFAULT_LEVELS]


class Config(BaseModel):
    highscore_filename: str = "highscores.json"

    seed: int = 42
    lives: int = Field(default=3, ge=1)
    level_max_time: int = Field(default=90, ge=1)

    pacgum: int = Field(default=42, ge=1)
    points_per_pacgum: int = Field(default=10, ge=0)
    points_per_super_pacgum: int = Field(default=50, ge=0)
    points_per_ghost: int = Field(default=200, ge=0)

    level: list[Level] = Field(default_factory=_default_levels)

    @model_validator(mode="after")
    def ensure_minimum_levels(self) -> Self:
        missing_count = len(DEFAULT_LEVELS) - len(self.level)
        if missing_count > 0:
            self.level.extend(
                level.copy() for level in DEFAULT_LEVELS[-missing_count:]
            )
        return self


class Parsing:

    @staticmethod
    def _strip_line_comment(line: str) -> str:
        """
        行内で最初にJSON文字列の外側に現れた '#' または '//' より
        右側をコメントとして切り捨てる。文字列リテラル内の '#'/'//' は
        値として保持する。
        """
        in_string = False
        escaped = False

        for i, ch in enumerate(line):
            if in_string:
                if escaped:
                    escaped = False
                elif ch == '\\':
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch == '#':
                return line[:i]
            elif ch == '/' and i + 1 < len(line) and line[i + 1] == '/':
                return line[:i]

        return line

    @staticmethod
    def _remove_comments(text: str) -> str:
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        lines = [
            Parsing._strip_line_comment(line) for line in text.splitlines()
        ]
        return '\n'.join(lines)

    @staticmethod
    def parse_file(filename: str) -> Config:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                text = f.read()

        except FileNotFoundError:
            print(f"File not found: {filename}")
            return Config()

        except PermissionError:
            print(f"Permission denied: {filename}")
            return Config()

        except OSError as e:
            print(f"Could not open config file: {e}")
            return Config()

        text = Parsing._remove_comments(text)

        try:
            data = json.loads(text)

        except json.JSONDecodeError as e:
            print(
                f"Invalid JSON: "
                f"line {e.lineno}, "
                f"column {e.colno}: "
                f"{e.msg}"
            )
            return Config()

        if not isinstance(data, dict):
            print("Config root must be a JSON object.")
            return Config()

        return Parsing._build_config(data)

    @staticmethod
    def _build_config(data: dict[str, object]) -> Config:
        """
        キーごとに検証し、不正な値は安全なデフォルトにフォールバックして
        ログ出力のうえ処理を続行する。未知のキーは無視する。
        """
        config = Config()

        for key, value in data.items():
            if key not in Config.model_fields:
                continue

            try:
                config = Config.model_validate(
                    {**config.model_dump(), key: value}
                )
            except ValidationError as e:
                default = Config.model_fields[key].get_default(
                    call_default_factory=True
                )
                print(
                    f"Invalid value for '{key}': {value!r} "
                    f"-> using default {default!r} "
                    f"({e.error_count()} error(s))"
                )

        return config
