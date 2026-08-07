import json
from pydantic import BaseModel, Field, ValidationError


class Level(BaseModel):
    id: int = Field(ge=1)
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class Config(BaseModel):
    highscore_filename: str = "highscores.json"

    seed: int = 42
    lives: int = Field(default=10, ge=1)  # 一旦1にしてますが、10に変える
    level_max_time: int = Field(default=90, ge=1)

    pacgum: int = Field(default=42, ge=1)
    points_per_pacgum: int = Field(default=10, ge=0)
    points_per_super_pacgum: int = Field(default=50, ge=0)
    points_per_ghost: int = Field(default=200, ge=0)

    level: list[Level] = Field(default_factory=list)


class Parsing:

    @staticmethod
    def _remove_comments(text: str) -> str:

        rows: list[str] = []

        for row in text.splitlines():
            if row.lstrip().startswith("#"):
                continue

            rows.append(row)

        return "\n".join(rows)

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

        try:
            return Config.model_validate(data)

        except ValidationError as e:
            print("Invalid configuration:")
            print(e)
            return Config()
