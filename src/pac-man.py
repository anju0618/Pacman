import argparse
from parse import Parsing


def main() -> None:
    parser = argparse.ArgumentParser(
        description="packman"
    )
    parser.add_argument(
        "config",
        help="config file name"
    )
    parser.add_argument(
        "--cheat",
        action="store_true",
        help="can not be dameged"
    )
    args = parser.parse_args()
    print(args.config)
    print("=" * 30)
    file_parser = Parsing()
    config = file_parser.parse_file(args.config)
    print(config)


if __name__ == "__main__":
    main()
