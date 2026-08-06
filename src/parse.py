from typing import Any
from pydantic import BaseModel
import defaultdict


def parse_file(path: str) -> list[dict[str, Any]]:
    config: list[dict[str, Any]] = []
    try:
        with open(path, "r") as f:
            text: str = f.read()
            text_rows: list[str] = text.splitlines()
            new_rows: list[str] = []
            for row in text_rows:
                if row.strip().startswith("#"):
                    continue
                new_rows.append(row)

    except PermissionError as e:
        print(e)
    except FileNotFoundError as e:
        print(e)
    return config
