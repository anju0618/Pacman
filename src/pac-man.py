import argparse
from parse import Parsing


def main() -> None:
    parser = argparse.ArgumentParser(
        description="packman"
    )
    parser.add_argument("configfile", help="ConfigFile")
    args = parser.parse_args()
    print(args.configfile)
    print("=" * 30)
    file_parser = Parsing()
    config = file_parser.parse_file(args.configfile)
    print(config)


if __name__ == "__main__":
    main()
