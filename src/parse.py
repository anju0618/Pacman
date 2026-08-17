"""
config.jsonの読み込み・検証を行うモジュール。

JSON標準に加えて、空白を除いた行頭が `#` のコメント行を許容する
パーサー(Parsing)と、pydanticによる型・範囲検証つきの設定モデル
(Config)を提供する。
"""
import json
from typing import Annotated, Self, TypedDict

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


class Level(TypedDict):
    """1レベル分の迷路設定(レベル番号・幅・高さ)を表す型。"""

    id: Annotated[int, Field(ge=1)]
    width: Annotated[int, Field(ge=1)]
    height: Annotated[int, Field(ge=1)]


# DEFAULT_LEVELS: tuple[Level, ...] = (
#     {"id": 1, "width": 21, "height": 21},
#     {"id": 2, "width": 25, "height": 25},
#     {"id": 3, "width": 31, "height": 31},
#     {"id": 4, "width": 31, "height": 31},
#     {"id": 5, "width": 31, "height": 31},
#     {"id": 6, "width": 31, "height": 31},
#     {"id": 7, "width": 31, "height": 31},
#     {"id": 8, "width": 31, "height": 31},
#     {"id": 9, "width": 31, "height": 31},
#     {"id": 10, "width": 31, "height": 31},
# )

# config.jsonの"level"配列が10件未満だったときに、不足分を末尾から
# 補って必ず最低10レベル(課題要件)になるようにするためのデフォルト値。
DEFAULT_LEVELS: tuple[Level, ...] = (
    {"id": 1, "width": 10, "height": 10},
    {"id": 2, "width": 10, "height": 10},
    {"id": 3, "width": 10, "height": 10},
    {"id": 4, "width": 11, "height": 11},
    {"id": 5, "width": 11, "height": 11},
    {"id": 6, "width": 11, "height": 11},
    {"id": 7, "width": 11, "height": 11},
    {"id": 8, "width": 11, "height": 11},
    {"id": 9, "width": 11, "height": 11},
    {"id": 10, "width": 11, "height": 11}
)


def _default_levels() -> list[Level]:
    """DEFAULT_LEVELSのコピーを返す(Configのdefault_factory用)。

    pydanticのdefault_factoryはミュータブルな既定値を安全に生成する
    ための仕組みなので、タプルそのものではなく毎回新しいlistを返す。
    """
    return [level.copy() for level in DEFAULT_LEVELS]


class Config(BaseModel):
    """検証済みのゲーム設定を保持するpydanticモデル。

    config.jsonの各キーに対応するフィールドを持ち、型・範囲(Field(ge=...))
    はpydanticが自動的に検証する。不正な値が渡された場合の安全な
    デフォルトへのフォールバック処理は、このクラス自体ではなく
    Parsing._build_config()側で行う(キー単位でフォールバックしたい
    ため、Configをまるごと再構築するのではなくフィールド単位で
    model_validateを試みる設計になっている)。
    """

    highscore_filename: str = "highscores.json"

    seed: int = 42
    lives: int = Field(default=3, ge=1)
    level_max_time: int = Field(default=90, ge=1)

    points_per_pacgum: int = Field(default=10, ge=0)
    points_per_super_pacgum: int = Field(default=50, ge=0)
    points_per_ghost: int = Field(default=200, ge=0)

    level: list[Level] = Field(default_factory=_default_levels)

    @field_validator(
        "seed",
        "lives",
        "level_max_time",
        "points_per_pacgum",
        "points_per_super_pacgum",
        "points_per_ghost",
        mode="before",
    )
    @classmethod
    def reject_boolean_integers(cls, value: object) -> object:
        """真偽値を整数設定として受理しない。"""
        if isinstance(value, bool):
            raise ValueError("integer settings must not be boolean")
        return value

    @field_validator("level", mode="before")
    @classmethod
    def reject_boolean_level_values(cls, value: object) -> object:
        """レベル設定内の真偽値を整数として受理しない。"""
        if isinstance(value, (list, tuple)):
            for level in value:
                if isinstance(level, dict) and any(
                    isinstance(level.get(field_name), bool)
                    for field_name in ("id", "width", "height")
                ):
                    raise ValueError(
                        "level integer settings must not be boolean"
                    )
        return value

    @model_validator(mode="after")
    def ensure_minimum_levels(self) -> Self:
        """課題要件の「最低10レベル」を満たすよう、不足分を自動で補う。

        config.jsonで指定されたレベル数がDEFAULT_LEVELSより少ない場合、
        DEFAULT_LEVELSの末尾側(指定レベルの続き)から不足分を補完する。
        """
        missing_count = len(DEFAULT_LEVELS) - len(self.level)
        if missing_count > 0:
            self.level.extend(
                level.copy() for level in DEFAULT_LEVELS[-missing_count:]
            )
        return self


class Parsing:
    """config.jsonファイルを読み込み、Configへ変換するローダー。

    JSON標準に無い、行頭が `#` のコメント行の除去と、
    キー単位で安全なデフォルトへフォールバックする検証を担当する。
    ファイルの欠損・不正なJSON・不正な値、いずれの場合もトレースバック
    ではなくメッセージを出力して処理を継続する(課題要件V.1/V.3)。
    """

    @staticmethod
    def _remove_comments(text: str) -> str:
        """空白を除いた行頭が `#` のコメント行だけを取り除く。"""
        return '\n'.join(
            line
            for line in text.splitlines()
            if not line.lstrip().startswith('#')
        )

    @staticmethod
    def parse_file(filename: str) -> Config:
        """config.jsonファイルを読み込み、検証済みのConfigを返す。

        ファイルが存在しない・権限がない・UTF-8として読めない・
        JSONとして壊れている、いずれの場合もクラッシュせずメッセージを
        出力し、デフォルト値のConfig()を返す
        (課題要件: 不正な設定でも安全に継続すること)。
        """
        try:
            with open(filename, "r", encoding="utf-8") as f:
                text = f.read()

        except FileNotFoundError:
            print(f"File not found: {filename}")
            return Config()

        except PermissionError:
            print(f"Permission denied: {filename}")
            return Config()

        except UnicodeDecodeError as e:
            print(f"Config file is not valid UTF-8: {filename} ({e})")
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

        1つのConfig()を土台にして、JSONの各キーを1つずつ
        model_validateで検証・適用していく。あるキーの値が不正
        (型違反・範囲外など)でValidationErrorになった場合は、その
        キーだけデフォルト値のままにしてメッセージを出し、他のキーの
        検証は続行する(「1箇所の不正値で設定全体が全滅する」ことを防ぐ)。
        """
        config = Config()

        for key, value in data.items():
            if key not in Config.model_fields:
                # 課題要件: 未知のキーは無視する。
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
