"""
Pacman・ゴーストで共通のキャラクター基底クラスを定義するモジュール。

マス目単位ではなく、マス未満の細かい座標(float)で滑らかに移動する
物理演算(壁の当たり判定・コーナリング)をここに1箇所へ集約している。
Pacman/Ghostはこの上に、入力の受け取りやAIによる方向決定を足すだけで
移動処理そのものには手を加えない設計になっている。
"""
from math import sqrt

from src.enums import Direction


class Character:
    """
    Pacman・ゴースト共通の移動・当たり判定を持つ基底クラス。

    座標系について: self.x, self.yは「マス目の中心を整数値とする」
    浮動小数点座標。例えばx=3.0はグリッド上の3列目マスの中心を表し、
    x=3.4はそこから右に0.4マス分進んだ位置を表す。この方式により、
    マス単位の壁判定グリッド(0/1の2次元配列)と、マス未満の滑らかな
    移動アニメーションを両立させている。

    CORNER_CUT_DISTANCE: 曲がり角に差し掛かった時、どれだけ手前から
    斜めに切り込んで曲がり始めるかの距離。0だとマスの中心にきっちり
    到達してから曲がる(Ghost向け)。Pacmanはこれを正の値に設定して
    やや早めに曲がり始めることで、キー入力への反応をよく見せている。
    """

    CORNER_CUT_DISTANCE = 0.0

    def __init__(self, start_x: float, start_y: float) -> None:
        """初期座標を受け取り、状態(向き・速度・当たり判定半径)を初期化する。

        Args:
            start_x: 開始位置のグリッドx座標。
            start_y: 開始位置のグリッドy座標。
        """
        self.x: float = start_x
        self.y: float = start_y
        self.direction: Direction = Direction.RIGHT
        self.next_direction: Direction | None = None
        self.speed: float = 0.095
        # 当たり判定と描画の両方で共有する半径（食い違うと壁にめり込んで見える）
        self.radius: float = 0.45  # 0.45にすると食い込まない

    def get_current_grid(self) -> tuple[int, int]:
        """現在位置に最も近いグリッド座標(整数のマス目)を返す。

        +0.5してint()で切り捨てることで、四捨五入相当の変換になる
        (例: x=2.6 -> int(3.1) -> 3、x=2.4 -> int(2.9) -> 2)。
        """
        return int(self.x + 0.5), int(self.y + 0.5)

    def _collides_with_wall(
        self,
        check_x: float,
        check_y: float,
        maze_data: list[list[int]],
        collision_radius: float | None = None
    ) -> bool:
        """指定した座標のボックスが壁(1)に接触しているかを正確に判定する

        キャラクターを「中心(check_x, check_y)、半径collision_radius
        (省略時はself.radius)の正方形の当たり判定ボックス」とみなし、
        そのボックスが重なる可能性のある全グリッドセルを走査して、
        1つでも壁(値1)または迷路の範囲外があれば衝突とみなす。
        範囲外を壁扱いにしているのは、配列の範囲外アクセスによる
        クラッシュを防ぎつつ、迷路の外へキャラクターが出ないように
        するため。

        Args:
            check_x: 判定したい中心のx座標。
            check_y: 判定したい中心のy座標。
            maze_data: 壁=1/通路=0のグリッド。
            collision_radius: 判定に使う半径。省略時はself.radius。

        Returns:
            壁または迷路範囲外に接触していればTrue。
        """
        radius = self.radius if collision_radius is None else collision_radius

        left = check_x - radius
        right = check_x + radius
        top = check_y - radius
        bottom = check_y + radius

        min_x = int(left + 0.5)
        max_x = int(right + 0.5)
        min_y = int(top + 0.5)
        max_y = int(bottom + 0.5)

        height = len(maze_data)

        for gy in range(min_y, max_y + 1):
            for gx in range(min_x, max_x + 1):
                if gy < 0 or gy >= height:
                    return True
                if gx < 0 or gx >= len(maze_data[gy]):
                    return True
                if maze_data[gy][gx] == 1:
                    return True

        return False

    def move_forward(self, maze_data: list[list[int]]) -> bool:
        """毎フレーム呼ばれる移動処理の本体。

        以下の優先順位で1フレーム分の移動を試みる。

        1. 予約された次の方向(next_direction)が現在の向きの真逆
           (Uターン)なら、壁判定を待たずに即座に向きを切り替える
           (パックマンらしい即応性のため)。
        2. コーナーカット中(CORNER_CUT_DISTANCE > 0)なら、
           _move_during_corner_alignmentで斜め移動を継続する。
        3. 交差点に近ければ_move_through_turnで曲がる。
        4. どれにも該当しなければ、現在の向きへ直進を試みる。

        Returns:
            実際に座標が変化した(移動できた)かどうか。壁に阻まれて
            動けなかった場合はFalse。
        """
        if self.next_direction is not None:
            is_horizontal_opposite = (
                self.direction in (Direction.LEFT, Direction.RIGHT) and
                self.next_direction in (Direction.LEFT, Direction.RIGHT) and
                self.direction != self.next_direction
            )
            is_vertical_opposite = (
                self.direction in (Direction.UP, Direction.DOWN) and
                self.next_direction in (Direction.UP, Direction.DOWN) and
                self.direction != self.next_direction
            )
            if is_horizontal_opposite or is_vertical_opposite:
                # 真後ろへの方向転換は、交差点でなくても即座に許可する。
                self.direction = self.next_direction
                self.next_direction = None

        if self._move_during_corner_alignment(maze_data):
            return True

        if self._move_through_turn(maze_data):
            return True

        # 2. 現在の方向へ進む
        next_x, next_y = self.x, self.y
        if self.direction == Direction.UP:
            next_y -= self.speed
        elif self.direction == Direction.DOWN:
            next_y += self.speed
        elif self.direction == Direction.LEFT:
            next_x -= self.speed
        elif self.direction == Direction.RIGHT:
            next_x += self.speed

        # 3. 壁がなければ座標を確定
        if not self._collides_with_wall(next_x, next_y, maze_data):
            self.x = next_x
            self.y = next_y
            return True

        return False

    def _move_during_corner_alignment(
        self,
        maze_data: list[list[int]]
    ) -> bool:
        """切り込んだ旋回中は、速度を保ちながら通路中央へ寄せる

        _move_through_turnで曲がり角を斜めに切り込んだ直後は、
        キャラクターが通路の中心線からわずかにズレた位置にいる。
        このメソッドは、そのズレ(alignment_distance)を毎フレーム
        少しずつ解消しながら進行方向にも進むことで、「斜めに切り込んで
        から自然に中心線へ戻る」動きを実現する。

        速度ベクトルを「中心線へ寄る成分」と「進行方向へ進む成分」に
        分解し、全体の移動量がself.speedを超えないよう
        (alignment_step^2 + forward_step^2 = speed^2 となるように)
        三平方の定理で配分している。

        Returns:
            補正込みで移動できればTrue。CORNER_CUT_DISTANCEが0の
            場合や、既に中心線上にいる場合、あるいは補正後の位置が
            壁に当たる場合はFalseを返し、呼び出し元に別の移動処理
            (_move_through_turnや直進)を試みさせる。
        """
        if self.CORNER_CUT_DISTANCE <= 0:
            return False

        grid_x = round(self.x)
        grid_y = round(self.y)
        if self.direction in (Direction.UP, Direction.DOWN):
            alignment_distance = abs(grid_x - self.x)
        else:
            alignment_distance = abs(grid_y - self.y)

        if alignment_distance <= 1e-9:
            return False

        alignment_step = min(
            alignment_distance,
            self.speed / sqrt(2.0)
        )
        forward_step = sqrt(
            max(0.0, self.speed ** 2 - alignment_step ** 2)
        )

        next_x, next_y = self._position_in_direction(
            self.x,
            self.y,
            self.direction,
            forward_step
        )
        if self.direction in (Direction.UP, Direction.DOWN):
            next_x += alignment_step if self.x < grid_x else -alignment_step
        else:
            next_y += alignment_step if self.y < grid_y else -alignment_step

        corner_radius = max(0.0, self.radius - self.CORNER_CUT_DISTANCE)
        if self._collides_with_wall(
            next_x, next_y, maze_data, corner_radius
        ):
            return False

        self.x = next_x
        self.y = next_y
        return True

    def _move_through_turn(self, maze_data: list[list[int]]) -> bool:
        """交差点の中心を基準に、残りの移動量で曲がる

        次に曲がりたい方向(next_direction)が現在の向きと直交して
        いて(例: 直進中にUPが予約されている)、かつマス中心までの
        距離が「今フレームで進める距離(+コーナーカット分の余裕)」
        以内に近づいたら、曲がり始める。

        距離に応じて2パターンに分岐する。
        - マス中心まで遠い(distance_to_center > self.speed):
          中心までの残り距離を「現在の向きへの成分」と「次の向きへの
          成分」に分解して斜めに進む(切り込み)。この場合はまだ
          direction/next_directionを確定させない(次フレームでも
          _move_through_turnが呼ばれ続ける)。
        - マス中心まで近い: 中心へ到達しきってから、残りの移動量分
          だけ新しい方向へ進める。ここでdirectionを確定させ、
          next_directionをクリアする。

        Returns:
            曲がる処理を実行できればTrue。次の方向が予約されて
            いない、直交していない、まだ交差点に近づいていない、
            あるいは曲がった先が壁の場合はFalseを返し、呼び出し元
            (move_forward)に直進を試みさせる。
        """
        if self.next_direction is None:
            return False

        is_current_horizontal = self.direction in (
            Direction.LEFT, Direction.RIGHT
        )
        is_next_horizontal = self.next_direction in (
            Direction.LEFT, Direction.RIGHT
        )
        if is_current_horizontal == is_next_horizontal:
            # 同じ軸(水平/垂直)への切り替えは「曲がる」ではなく
            # move_forward先頭のUターン処理で扱うので、ここでは何もしない。
            return False

        grid_x = round(self.x)
        grid_y = round(self.y)

        if self.direction == Direction.UP:
            signed_distance_to_center = self.y - grid_y
        elif self.direction == Direction.DOWN:
            signed_distance_to_center = grid_y - self.y
        elif self.direction == Direction.LEFT:
            signed_distance_to_center = self.x - grid_x
        else:
            signed_distance_to_center = grid_x - self.x

        distance_to_center = abs(signed_distance_to_center)
        corner_entry_distance = self.speed
        if signed_distance_to_center >= 0:
            corner_entry_distance += self.CORNER_CUT_DISTANCE
        if distance_to_center > corner_entry_distance:
            return False

        test_x, test_y = self._position_in_direction(
            float(grid_x),
            float(grid_y),
            self.next_direction,
            self.speed
        )
        if self._collides_with_wall(test_x, test_y, maze_data):
            # 曲がった先が壁なら、無理に曲がらず直進判定に任せる。
            return False

        if distance_to_center > self.speed:
            # まだマス中心より手前なので、今フレームでは中心まで
            # 到達しきらない。現在の向きと次の向きへ半分ずつ
            # (斜めに)進むことで、角を滑らかに切り込む。
            diagonal_step = self.speed / sqrt(2.0)
            next_x, next_y = self._position_in_direction(
                self.x,
                self.y,
                self.direction,
                diagonal_step
            )
            next_x, next_y = self._position_in_direction(
                next_x,
                next_y,
                self.next_direction,
                diagonal_step
            )
            corner_radius = max(
                0.0, self.radius - self.CORNER_CUT_DISTANCE
            )
            if self._collides_with_wall(
                next_x, next_y, maze_data, corner_radius
            ):
                return False

            self.x = next_x
            self.y = next_y
            self.direction = self.next_direction
            self.next_direction = None
            return True

        # マス中心まで到達しきる距離なので、中心を経由して残りの
        # 移動量を新しい向きへ消化し、方向転換を確定させる。
        remaining_distance = self.speed - distance_to_center
        if self.CORNER_CUT_DISTANCE > 0:
            diagonal_remaining = sqrt(
                max(0.0, self.speed ** 2 - distance_to_center ** 2)
            )
            remaining_distance = min(
                remaining_distance + self.CORNER_CUT_DISTANCE,
                diagonal_remaining
            )
        self.x, self.y = self._position_in_direction(
            float(grid_x),
            float(grid_y),
            self.next_direction,
            remaining_distance
        )
        self.direction = self.next_direction
        self.next_direction = None
        return True

    @staticmethod
    def _position_in_direction(
        x: float,
        y: float,
        direction: Direction,
        distance: float
    ) -> tuple[float, float]:
        """(x, y)からdirection方向へdistanceだけ進んだ座標を返す。

        画面座標系(下方向がy増加)に合わせて、UPはyを減らし
        DOWNはyを増やす。
        """
        if direction == Direction.UP:
            y -= distance
        elif direction == Direction.DOWN:
            y += distance
        elif direction == Direction.LEFT:
            x -= distance
        elif direction == Direction.RIGHT:
            x += distance
        return x, y
