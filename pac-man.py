# pac-man.py
"""
ゲームのエントリポイント。

コマンドライン引数(設定ファイル)を解釈し、設定を読み込んで
ゲーム本体(Display)を起動する。
"""
import argparse
import sys

from src.game_state import PacmanGameContext
from src.graphic.display import Display
from src.parse import Parsing
from src.resources import is_frozen, resource_path

DEFAULT_CONFIG_NAME = "config.json"


def _parse_args() -> argparse.Namespace:
    """コマンドライン引数を解釈する。

    課題要件(V.1)により、ソースから実行する場合は
    `python3 pac-man.py config.json` のように設定ファイルを
    1つ受け取る。

    ただしパッケージ版(Steam/Itch.io等から起動される実行ファイル)は
    ダブルクリックで起動され、引数が一切渡されない。そのため
    パッケージ版に限り引数を省略可能にし、同梱のconfig.jsonを
    既定値として使う。
    """
    parser = argparse.ArgumentParser(
        prog="pac-man",
        description="Pac-Man - a 42 school project.",
    )
    parser.add_argument(
        "config",
        nargs="?" if is_frozen() else None,
        help="path to the JSON configuration file",
    )
    parser.add_argument(
        "--cheat",
        action="store_true",
        help="enable cheat mode (invincibility, extra lives, "
             "faster movement, F to freeze ghosts, N to skip a level)",
    )
    return parser.parse_args()


def main() -> None:
    """設定を読み込み、ゲームを起動する。"""
    args = _parse_args()

    config_path = args.config
    if config_path is None:
        # パッケージ版で引数なしに起動された場合は、実行ファイルに
        # 同梱されたconfig.jsonを使う。
        config_path = str(resource_path(DEFAULT_CONFIG_NAME))

    config = Parsing.parse_file(config_path)

    game_context = PacmanGameContext(
        config=config,
        lives=config.lives,
        time_remaining=config.level_max_time,
        is_cheat_mode_active=args.cheat,
    )

    Display(game_context).run()


if __name__ == "__main__":
    # 課題要件(III.1)「未処理の例外でクラッシュしないこと」の最終防壁。
    # display.run()内のループ本体はDisplay.run()自身が保護しているが、
    # 設定ファイルの読み込みやDisplay構築（スプライト読み込みなど）は
    # ループの外で行われるため、ここでも念のため覆っておく。
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as error:
        print(f"Fatal error: {error}")
        sys.exit(1)
