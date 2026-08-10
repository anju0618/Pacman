# pac-man.py
import argparse
from src.parse import Parsing
from src.game_state import PacmanGameContext


def main() -> None:

    parser = argparse.ArgumentParser(description="packman")
    parser.add_argument("config", help="config file name")
    parser.add_argument("--cheat", action="store_true", help="can not be dameged")

    args = parser.parse_args()

    file_parser = Parsing()
    config = file_parser.parse_file(args.config)

    game_context = PacmanGameContext(
        config=config,
        lives=config.lives,
        time_remaining=config.level_max_time,
        is_cheat_mode_active=args.cheat
    )

    print(f"残機: {game_context.lives}, 制限時間: {game_context.time_remaining}")
    if game_context.is_cheat_mode_active:
        print("チートモード有効")


if __name__ == "__main__":
    main()
