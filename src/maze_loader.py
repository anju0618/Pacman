"""
外部パッケージ「A-Maze-ing」(mazegenerator)を使って迷路を生成し、
ゲーム側が扱いやすいバイナリグリッド(壁=1, 通路=0)に変換するモジュール。

課題要件(V.4)により、割り当てられた迷路生成パッケージは改変せず、
そのインターフェースにこちら側が合わせて使用する必要がある。
"""
from typing import cast
from mazegenerator import MazeGenerator


class MazeLoader:
    """MazeGeneratorをラップし、ゲームが使いやすい形へ変換するクラス。

    MazeGeneratorが返す迷路データは「1マス=1セル、壁の有無をビット
    マスクで表現」という独自形式なので、これをそのまま使わず、
    パックマンのキャラクター移動・当たり判定で扱いやすい
    「壁=1、通路=0」の単純な2次元グリッドに変換して提供する。
    """

    def __init__(self, width: int, height: int, seed: int) -> None:
        """指定サイズ・シードで外部パッケージの迷路生成器を初期化する。

        Args:
            width: 迷路の幅(MazeGenerator側のセル数)。
            height: 迷路の高さ(MazeGenerator側のセル数)。
            seed: 生成に使う乱数シード。0以下だと真の乱数になる
                (MazeGenerator側の仕様)。レベル1は固定シード、
                それ以降のレベルは0(ランダム)を渡す運用にしている。
        """
        self.generator = MazeGenerator(
            size=(width, height),
            # 課題要件(V.4): PERFECT=Falseにしてループのある
            # パックマン向けの通路を生成させる(完全な木構造だと
            # 迷路内に周回できるループが一切できず、パックマンらしい
            # 迷路にならないため)。
            perfect=False,
            seed=seed
        )

    def get_maze_data(self) -> list[list[int]]:
        """MazeGeneratorが生成した迷路データをそのまま返す。

        戻り値の各セルは、そのマスの4方向の壁の有無をビットマスクで
        表した整数(詳しくはget_binary_grid()を参照)。mazegenerator
        パッケージ自体には型情報が無いためcast()で明示している。
        """
        return cast(list[list[int]], self.generator.maze)

    def find_center_start_position(self) -> tuple[int, int]:
        """パックマンの初期位置・リスポーン位置(迷路の中心)を返す。

        課題要件により「プレイヤーは迷路の真ん中からスタートする」
        必要があるため、生成された迷路の幾何学的な中心に最も近い
        通路セルを探して返す(中心そのものが壁の場合もあるため、
        _find_nearest_open_cellで最寄りの通路セルまで探索する)。

        Returns:
            バイナリグリッド座標系での(x, y)。
        """
        binary_grid = self.get_binary_grid()
        height = len(binary_grid)
        width = len(binary_grid[0])
        center_x, center_y = width // 2, height // 2

        return self._find_nearest_open_cell(binary_grid, center_x, center_y)

    def find_corner_positions(self) -> list[tuple[int, int]]:
        """迷路の四隅に最も近い通路セルを、四隅の座標の順に4つ返す。

        課題要件により「4匹のゴーストは迷路の四隅に出現する」必要が
        あるため使用する。戻り値の順序は左上・右上・左下・右下に
        対応し、Display側でBlinky/Pinky/Inky/Clydeの順に割り当てる。
        同じ座標は、超パグム(スーパーパグム)の設置位置としても
        流用される(src/pacgum.py)。

        Returns:
            バイナリグリッド座標系での(x, y)を4つ並べたリスト。
        """
        binary_grid = self.get_binary_grid()
        height = len(binary_grid)
        width = len(binary_grid[0])
        corners = [
            (0, 0),
            (width - 1, 0),
            (0, height - 1),
            (width - 1, height - 1),
        ]
        return [
            self._find_nearest_open_cell(binary_grid, corner_x, corner_y)
            for corner_x, corner_y in corners
        ]

    def _find_nearest_open_cell(
        self,
        binary_grid: list[list[int]],
        target_x: int,
        target_y: int
    ) -> tuple[int, int]:
        """指定座標に最も近い通路セル(値が0のマス)の座標を返す。

        目的地(中心や四隅)そのものが壁の場合に備え、まずその場所が
        通路ならそのまま返し、そうでなければ全マスを総当たりして
        ユークリッド距離(の2乗)が最小の通路セルを探す。迷路の
        サイズはたかだか数十マス四方なので、総当たりでも十分速い。

        Args:
            binary_grid: 壁=1/通路=0のグリッド。
            target_x: 探索したい目的地のx座標。
            target_y: 探索したい目的地のy座標。

        Returns:
            目的地に最も近い通路セルの(x, y)。
        """
        if binary_grid[target_y][target_x] == 0:
            return target_x, target_y

        height = len(binary_grid)
        width = len(binary_grid[0])
        best_position = (target_x, target_y)
        best_distance = None
        for y in range(height):
            for x in range(width):
                if binary_grid[y][x] != 0:
                    continue
                distance = (x - target_x) ** 2 + (y - target_y) ** 2
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_position = (x, y)

        return best_position

    def get_binary_grid(self) -> list[list[int]]:
        """MazeGeneratorのビットマスク形式を、壁=1/通路=0のグリッドに変換する。

        MazeGeneratorの1マスは「壁の有無を4ビットで表した整数」で
        表現されており(ビット0=北, ビット1=東, ビット2=南, ビット3=西
        の壁が「立っている(閉じている)」ことを表す。立っていない
        ＝そちら方向へは壁が無く通行できる)、そのままではPacmanや
        ゴーストの移動・当たり判定(1マス単位の壁/通路グリッド)に
        使えない。

        そこで、元のN×Mマスを「マスの中心」と「マス間の壁」を
        それぞれ1マスとして展開した (2N+1)×(2M+1) のグリッドに
        変換する。各元マスの中心は必ず通路(0)にし、該当方向の壁
        ビットが立っていなければ、その中心と隣接マスの間にある
        壁マスも通路(0)に開ける。こうすることで、壁の太さも含めて
        「1マス移動=1グリッドセル」で扱えるようになる。

        Returns:
            壁=1、通路=0の2次元グリッド((2N+1) x (2M+1))。
        """
        maze_data = self.get_maze_data()
        orig_height = len(maze_data)
        orig_width = len(maze_data[0])
        new_height = orig_height * 2 + 1
        new_width = orig_width * 2 + 1
        # 全マスをいったん壁で初期化し、通路になる部分だけ後から0にする。
        binary_grid = [
            [1 for _ in range(new_width)] for _ in range(new_height)
        ]

        for y in range(orig_height):
            for x in range(orig_width):
                cell = maze_data[y][x]
                # 元マス(x, y)は、展開後グリッドでは(cx, cy)に対応する
                # (偶数インデックスがマス間の壁、奇数インデックスが
                # マスの中心)。
                cy, cx = y * 2 + 1, x * 2 + 1

                binary_grid[cy][cx] = 0

                if not (cell & 1):
                    # 北側の壁ビットが立っていない=北に抜けられるので、
                    # 1つ上の壁マスも通路として開ける。
                    binary_grid[cy - 1][cx] = 0

                if not (cell & 2):
                    # 東側が開いている。
                    binary_grid[cy][cx + 1] = 0

                if not (cell & 4):
                    # 南側が開いている。
                    binary_grid[cy + 1][cx] = 0

                if not (cell & 8):
                    # 西側が開いている。
                    binary_grid[cy][cx - 1] = 0

        return binary_grid
