"""ハイスコアの永続化を担当するモジュール。

課題要件(V.5)により、ハイスコアシステムは以下を満たす必要がある。
- ファイルの欠損・不正フォーマットに対して堅牢であること(クラッシュしない)。
- プレイヤー名(最大10文字、英数字とスペースのみ)とスコア(非負整数)を扱えること。
- 上位10件のみを保持すること。
- ゲーム開始時にロードし、ゲーム終了時にセーブすること。
"""

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import tempfile
from typing import TypeGuard


MAX_HIGH_SCORES = 10
# 名前の妥当性チェック用の正規表現: 半角英数字とスペースのみ、1〜10文字。
_NAME_PATTERN = re.compile(r"[A-Za-z0-9 ]{1,10}")


@dataclass(frozen=True)
class HighScoreEntry:
    """検証済みの1件分のハイスコア(プレイヤー名とスコア)。

    frozen=Trueにしているのは、ランキング内で扱う値を不変にして
    意図しない書き換えを防ぐため。
    """

    name: str
    score: int


class HighScoreSystem:
    """上位10件のハイスコアの読み込み・順位付け・保存を行うクラス。

    JSONファイルへの読み書きを担当し、ファイルが存在しない・壊れて
    いる・不正な内容であっても例外を外へ漏らさず、安全なフォール
    バック(空のリスト)で処理を継続する。
    """

    def __init__(self, filename: str) -> None:
        """保存先ファイルのパスを受け取り、空の状態で初期化する。

        Args:
            filename: ハイスコアを保存するJSONファイルのパス
                (config.jsonの`highscore_filename`から渡される)。
        """
        self.path = Path(filename)
        self.entries: list[HighScoreEntry] = []

    @staticmethod
    def normalize_name(name: str) -> str:
        """プレイヤー名の前後の余分な空白を取り除く。"""
        return name.strip()

    @classmethod
    def is_valid_name(cls, name: str) -> bool:
        """名前が「半角英数字とスペースのみ、1〜10文字」を満たすか判定する。"""
        normalized = cls.normalize_name(name)
        return _NAME_PATTERN.fullmatch(normalized) is not None

    @staticmethod
    def is_valid_score(score: object) -> TypeGuard[int]:
        """スコアが非負の整数かどうかを判定する(bool型は弾く)。

        `type(score) is int`という厳密な型チェックにしているのは、
        Pythonでは`bool`が`int`のサブクラスであり
        `isinstance(True, int)`がTrueになってしまうため、
        JSONから読み込んだ値に紛れ込んだ真偽値を誤ってスコアとして
        受理しないようにするための対策。
        """
        return type(score) is int and score >= 0

    @staticmethod
    def _rank(entries: list[HighScoreEntry]) -> list[HighScoreEntry]:
        """スコアの高い順に並べ替える(同点は先に登録された方を優先)。"""
        # Python's sort is stable, so an earlier entry wins a tie.
        return sorted(entries, key=lambda entry: entry.score, reverse=True)

    def load(self) -> list[HighScoreEntry]:
        """ハイスコアファイルを読み込み、上位10件をentriesに保持する。

        ファイルが存在しない場合や、JSONとして壊れている場合、
        中身がリストでない場合、いずれもクラッシュせず空のリストへ
        フォールバックする(課題要件: ファイルエラーに堅牢であること)。

        Returns:
            読み込んだ(または空の)ハイスコア一覧のコピー。
        """
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            self.entries = []
            return []
        except (UnicodeDecodeError, OSError, ValueError) as error:
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
                # 1件だけ壊れていても全体を諦めず、そのエントリだけ
                # 読み飛ばして残りを活かす。
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
        """JSON中の1要素を検証し、妥当ならHighScoreEntryに変換する。

        辞書でない、name/scoreが無い・型が違う、名前が命名規則に
        反する、スコアが非負整数でない、いずれの場合もNoneを返す
        (呼び出し元のload()側でそのエントリを読み飛ばす)。
        """
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
        """新しいスコアを登録し、上位10件を更新する。

        Args:
            name: プレイヤー名(命名規則に合わないとValueError)。
            score: 非負整数のスコア(そうでないとValueError)。

        Returns:
            このスコアが上位10件に残ったかどうか。
        """
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
        """現在のentriesをJSONファイルへアトミックに保存する。

        書き込み途中でクラッシュ・強制終了してもファイルが壊れた
        状態で残らないよう、まず同じディレクトリに一時ファイルを
        作って書き込みを完了させてから、`os.replace`で本来のパスへ
        アトミックに置き換える(保存の途中経過が外から見えない)。

        Returns:
            保存に成功したかどうか。失敗時も例外は投げず、
            falseを返してエラーメッセージだけ出力する。
        """
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
        except (OSError, ValueError) as error:
            print(f"Could not save high scores to '{self.path}': {error}")
            return False
        finally:
            # os.replace()が成功していれば一時ファイルは既に本来の
            # パスへ移動済みなので、ここに残っているのは失敗時のゴミ
            # だけ。掃除にも失敗しても致命的ではないので握りつぶす。
            if temporary_path is not None and temporary_path.exists():
                try:
                    temporary_path.unlink()
                except OSError:
                    pass

        return True
