# pac-man.py
import argparse
import sys
from src.parse import Parsing
from src.game_state import PacmanGameContext
from src.graphic.display import Display


def main() -> None:

    parser = argparse.ArgumentParser(description="packman")
    parser.add_argument(
        "config", help="config file name"
        )
    parser.add_argument(
        "--cheat", action="store_true", help="can not be dameged"
        )

    args = parser.parse_args()

    file_parser = Parsing()
    config = file_parser.parse_file(args.config)

    game_context = PacmanGameContext(
        config=config,
        lives=config.lives,
        time_remaining=config.level_max_time,
        is_cheat_mode_active=args.cheat
    )

    display = Display(game_context)
    display.run()
    print(f"残機: {game_context.lives}, 制限時間: {game_context.time_remaining}")
    if game_context.is_cheat_mode_active:
        print("チートモード有効")


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
