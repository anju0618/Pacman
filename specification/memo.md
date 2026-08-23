# Packman 全コード解説メモ

レビュー本番で「これはどういう実装か」と聞かれた時に、自分の言葉で
説明できるようにするための詳細メモ。依存関係の浅い順(≒読む順)に
並べてある。コードスニペットは基本的に実物からの抜粋で、要点だけ
抜き出している箇所は `...` で省略している。

---

## 目次

1. [全体アーキテクチャ](#1-全体アーキテクチャ)
2. [`pac-man.py` — エントリポイント](#2-pac-manpy--エントリポイント)
3. [`src/enums.py` — 共有enum](#3-srcenumspy--共有enum)
4. [`src/parse.py` — Config と Parsing](#4-srcparsepy--config-と-parsing)
5. [`src/resources.py` — リソースパス解決](#5-srcresourcespy--リソースパス解決)
6. [`src/maze_loader.py` — 迷路生成のラッパー](#6-srcmaze_loaderpy--迷路生成のラッパー)
7. [`src/character/base.py` — Character(移動物理)](#7-srccharacterbasepy--character移動物理)
8. [`src/character/pacman.py` — Pacman](#8-srccharacterpacmanpy--pacman)
9. [`src/character/ghost.py` — Ghost(AI基底)](#9-srccharacterghostpy--ghostai基底)
10. [`src/character/{blinky,pinky,inky,clyde}.py` — 4匹の個性](#10-srccharacterblinkypinkyinkyclydepy--4匹の個性)
11. [`src/pacgum.py` — パグムの配置・回収](#11-srcpacgumpy--パグムの配置回収)
12. [`src/highscore.py` — ハイスコア永続化](#12-srchighscorepy--ハイスコア永続化)
13. [`src/game_state.py` — PacmanGameContext](#13-srcgame_statepy--pacmangamecontext)
14. [`src/graphic/sprites.py` — スプライト読み込み](#14-srcgraphicspritespy--スプライト読み込み)
15. [`src/graphic/display.py` — メインループ・司令塔](#15-srcgraphicdisplaypy--メインループ司令塔)
16. [`tests/` — テストの構成と意図](#16-tests--テストの構成と意図)
17. [`scripts/generate_horror_sprites.py` — ホラースプライト生成](#17-scriptsgenerate_horror_spritespy--ホラースプライト生成)
18. [パッケージング — Makefile / build_package.sh / pacman.spec](#18-パッケージング--makefile--build_packagesh--pacmanspec)
19. [想定問答クイックリファレンス](#19-想定問答クイックリファレンス)

---

## 1. 全体アーキテクチャ

ゲームループを1ファイルに詰め込まず、単体でテストできる小さな部品を
依存順に積み上げている。

```
enums.py, parse.py(Config)          … 基盤(循環import回避のため最下層)
        ↓
maze_loader.py, resources.py
        ↓
character/base.py (Character)       … 移動物理を1箇所に集約
        ↓
character/pacman.py, character/ghost.py (Ghost)
        ↓
character/{blinky,pinky,inky,clyde}.py   … determine_direction()だけ差し替え
        ↓
pacgum.py, highscore.py, game_state.py   … 単一責務の協調オブジェクト
        ↓
graphic/sprites.py, graphic/display.py (Display)   … 司令塔
        ↓
pac-man.py                           … CLIエントリポイント
```

軸になる設計判断は3つ。

- **`Character` → `Pacman` / `Ghost`**: 移動物理(壁当たり判定・コーナリング)は
  `Character` に1箇所だけ実装。`Pacman` は入力予約を、`Ghost` はAI(ターゲット決定)を
  足すだけで、移動処理そのものには一切触れない。
- **`GhostMode`(enum)がゴーストのAI状態機械を表現**: Scatter/Chase/Frightened/
  Eaten/Waitingの5状態。
- **`GameState`(enum)が`Display.run()`の画面遷移を駆動**: メインメニュー/
  ハイスコア/操作説明/インゲーム/ポーズ/ゲームオーバー・勝利、それぞれが
  `_handle_..._event` / `_render_...` のペアとして実装されている。

---

## 2. `pac-man.py` — エントリポイント

```python
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(...)
    parser.add_argument(
        "config",
        nargs="?" if is_frozen() else None,
        help="path to the JSON configuration file",
    )
    parser.add_argument("--cheat", action="store_true", ...)
    parser.add_argument("--horror", action="store_true", ...)
    return parser.parse_args()
```

- 要件V.1により、ソース実行時は `python3 pac-man.py config.json` の
  ように設定ファイルを**必須**の第1引数として受け取る。
- ただしパッケージ版(PyInstaller)はダブルクリックで起動され引数が
  一切渡らないため、`is_frozen()`(`src/resources.py`)が真の時だけ
  `nargs="?"` にして省略可能にする。省略時は同梱の `config.json` を
  `resource_path()` 経由で使う。

```python
def main() -> None:
    args = _parse_args()
    config_path = args.config or str(resource_path(DEFAULT_CONFIG_NAME))
    config = Parsing.parse_file(config_path)
    game_context = PacmanGameContext(
        config=config,
        lives=config.lives,
        time_remaining=config.level_max_time,
        is_cheat_mode_active=args.cheat,
    )
    Display(game_context, horror_mode=args.horror).run()
```

`Config` → `PacmanGameContext` → `Display` の順に組み立てて渡すだけの薄い層。

### 未処理例外への最終防壁(要件III.1)

```python
if __name__ == "__main__":
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
```

`Display.run()` のメインループ自体は自分で `try/except` を持っている
(§15参照)が、それは**ループの中**の話。設定ファイル読み込みや
`Display` の構築(スプライト読み込みなど)は**ループの外**で起きるので、
ここでも二重に保護している。`SystemExit` だけは素通しする点に注意
(迷路生成が2回とも失敗した時の意図的な終了(§15)を握りつぶさないため)。

---

## 3. `src/enums.py` — 共有enum

```python
class GameState(Enum):
    MAIN_MENU = auto()
    HIGHSCORES = auto()
    INSTRUCTIONS = auto()
    IN_GAME = auto()
    PAUSED = auto()
    LEVEL_CLEARED = auto()   # 現状未使用。レベルクリア時はIN_GAMEのまま次レベルへ進む
    GAME_OVER = auto()
    VICTORY = auto()

class Direction(Enum):
    UP = auto(); DOWN = auto(); LEFT = auto(); RIGHT = auto()

class GhostMode(Enum):
    SCATTER = auto()     # 縄張り巡回
    CHASE = auto()       # 追跡
    FRIGHTENED = auto()  # イジケ(逃亡)
    EATEN = auto()       # 目玉で帰還中
    WAITING = auto()     # 巣で復活待ち

class GhostType(Enum):
    BLINKY = auto(); PINKY = auto(); INKY = auto(); CLYDE = auto()
```

4つの列挙型を1ファイルに集約しているのは、複数モジュールから参照される
値を分散させると循環import(`display.py`が`ghost.py`を、`ghost.py`が
`enums.py`を、という依存が絡み合う)を招きやすいため。

---

## 4. `src/parse.py` — Config と Parsing

要件V.2/V.3(JSON設定・コメント除去・不正値のデフォルトフォールバック・
未知キー無視)を担当する2クラス構成。

### `Config`(pydantic モデル)

```python
class Config(BaseModel):
    highscore_filename: str = "highscores.json"
    seed: int = 42
    lives: int = Field(default=3, ge=1)
    level_max_time: int = Field(default=90, ge=1)
    points_per_pacgum: int = Field(default=10, ge=0)
    points_per_super_pacgum: int = Field(default=50, ge=0)
    points_per_ghost: int = Field(default=200, ge=0)
    level: list[Level] = Field(default_factory=_default_levels)
```

型・範囲(`Field(ge=...)`)の検証をpydanticに一括で任せている。

**bool値の弾き出し**(実際に開発中に踏んだバグの修正、§19参照):

```python
@field_validator("seed", "lives", ..., mode="before")
@classmethod
def reject_boolean_integers(cls, value: object) -> object:
    if isinstance(value, bool):
        raise ValueError("integer settings must not be boolean")
    return value
```

Pythonでは `bool` は `int` のサブクラスなので、`isinstance(True, int)`が
`True`になる。素朴に`int`型として検証するとJSONの`true`がそのまま
`lives`などに通ってしまうため、`mode="before"`(型変換前)の
バリデータで明示的に弾いている。`level`配列内の`id/width/height`にも
同種のチェック(`reject_boolean_level_values`)がある。

**最低10レベルの自動補完**:

```python
@model_validator(mode="after")
def ensure_minimum_levels(self) -> Self:
    missing_count = len(DEFAULT_LEVELS) - len(self.level)
    if missing_count > 0:
        self.level.extend(level.copy() for level in DEFAULT_LEVELS[-missing_count:])
    return self
```

`DEFAULT_LEVELS`はid1〜10の既定サイズ(10x10〜11x11)を持つタプル。
config.jsonで指定したレベル数がそれより少なければ、末尾側から不足分を
継ぎ足す。

### `Parsing`(ファイル読み込み・コメント除去・キー単位フォールバック)

```python
@staticmethod
def _remove_comments(text: str) -> str:
    return '\n'.join(
        line for line in text.splitlines()
        if not line.lstrip().startswith('#')
    )
```

空白を除いた**行頭**が`#`の行だけを除去する(行の途中に`#`があっても
消さない — `test_parser_only_removes_hash_comment_lines`が
`"scores/*keep*/#keep//data.json"`という値が壊れないことを検証している)。

```python
@staticmethod
def parse_file(filename: str) -> Config:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"File not found: {filename}")
        return Config()
    except PermissionError: ...
    except UnicodeDecodeError as e: ...
    except OSError as e: ...

    text = Parsing._remove_comments(text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e: ...
    except ValueError as e: ...

    if not isinstance(data, dict):
        print("Config root must be a JSON object.")
        return Config()

    return Parsing._build_config(data)
```

ファイル欠損・権限エラー・UTF-8として読めない・JSON構文エラー・
ルートがオブジェクトでない、いずれの場合も例外を外に投げず、
メッセージを出して**全デフォルトの`Config()`**にフォールバックする。

```python
@staticmethod
def _build_config(data: dict[str, object]) -> Config:
    config = Config()
    for key, value in data.items():
        if key not in Config.model_fields:
            continue  # 未知キーは無視(要件)
        try:
            config = Config.model_validate({**config.model_dump(), key: value})
        except ValidationError as e:
            default = Config.model_fields[key].get_default(call_default_factory=True)
            print(f"Invalid value for '{key}': {value!r} -> using default {default!r} ...")
    return config
```

ここが設計の肝: `Config`をまるごと検証するのではなく、**キーを1つずつ**
`model_validate`にかけている。あるキーが不正でも、そのキーだけ
デフォルトのままにして他のキーの検証は続ける(「1箇所の不正値で
設定全体が全滅する」ことを防ぐ)。

---

## 5. `src/resources.py` — リソースパス解決

```python
def is_frozen() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")

def resource_root() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[1]

def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)
```

ソース実行時とPyInstallerパッケージ実行時とで、画像や`config.json`の
在り処が変わる。この違いを`resource_root()`一箇所に閉じ込めることで、
`sprites.py`や`pac-man.py`側は「実行形態が何か」を意識しなくてよい。
`sys._MEIPASS`はPyInstallerが実行時展開したディレクトリを指す特殊属性で、
mypyには型情報が無いため`getattr`で取り出している。

---

## 6. `src/maze_loader.py` — 迷路生成のラッパー

要件V.4: 割り当てられた外部パッケージ`A-Maze-ing`(`mazegenerator`)を
**改変せず**、そのインターフェースに合わせて使う。

```python
self.generator = MazeGenerator(
    size=(width, height),
    perfect=False,   # ループのある通路を生成させる(要件)
    seed=seed,
)
```

### ビットマスク → (2N+1)グリッド変換(`get_binary_grid`)

外部ジェネレータの1マスは「4方向の壁ビット」を持つ整数
(ビット0=北・1=東・2=南・3=西。立っている=壁)。これは1マス単位の
当たり判定にそのまま使えないので、元のN×Mマスを「マスの中心」と
「マス間の壁」をそれぞれ1マスとして展開した (2N+1)×(2M+1) の
0/1グリッドに変換する。

```python
binary_grid = [[1] * new_width for _ in range(new_height)]  # 全部いったん壁
for y in range(orig_height):
    for x in range(orig_width):
        cell = maze_data[y][x]
        cy, cx = y * 2 + 1, x * 2 + 1
        binary_grid[cy][cx] = 0                       # マス中心は必ず通路
        if not (cell & 1): binary_grid[cy - 1][cx] = 0  # 北の壁ビットが無ければ開ける
        if not (cell & 2): binary_grid[cy][cx + 1] = 0  # 東
        if not (cell & 4): binary_grid[cy + 1][cx] = 0  # 南
        if not (cell & 8): binary_grid[cy][cx - 1] = 0  # 西
```

これにより「壁の太さ込みで1マス移動=1グリッドセル」という単純な
配列参照だけで、壁判定・BFS・パグム配置すべてを統一的に扱える。

### 中心・四隅の解決(`_find_nearest_open_cell`)

迷路の幾何学的な中心・四隅そのものが壁の可能性があるため、まず
その場所が通路ならそのまま返し、そうでなければ**全マス総当たり**で
ユークリッド距離(の2乗)最小の通路セルを探す。迷路は数十マス四方
止まりなので全探索でも十分速い、という判断。

- `find_center_start_position()`: Pacmanの出現・リスポーン位置(要件:
  「真ん中からスタート」)。
- `find_corner_positions()`: 左上・右上・左下・右下の順で4座標。
  ゴーストの出現位置であり、同じ座標が`pacgum.py`のスーパーパグム
  設置位置としても再利用される。

---

## 7. `src/character/base.py` — Character(移動物理)

Pacman・ゴースト共通の「マス未満で滑らかに移動する」処理を1箇所に
集約したクラス。

### 座標系

`self.x, self.y` はfloat。整数値が**マス目の中心**を表す。
`x=3.4`は3列目マスの中心から右へ0.4マス進んだ位置。

```python
def get_current_grid(self) -> tuple[int, int]:
    return int(self.x + 0.5), int(self.y + 0.5)
```

`+0.5`してint()で切り捨てることで四捨五入相当になる。

主要な定数:
- `speed = 0.095`(マス/フレーム)。Ghostは`__init__`で`*= 0.8`される。
- `radius = 0.45`。当たり判定と描画の両方で共有(食い違うと壁に
  めり込んで見える)。
- `CORNER_CUT_DISTANCE`: 基底クラスでは`0.0`(=Ghost用)。`Pacman`だけ
  `0.08`にオーバーライドし、キー入力への反応を良く見せるため早めに
  曲がり始める。

### 壁当たり判定 `_collides_with_wall`

```python
radius = self.radius if collision_radius is None else collision_radius
left, right = check_x - radius, check_x + radius
top, bottom = check_y - radius, check_y + radius
min_x, max_x = int(left + 0.5), int(right + 0.5)
min_y, max_y = int(top + 0.5), int(bottom + 0.5)

for gy in range(min_y, max_y + 1):
    for gx in range(min_x, max_x + 1):
        if gy < 0 or gy >= height: return True
        if gx < 0 or gx >= len(maze_data[gy]): return True
        if maze_data[gy][gx] == 1: return True
return False
```

キャラクターを「中心`(check_x, check_y)`、一辺`radius*2`の正方形の
当たり判定ボックス」とみなし、重なりうる**全グリッドセル**を洗い出して
1つでも壁または範囲外があれば衝突とみなす。範囲外を壁扱いにするのは
(1)配列範囲外アクセスでのクラッシュ防止、(2)迷路の外へキャラクターが
出ないようにするため、の2つの意味がある。

### `move_forward()` の優先順位

```python
def move_forward(self, maze_data):
    if self.next_direction is not None:
        # 真逆(Uターン)なら交差点を待たず即座に反映
        ...
        self.direction = self.next_direction; self.next_direction = None

    if self._move_during_corner_alignment(maze_data):
        return True
    if self._move_through_turn(maze_data):
        return True
    # 現在の向きへ直進
    ...
```

1. 予約方向が現在の向きの**真逆**(左右逆・上下逆)なら、交差点かどうか
   に関係なく即座に反映する(パックマンらしい即応性のため)。
2. コーナーカット中なら中心線へ寄せながら進む。
3. 交差点に近ければ曲がる。
4. どれにも該当しなければ直進。

### `_move_through_turn`: 曲がり角の処理

`next_direction`が現在の向きと**直交**していて(同じ軸内の切替はUターン
処理で扱うので対象外)、マス中心までの距離が「今フレームで進める距離+
コーナーカットの余裕」以内に近づいたら曲がり始める。

```python
corner_entry_distance = self.speed
if signed_distance_to_center >= 0:
    corner_entry_distance += self.CORNER_CUT_DISTANCE
if distance_to_center > corner_entry_distance:
    return False  # まだ交差点に近づいていない
```

- **中心までまだ遠い場合**(`distance_to_center > self.speed`): 斜めに
  切り込む。
  ```python
  diagonal_step = self.speed / sqrt(2.0)
  next_x, next_y = position_in_direction(x, y, self.direction, diagonal_step)
  next_x, next_y = position_in_direction(next_x, next_y, self.next_direction, diagonal_step)
  ```
  現在の向きと次の向きへ speed を等分に振り分けて斜め移動する
  (三平方の定理で合成した移動量が`speed`になる)。この時点では
  `direction`はまだ確定させない(次フレームも`_move_through_turn`が
  呼ばれ続ける)。
- **中心まで到達しきる場合**: 中心を経由して残りの移動量を新しい向きへ
  消化し、`direction`を確定・`next_direction`をクリアする。

### `_move_during_corner_alignment`: 曲がった後の中心線への収束

上記の斜め切り込みの直後、キャラクターは新しい進行方向の通路の
**中心線から少しズレた位置**にいる。これを毎フレーム少しずつ解消しながら
前進もし続ける処理。

```python
if self.direction in (UP, DOWN):
    alignment_distance = abs(grid_x - self.x)   # 直交軸のズレを測る
else:
    alignment_distance = abs(grid_y - self.y)

alignment_step = min(alignment_distance, self.speed / sqrt(2.0))
forward_step = sqrt(max(0.0, self.speed ** 2 - alignment_step ** 2))
```

1フレームで動ける距離の合計を`speed`に固定したまま、「中心へ寄る成分」
と「前進する成分」を`alignment_step² + forward_step² = speed²`の
関係で配分する。当たり判定には縮小半径
`corner_radius = radius - CORNER_CUT_DISTANCE`を使う(曲がり角の内側は
壁の角に近く、通常半径だと引っかかってしまうため)。

`CORNER_CUT_DISTANCE = 0.0`のGhostでは、この関数は先頭の
`if self.CORNER_CUT_DISTANCE <= 0: return False`で即座に抜けるため、
実質的に一切発生しない。Ghostはマス中心にきっちり到達してから
直角に曲がる。

### `_position_in_direction`

```python
@staticmethod
def _position_in_direction(x, y, direction, distance):
    if direction == UP: y -= distance
    elif direction == DOWN: y += distance
    elif direction == LEFT: x -= distance
    else: x += distance
    return x, y
```
画面座標系(下方向がy増加)に合わせた単純な座標移動のヘルパー。

---

## 8. `src/character/pacman.py` — Pacman

```python
class Pacman(Character):
    CORNER_CUT_DISTANCE = 0.08

    def set_direction(self, direction: Direction) -> None:
        self.next_direction = direction

    def update(self, maze_data: list[list[int]]) -> None:
        self.move_forward(maze_data)
```

プレイヤーキャラクター。移動物理はすべて`Character`任せで、このクラス
自体は「キー入力を`next_direction`として予約する」役割だけを持つ。
即座に向きを変えるのではなく、`Character.move_forward`側のタイミング
(Uターン即時/交差点で曲がる)に従って実際の向き転換が起きる。

---

## 9. `src/character/ghost.py` — Ghost(AI基底)

移動物理は`Character`任せ、`Ghost`は「次にどちらへ進むか」を決める
AI部分(モード管理・BFS経路探索)を担当する。

### モードの状態機械

```python
FRIGHTENED_SPEED_FACTOR = 0.5
EATEN_SPEED_FACTOR = 2.0

def set_mode(self, mode: GhostMode) -> None:
    if mode == self.mode: return
    self.mode = mode
    self._decided_grid = None
    if mode == GhostMode.FRIGHTENED:
        self.speed = self.base_speed * self.FRIGHTENED_SPEED_FACTOR
        self.direction = self._opposite_direction(self.direction)
    elif mode == GhostMode.EATEN:
        self.speed = self.base_speed * self.EATEN_SPEED_FACTOR
    elif mode == GhostMode.WAITING:
        self.speed = 0.0
    else:
        self.speed = self.base_speed
```

モード切替の中身(スケジュール進行・タイマー管理)自体は`Display`側
(§15)が持っていて、`Ghost.set_mode()`は「切り替わった結果、速度と
向きをどう追従させるか」だけを担当する。FRIGHTENEDへ入る瞬間は
向きを反転させる(本家同様、驚いて逆走する演出)。

### 毎フレームの更新

```python
def update(self, pacman, maze_data, ghosts) -> None:
    if self.mode == GhostMode.WAITING:
        return  # 巣で復活を待つ間は動かない
    current_grid = self.get_current_grid()
    if current_grid != self._decided_grid:
        self._decided_grid = current_grid
        self._recent_cells.append(current_grid)
        self.next_direction = self._decide_direction_for_mode(pacman, maze_data, ghosts)
    self.move_forward(maze_data)
```

方向決定は**毎フレームではなく、新しいマスに入った瞬間だけ**行う。
毎フレーム再計算すると、Uターン禁止の判定がキー入力の一瞬の揺らぎで
覆り、交差点でその場で震えるような挙動になってしまう。

```python
def _decide_direction_for_mode(self, pacman, maze_data, ghosts) -> Direction:
    available_directions = self.get_available_directions(maze_data)
    if self.mode == GhostMode.FRIGHTENED:
        return self._decide_frightened_direction(available_directions)
    if self.mode in (GhostMode.SCATTER, GhostMode.EATEN):
        home_x, home_y = self.home_position
        return self.decide_next_direction_bfs(available_directions, maze_data, home_x, home_y)
    return self.determine_direction(pacman, maze_data, ghosts)  # CHASE: サブクラスに委譲
```

- **FRIGHTENED**: `random.choice(available_directions)`でランダム逃走。
- **SCATTER/EATEN**: ターゲットは共通で`home_position`(自分の出現した
  四隅)。BFSで最短方向へ。
- **CHASE**: サブクラスの`determine_direction()`にターゲット計算を委譲。

### Uターン禁止と振動防止

```python
def get_available_directions(self, maze_data) -> list[Direction]:
    opposite = self._opposite_direction(self.direction)
    open_directions = [... 壁でない全方向 ...]
    non_reverse = [d for d in open_directions if d != opposite]
    if not non_reverse:
        return open_directions  # 行き止まりなら逆走も許可

    unvisited = [
        d for d in non_reverse
        if self._get_neighbor_grid(current_grid, d) not in self._recent_cells
    ]
    return unvisited if unvisited else non_reverse
```

- 来た道(現在の向きの逆)は、行き止まりでない限り除外(本家のUターン
  禁止ルール)。
- さらに直近12マスの履歴(`deque(maxlen=12)`)を持ち、可能なら「最近
  訪れていないマス」を優先することで、交差点での行ったり来たりの
  振動を抑える(`tests/test_ghost.py`の
  `test_ghosts_reach_a_stationary_pacman_without_looping_forever`が
  この無限ループバグの回帰テスト)。

### BFSによる経路決定

```python
def decide_next_direction_bfs(self, available_directions, maze_data, target_x, target_y) -> Direction:
    target = self._correct_target_to_open_cell(maze_data, (target_x, target_y))
    if target is None:
        return self.decide_next_direction(available_directions, target_x, target_y)

    distances = self._get_bfs_distances(maze_data, target)
    bfs_direction = self._select_bfs_direction(available_directions, distances)
    if bfs_direction is not None:
        return bfs_direction
    return self.decide_next_direction(available_directions, target[0], target[1])
```

1. `_correct_target_to_open_cell`: ターゲットが壁/迷路外なら、
   総当たりで最寄りの通路セルへ補正する(例: Pinky/Inkyのターゲット
   計算は迷路の外を指すことがある)。
2. `_get_bfs_distances`: ターゲットから各通路マスまでの距離をBFSで
   一括計算。
   ```python
   def _get_bfs_distances(self, maze_data, target):
       if self._bfs_target == target and self._bfs_maze is maze_data:
           return self._bfs_distances  # キャッシュ
       ...
   ```
   各ゴーストが直近の`(ターゲット, 迷路)`ペアでキャッシュを持つ。
   SCATTER/EATEN中はターゲット(home_position)が不変なので実質1回しか
   計算しない。CHASE中はパックマンが動くたびに再計算になるが、
   迷路は数十マス四方でBFS自体は軽く、60FPSでも問題にならない。
3. `_select_bfs_direction`: 隣接候補の中で距離が最小の方向を選ぶ。
   同距離なら現在の進行方向を優先、それも無ければ固定優先順位
   (上>左>下>右、`_tie_breaker`)でタイブレークする。
4. BFSでターゲットに到達できない(孤立領域にいる等)場合は
   `decide_next_direction`(直線距離の貪欲法)にフォールバックする。

---

## 10. `src/character/{blinky,pinky,inky,clyde}.py` — 4匹の個性

共通ロジック(移動・モード管理・BFS・振動防止)はすべて`Ghost`基底に
あり、各サブクラスは**CHASEモード時のターゲット座標を決める
`determine_direction()`1メソッドだけ**をオーバーライドする。

### Blinky(赤・オイカケ、左上出現)

```python
target_x, target_y = pacman.get_current_grid()
return self.decide_next_direction_bfs(available_directions, maze_data, target_x, target_y)
```
パックマンの現在マスへ直接BFS。最もシンプルな直接追跡。

### Pinky(ピンク・マチブセ、右上出現)

```python
target_x, target_y = pacman.get_current_grid()
if pacman.direction == UP:
    target_x -= 4; target_y -= 4   # 本家の有名なバグを意図的に再現
elif pacman.direction == DOWN: target_y += 4
elif pacman.direction == LEFT: target_x -= 4
elif pacman.direction == RIGHT: target_x += 4
```
パックマンの向いている方向の4マス先を先回りする。**上向きの時だけ
「上4マス」ではなく「上4マス+左4マス」ズレる**のは、オリジナルの
Pac-Manに実在する有名なバグをそのまま再現したもの(意図的、実装ミス
ではない)。

### Inky(水色・キマグレ、左下出現)

```python
pivot_x, pivot_y = pacman.get_current_grid()
# Pinky同様、上向き時は上2+左2にズレる(同じ本家バグを再現)
...
blinky = next((g for g in ghosts if g.type == GhostType.BLINKY), None)
if blinky is not None:
    blinky_x, blinky_y = blinky.get_current_grid()
    target_x = 2 * pivot_x - blinky_x
    target_y = 2 * pivot_y - blinky_y
else:
    target_x, target_y = pivot_x, pivot_y
```
パックマン前方2マスを「基準点(pivot)」とし、
`target = 2×pivot − Blinkyの現在地`(Blinkyから基準点へのベクトルを
2倍延長した先)を狙う。`ghosts`リストからBlinkyを検索するため、
Blinkyが見つからなければ基準点そのものにフォールバックする
(Blinky依存の設計だが、単体テストなどBlinkyがいない状況でも
クラッシュしないための保険)。

### Clyde(オレンジ・オトボケ、右下出現)

```python
SHY_DISTANCE = 8
distance_sq = (pacman_x - self_x) ** 2 + (pacman_y - self_y) ** 2
if distance_sq >= self.SHY_DISTANCE ** 2:
    target_x, target_y = pacman_x, pacman_y   # 遠ければBlinky同様に直接追跡
else:
    target_x, target_y = self.home_position   # 近ければ自陣へ逃げる
```
パックマンとの距離が8マス以上ならBlinky同様に直接追跡、8マス未満に
近づくと臆病になって自陣(home_position)へ引き返す。近づいたり離れたり
を繰り返す独特の挙動になる。

---

## 11. `src/pacgum.py` — パグムの配置・回収

要件VI.1/VI.4「ほとんどの通路にドットを置く」に対応。configに個数の
設定キーは**無く**、通路セル数に応じて自動でスケールする。

```python
class Pacgum:
    def __init__(self, maze_data, super_positions, excluded_positions):
        self.super_positions = set(super_positions)
        initial_positions = set(excluded_positions)
        excluded = initial_positions | self.super_positions
        reachable_positions = self._reachable_open_cells(maze_data, initial_positions)
        self.normal_positions = set(
            position for position in self._open_cells(maze_data, excluded)
            if position in reachable_positions
        )
```

- `super_positions`: 四隅(`MazeLoader.find_corner_positions()`と同じ
  座標を共有)。
- `normal_positions`: Pacman初期位置から**到達可能**な通路セル全て
  (四隅・出現地点を除く)。

### なぜ「到達可能」に絞るのか

```python
@staticmethod
def _reachable_open_cells(maze_data, start_positions):
    pending = deque(p for p in start_positions if Pacgum._is_open_cell(maze_data, p))
    ...
    reachable = set(pending)
    while pending:
        x, y = pending.popleft()
        for next_x, next_y in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if Pacgum._is_open_cell(maze_data, (next_x, next_y)) and (next_x, next_y) not in reachable:
                reachable.add((next_x, next_y)); pending.append((next_x, next_y))
    return reachable
```

BFSでPacman初期位置から到達可能な通路セルの集合を先に求める。
外部の迷路生成器が装飾用の孤立セルを含むことがあり、そこに機械的に
パグムを置くとプレイヤーが物理的に回収できずレベルを永久にクリア
できなくなるため。`tests/test_pacgum.py`の
`test_does_not_place_pacgums_on_unreachable_cells`が、実際のレベル1
サイズ(21x21, seed=42)の迷路で「通路セル全体 − 到達可能集合」が
空でない(=孤立セルが実在する)ことまで確認している。

```python
def collect(self, position) -> PacgumKind | None:
    if position in self.normal_positions:
        self.normal_positions.remove(position); return PacgumKind.NORMAL
    if position in self.super_positions:
        self.super_positions.remove(position); return PacgumKind.SUPER
    return None

def is_empty(self) -> bool:
    return self.remaining_count() == 0
```
`collect()`は`set`から取り除くだけの単純な処理。`is_empty()`が
`Display.is_cleared()`(レベルクリア判定)から使われる。得点への
変換(`points_per_pacgum`等)はこのクラスの責務ではなく、呼び出し側
(`Display`)がconfigを見て行う。

---

## 12. `src/highscore.py` — ハイスコア永続化

要件V.5(ファイルエラーに堅牢・上位10件・名前とスコアのバリデーション・
起動時ロード/終了時セーブ)を満たす、外部ライブラリ不要の実装。

```python
MAX_HIGH_SCORES = 10
_NAME_PATTERN = re.compile(r"[A-Za-z0-9 ]{1,10}")

@dataclass(frozen=True)
class HighScoreEntry:
    name: str
    score: int
```
`frozen=True`はランキング内で扱う値を不変にして意図しない書き換えを
防ぐため。

### bool を score として弾く仕組み

```python
@staticmethod
def is_valid_score(score: object) -> TypeGuard[int]:
    return type(score) is int and score >= 0
```
`isinstance(score, int)`ではなく`type(score) is int`で**厳密**に
チェックしている。`bool`は`int`のサブクラスで`isinstance(True, int)`が
`True`になるため、JSONに紛れ込んだ真偽値を誤ってスコアとして受理
しないための対策(`parse.py`の`reject_boolean_integers`と同根の
問題意識)。

### 部分読み飛ばし

```python
def load(self) -> list[HighScoreEntry]:
    try:
        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        self.entries = []; return []
    except (UnicodeDecodeError, OSError, ValueError) as error:
        print(f"Could not load high scores from '{self.path}': {error}")
        self.entries = []; return []

    if not isinstance(data, list):
        print(f"Invalid high-score format in '{self.path}': expected a list")
        self.entries = []; return []

    valid_entries = []
    for index, item in enumerate(data):
        entry = self._parse_entry(item)
        if entry is None:
            print(f"Ignoring invalid high-score entry {index} in '{self.path}'")
            continue
        valid_entries.append(entry)

    self.entries = self._rank(valid_entries)[:MAX_HIGH_SCORES]
    return list(self.entries)
```
ファイル欠損・JSON構文エラー・ルートがリストでない場合は空の
テーブルにフォールバック。リストの中身は`_parse_entry`で1件ずつ
検証し、不正なエントリ(名前が命名規則違反、スコアが非負整数でない
等)だけを読み飛ばして残りは活かす(1件のノイズでファイル全体を
諦めない)。

同点は先着優先: `_rank`はPythonの**安定ソート**(`sorted`は安定)を
利用しているだけで、特別なタイブレーク処理は書いていない。

### アトミック書き込み `save()`

```python
with tempfile.NamedTemporaryFile(
    mode="w", encoding="utf-8",
    prefix=f".{self.path.name}.", suffix=".tmp",
    dir=self.path.parent, delete=False,
) as file:
    temporary_path = Path(file.name)
    json.dump([asdict(e) for e in self.entries], file, ensure_ascii=True, indent=2)
    file.write("\n"); file.flush(); os.fsync(file.fileno())
os.replace(temporary_path, self.path)
```
同じディレクトリに一時ファイルを作って書き込みを完了させ、
`os.fsync`で確実にディスクへ落としてから`os.replace`で本来のパスへ
**アトミックに**置き換える。途中でクラッシュ・強制終了しても、
ファイルが壊れた状態(書きかけJSON)で残ることがない。`finally`で
一時ファイルの掃除も試みるが、失敗しても`pass`で握りつぶす
(致命的ではないため)。

---

## 13. `src/game_state.py` — PacmanGameContext

```python
@dataclass
class PacmanGameContext:
    config: Config
    state: GameState = GameState.MAIN_MENU
    current_level: int = 1
    score: int = 0
    lives: int = 3
    time_remaining: float = 90.0
    is_cheat_mode_active: bool = False
    CHEAT_EXTRA_LIVES = 2
```

レベル遷移で`Display`が丸ごと再構築されても**生き残るべき値**
(スコア・残機・タイマー・現在の`GameState`・チートフラグ)を1箇所に
まとめたdataclass。`Display._load_level()`は迷路・Pacman・ゴースト・
パグムを毎レベル作り直すが、`game_context`は同じインスタンスを
使い回すので、レベルをまたいでもスコアが消えたりリセットされたり
しない。

```python
def reset_for_new_game(self) -> None:
    self.state = GameState.IN_GAME
    self.current_level = 1
    self.score = 0
    self.lives = self.config.lives
    if self.is_cheat_mode_active:
        self.lives += self.CHEAT_EXTRA_LIVES
    self.time_remaining = self.config.level_max_time

def lose_life(self) -> None:
    self.lives -= 1
    if self.lives <= 0:
        self.state = GameState.GAME_OVER

def add_score(self, points: int) -> None:
    if points > 0:
        self.score += points
```
`add_score`が`points > 0`の時だけ加算するのは、誤って0以下の値が
渡ってもスコアが減らないようにする安全策(要件: スコアは減少しない)。

---

## 14. `src/graphic/sprites.py` — スプライト読み込み

```python
ASSET_DIR = resource_path("assets", "sprites")
HORROR_ASSET_DIR = resource_path("assets", "sprites_horror")

SPRITE_FILENAMES: dict[str, str] = {
    "wall": "wall.png", "pacman_open": "pacman_open.png", ...
    "blinky": "ghost_blinky.png", ..., "frightened": "ghost_frightened.png",
    "eaten": "ghost_eaten.png",
}

class SpriteSet:
    def __init__(self, asset_dir: Path = ASSET_DIR) -> None:
        self._originals = {
            key: pygame.image.load(str(asset_dir / filename)).convert_alpha()
            for key, filename in SPRITE_FILENAMES.items()
        }
        self._scaled_cache: dict[tuple[str, int], pygame.Surface] = {}

    def get(self, key: str, cell_size: int) -> pygame.Surface:
        cache_key = (key, cell_size)
        cached = self._scaled_cache.get(cache_key)
        if cached is not None:
            return cached
        scaled = pygame.transform.smoothscale(self._originals[key], (cell_size, cell_size))
        self._scaled_cache[cache_key] = scaled
        return scaled
```
全ての見た目要素はPNGファイルから描画される(円や矩形の直接描画では
ない)。元画像は起動時に1度だけ読み込み、`(種類, セルサイズ)`の組み
合わせごとに拡縮結果をキャッシュする。迷路のセルサイズはレベルに
よって変わる(`_cell_size_for_maze`)ため、同じ元画像でも毎回違う
サイズへ拡縮する必要があるが、毎フレーム拡縮するのは無駄なので
キャッシュしている。`asset_dir`を引数化してあるのは、`--horror`用に
`HORROR_ASSET_DIR`へ差し替えられるようにするため(テストでもダミー
画像ディレクトリに差し替え可能)。

---

## 15. `src/graphic/display.py` — メインループ・司令塔

pygameウィンドウ・入力処理・状態ごとの描画・当たり判定・HUD・
チートモードを統括する、全体の中で最も大きい(1046行)モジュール。

### 主要な定数

```python
SCATTER_CHASE_SCHEDULE = ((GhostMode.SCATTER, 7.0), (GhostMode.CHASE, 20.0))
FRIGHTENED_DURATION = 6.0
EATEN_RESPAWN_WAIT = 5.0
CHEAT_SPEED_FACTOR = 1.5
CHOMP_INTERVAL = 0.1
PACMAN_CHOMP_FRAMES = ("pacman_closed", "pacman_half", "pacman_open", "pacman_half")
MAX_WINDOW_SIZE = 2000; MAX_CELL_SIZE = 45; MIN_CELL_SIZE = 10
```

### `_load_level()`: 1レベル分の初期化

新規ゲーム開始時だけでなく、レベルクリア時(`advance_to_next_level`)
にも呼ばれる共通処理。迷路生成→ワープトンネルの穴あけ→Pacman/
ゴースト/パグムの再配置→ゴーストモードのリセット→ウィンドウサイズ
再計算、までを1メソッドで行う。`game_context`(スコア・残機など)には
一切触れないため、レベルをまたいでもスコア・残機は保持される。

```python
seed = self.config.seed if self.current_level_index == 0 else 0
self.maze_loader, self.maze_data = self._build_maze(level["width"], level["height"], seed)
...
start_x, start_y = self.maze_loader.find_center_start_position()
self.tunnel_row = start_y
self.maze_data[start_y] = [0] * len(self.maze_data[start_y])  # トンネル用に丸ごと開通
```
レベル1(`current_level_index == 0`)だけ固定seed、以降は`seed=0`
(`MazeGenerator`が`seed<=0`の時に真の乱数を使う仕様)。

### `_build_maze`: 迷路生成失敗時のフォールバック(要件V.4)

```python
try:
    loader = MazeLoader(width=width, height=height, seed=seed)
    return loader, loader.get_binary_grid()
except Exception as error:
    print(f"Maze generation failed for size {width}x{height}: {error}")

try:
    loader = MazeLoader(width=fallback_width, height=fallback_height, seed=seed)  # レベル1既定サイズで再試行
    return loader, loader.get_binary_grid()
except Exception as fallback_error:
    print(f"Fallback maze generation also failed: {fallback_error}")
    pygame.quit()
    raise SystemExit(1) from fallback_error
```
指定サイズで生成を試み、失敗したらレベル1既定サイズで再試行、それも
失敗したらメッセージを出して`SystemExit(1)`(迷路が無いと起動を
続行できないため、ここだけは例外的に終了させる)。

### ゴーストモードの管理

```python
def _apply_scheduled_mode(self) -> None:
    mode, _ = SCATTER_CHASE_SCHEDULE[self.mode_schedule_index]
    for ghost in self.ghosts:
        if ghost.mode not in (FRIGHTENED, EATEN, WAITING):
            ghost.set_mode(mode)

def _end_frightened(self) -> None:
    mode, _ = SCATTER_CHASE_SCHEDULE[self.mode_schedule_index]
    for ghost in self.ghosts:
        if ghost.mode == FRIGHTENED:
            ghost.set_mode(mode)
```
`_apply_scheduled_mode`はFRIGHTENED/EATEN/WAITING中のゴーストを
意図的にスキップする(スケジュール進行がそれらの特殊状態を上書き
しないため)。だからFRIGHTENED終了時に**同じ関数を呼ぶと対象自身が
除外されて永久にFRIGHTENEDのまま止まる**ため、専用の`_end_frightened`
を用意している。

```python
def _advance_ghost_modes(self, delta_time: float) -> None:
    self._advance_waiting_ghosts(delta_time)
    if self.frightened_timer > 0:
        self.frightened_timer -= delta_time
        if self.frightened_timer <= 0:
            self.frightened_timer = 0.0
            self._end_frightened()
        return
    self.mode_timer += delta_time
    _, duration = SCATTER_CHASE_SCHEDULE[self.mode_schedule_index]
    if self.mode_timer >= duration:
        self.mode_timer = 0.0
        self.mode_schedule_index = (self.mode_schedule_index + 1) % len(SCATTER_CHASE_SCHEDULE)
        self._apply_scheduled_mode()
```
Scatter(7秒)⇄Chase(20秒)を交互に繰り返すスケジュール。FRIGHTENED中は
このスケジュール進行自体を一時停止し(`return`で以降の処理をスキップ)、
終了後に復帰する。

```python
def _resolve_eaten_ghosts(self) -> None:
    for ghost in self.ghosts:
        if ghost.mode == EATEN and ghost.get_current_grid() == ghost.home_position:
            ghost.set_mode(WAITING)
            ghost.wait_timer = EATEN_RESPAWN_WAIT

def _advance_waiting_ghosts(self, delta_time: float) -> None:
    mode, _ = SCATTER_CHASE_SCHEDULE[self.mode_schedule_index]
    for ghost in self.ghosts:
        if ghost.mode != WAITING: continue
        ghost.wait_timer -= delta_time
        if ghost.wait_timer <= 0:
            ghost.set_mode(mode)
```
EATENゴーストが自分の巣(四隅)に帰り着いたらWAITINGへ遷移し、
5秒(`EATEN_RESPAWN_WAIT`)待ってからScatter/Chaseへ復帰する。

### 当たり判定 `_check_ghost_collisions`

```python
for ghost in self.ghosts:
    if ghost.mode in (EATEN, WAITING): continue
    dx = self.pacman.x - ghost.x; dy = self.pacman.y - ghost.y
    contact_distance = self.pacman.radius + ghost.radius
    if dx*dx + dy*dy >= contact_distance*contact_distance: continue

    if ghost.mode == FRIGHTENED:
        ghost.set_mode(EATEN)
        self.game_context.add_score(self.config.points_per_ghost)
    elif not self.game_context.is_cheat_mode_active:
        self._handle_life_lost()
        return
```
円同士(半径の和)の距離判定。EATEN/WAITING中は判定対象外。
FRIGHTENED中のゴーストに触れると食べて加点、通常状態でチートモード
でなければライフロス。

### ワープトンネル `_apply_tunnel_wrap`

```python
def _apply_tunnel_wrap(self, character: Character) -> None:
    if round(character.y) != self.tunnel_row:
        return
    width = len(self.maze_data[0])
    if character.direction == LEFT and character.x <= character.radius:
        character.x = float(width - 1)
    elif character.direction == RIGHT and character.x >= width - 1 - character.radius:
        character.x = 0.0
```
迷路範囲外は`Character._collides_with_wall`が常に壁として扱うため、
座標が実際に`x < 0`や`x >= width`になることは無い。だから
「範囲外に出たら戻す」という判定は発火せず、キャラクターは端で物理的に
ブロックされて詰まってしまう。このメソッドは範囲外に出るのを待たず、
**端のマスで外向きに壁へ突き当たった時点**(`x <= radius`かつ
`direction == LEFT`など)でワープさせる。呼び出しは`_render_game`内で
`pacman.update()`/`ghost.update()`の**直後**(`_collides_with_wall`に
よる物理的なブロックが先に起きた後)に行われる。

### `_render_game`: 1フレームの処理順

```
1. 壁を描画
2. delta_time計算 → 残り時間減算。0以下ならライフロス処理(打ち切りうる)
3. ゴーストモードのスケジュールを進める(_advance_ghost_modes)
4. Pacman移動 → トンネル処理 → チョンプアニメのタイマー更新
5. 現在マスのパグムを回収 → 加点 / スーパーならゴーストをイジケさせる
6. 全回収済みなら次レベルへ進み、このフレームの残りは打ち切り
7. (凍結中でなければ)ゴースト移動 → トンネル処理 → 巣復帰処理
8. Pacman⇔ゴーストの当たり判定(ライフロスで打ち切りうる)
9. パグム・Pacman・ゴースト・HUDを描画
```
更新と描画を1メソッドにまとめているのは、ライフロスやレベルクリア
など「フレームの途中で処理を打ち切りたい」ケースが多く、更新と描画を
分離すると打ち切りタイミングの整合(描画だけ古い状態でやってしまう、
等)を取る方がかえって複雑になるための判断。

### チートモード(`--cheat`)

| 効果 | 実装箇所 |
|---|---|
| 無敵 | `_check_ghost_collisions`で`is_cheat_mode_active`の時だけライフロス処理をスキップ |
| 残機+2 | `PacmanGameContext.reset_for_new_game`で`CHEAT_EXTRA_LIVES`加算 |
| 速度×1.5 | `_load_level`でPacman生成直後に`speed *= CHEAT_SPEED_FACTOR` |
| `F`凍結 / `N`レベルスキップ | `_handle_event`のIN_GAME分岐、チートフラグの時だけ受け付ける |
| スコア非記録 | `_submit_highscore`冒頭でチート中なら保存せずメッセージだけ出す |

### 状態機械としての`_handle_event` / `_render_...`

`GameState`enumの値ごとに、入力処理(`_handle_..._event`)と描画
(`_render_...`)のペアが対応する。`run()`のメインループは現在の
`state`を見てこのペアを呼び分けるだけで、フラグを分散させず遷移を
明示的に保っている。

```python
def run(self) -> None:
    running = True
    try:
        while running:
            for event in pygame.event.get():
                if not self._handle_event(event):
                    running = False
            if not running: break
            state = self.game_context.state
            if state == MAIN_MENU: self._render_main_menu()
            elif state == HIGHSCORES: self._render_highscores()
            elif state == INSTRUCTIONS: self._render_instructions()
            elif state == IN_GAME: self._render_game()
            elif state == PAUSED: self._render_pause()
            elif state in END_STATES: self._render_end_screen()
            self.clock.tick(60)
            pygame.display.flip()
    except Exception as error:
        print(f"Unexpected error, shutting down cleanly: {error}")
    finally:
        pygame.quit()
```
要件III.1により、ループ全体を`try/except Exception`で囲み、`finally`
で必ず`pygame.quit()`を呼ぶ(正常終了・異常終了どちらでも)。

---

## 16. `tests/` — テストの構成と意図

各主要モジュールに対応するテストファイルが`tests/`にある。
特に押さえておきたい回帰テストを挙げる。

- **`test_character.py`**: Pacmanのコーナーカット物理(斜め切り込み量が
  `speed`ちょうどになること、壁がある時は曲がらないこと)、不正な形の
  迷路データ(`[]`や`[[0,0],[]]`のようなガタガタな配列)を壁扱いにして
  クラッシュしないこと。
- **`test_ghost.py`**:
  - `test_ghosts_reach_a_stationary_pacman_without_looping_forever`:
    静止したパックマンに対し、四隅から出発した4匹全員が5000フレーム
    以内に到達できることを検証。小さな輪っか状の通路を無限に周回する
    バグ(振動防止機構が無いと発生しうる)の回帰テスト。
  - `test_inky_target_uses_blinky_position`: Inkyのターゲットが
    「基準点そのもの」ではなく「Blinkyから基準点への延長線上」に
    なることを、旧実装だと壊れる具体的な配置(パックマン(10,10)右向き、
    Inkyを基準点(12,10)に置く)で検証。
  - `test_blinky_prefers_going_straight_when_bfs_paths_are_equal`:
    BFSの同距離タイブレークで現在の進行方向が優先されること。
- **`test_display.py`**: レベル進行・ウィンドウサイズの自動計算・
  迷路生成失敗時のフォールバック・スーパーパグムでのFRIGHTENED誘発・
  チートモードの無敵/凍結/レベルスキップ/スコア非記録・トンネル
  ワープの端条件・`run()`が未処理例外を外に漏らさないこと
  (`test_run_never_lets_an_unexpected_exception_escape`)など、
  司令塔の統合的な振る舞いを広くカバーしている。
- **`test_parse.py`**: bool値が整数設定に化けないこと(全設定キーを
  網羅的にパラメータ化)、コメント除去が行の途中の`#`を消さないこと、
  非UTF-8ファイルや巨大すぎる整数(JSON構文としては妥当だが
  パースエラーになるケース)でも安全にフォールバックすること。
- **`test_highscore.py`**: 同点は先着優先、上位10件のみ保持、名前の
  命名規則違反(空文字・長すぎる・記号・非ASCII)を`ValueError`で
  弾くこと、保存失敗時(存在しないディレクトリ)でもクラッシュせず
  再試行できること。
- **`test_pacgum.py`**: 到達不能な孤立セルにパグムを置かないこと。
- **`test_resources.py`**: ソース実行時とPyInstallerパッケージ実行時
  (`sys.frozen`/`sys._MEIPASS`をモンキーパッチで模擬)でパス解決が
  切り替わること。
- **`test_sprites.py`**: 宣言した全スプライトキーが読み込めること、
  同じ`(key, size)`の組み合わせはキャッシュされ同一オブジェクトが
  返ること。
- **`test_maze.py`**: 外部パッケージ`mazegenerator`自体が
  `perfect=False`で迷路データを返せること(自チームのコードではなく
  外部依存の疎通確認)。

多くのテストが`monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")`で
pygameをヘッドレス(実ウィンドウを開かない)動作させている点も、
CI環境で動かす上での工夫として説明できるようにしておくとよい。

---

## 17. `scripts/generate_horror_sprites.py` — ホラースプライト生成

`--horror`用の`assets/sprites_horror/`一式を、pygameの図形描画
(円・多角形・線)だけで**手続き的に生成する**スクリプト。外部の
画像素材や画像生成AIは使っていない。

```python
def bloodshot_eye(surf, center, radius, rng, hollow=False) -> None:
    """血走った目(または虚ろな眼窩)を描く。"""
    ...
    for _ in range(5):
        angle = rng.uniform(0, math.tau)
        edge = (cx + cos(angle)*radius, cy + sin(angle)*radius)
        mid = (cx + cos(angle)*radius*rng.uniform(0.25,0.55), ...)
        pygame.draw.line(surf, VEIN, edge, mid, 2)   # 血管を放射状に描く
    ...

def make_pacman(mouth_half_angle: float, rng_seed: int) -> pygame.Surface:
    ...
    # 口の部分を白いマスクで描いてからBLEND_RGBA_SUBで減算し、透明にくり抜く
    surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
```

- `bloodshot_eye`/`crack_line`/`drip`/`jagged_teeth`のような小さな
  描画部品(血管・ひび割れ・血だまり・尖った牙)を組み合わせて、
  Pacman・4種のゴースト・フライトゴースト・目玉・パグム・壁の全12種を
  生成する。
- 同じファイル名・同じ128x128解像度で`assets/sprites/`と対になって
  いるため、`SpriteSet`側のコードは通常版/ホラー版のどちらでも
  そのまま動く(`graphic/sprites.py`の`SPRITE_FILENAMES`が両方の
  ディレクトリで共通)。
- 生成物はリポジトリにコミット済みで、通常のプレイでこのスクリプトを
  再実行する必要はない(差し替えたい時だけ実行する)。

---

## 18. パッケージング — Makefile / build_package.sh / pacman.spec

要件VII: Steam/Itch.ioのようなプラットフォームから起動できる
パッケージを作成し、そのビルド手段をリポジトリのルートに置く。

### `Makefile`

```make
install:  uv sync
run:      uv run python $(MAIN_SCRIPT) $(CONFIG)
debug:    uv run python -m pdb $(MAIN_SCRIPT) $(CONFIG)
clean:    __pycache__・.mypy_cache・build/dist などを削除
fclean:   clean に加えて .venv も削除
lint:     flake8 . && mypy --disallow-untyped-defs --check-untyped-defs .
lint-strict: flake8 . && mypy --strict .
test:     PYTHONPATH=. uv run python -m pytest tests/ -v
package:  ./build_package.sh
```
要件2で必須の`install`/`run`/`debug`/`clean`/`lint`ターゲットに加え、
任意の`lint-strict`(より厳格な`mypy --strict`)、`test`、`package`
(パッケージング)を備える。

### `build_package.sh`

```sh
uv sync --group package                              # PyInstallerを追加インストール
uv run pyinstaller pacman.spec --noconfirm --clean
```
PyInstallerは通常の開発では不要な依存なので、`--group package`という
別グループに分けてある(`make install`では入らない)。

### `pacman.spec`

```python
analysis = Analysis(
    ['pac-man.py'],
    datas=[
        ('assets/sprites', 'assets/sprites'),
        ('assets/sprites_horror', 'assets/sprites_horror'),
        ('config.json', '.'),
        ('INSTRUCTIONS.txt', '.'),
    ],
    hiddenimports=['mazegenerator'],
    excludes=['pytest', 'mypy', 'flake8'],
    ...
)
executable = EXE(..., name='pacman', console=False, ...)
```

- `datas`: (コピー元, 展開先)のペア。実行時はPyInstallerがこの構造で
  `sys._MEIPASS`以下に展開し、`src/resources.py`の`resource_root()`が
  そのパスを解決する(§5と対応)。`config.json`を同梱しているのは、
  `pac-man.py`の「パッケージ版なら引数を省略できる」の受け皿。
- `hiddenimports=['mazegenerator']`: PyInstallerは`import`文を静的解析
  して依存を自動検出するが、動的import(`__import__`やプラグイン的な
  読み込み)やC拡張を含むパッケージは検出漏れが起きうる。外部パッケージ
  `mazegenerator`を明示的に指定することで、静的解析で見つからなくても
  確実に同梱させている。
- `console=False`: ゲームなのでターミナルウィンドウを出さない
  (エラーは`Display`側で標準出力/画面に出す設計、§15の`run()`参照)。

配布先ごとの手順: Itch.ioなら`dist/pacman`を`INSTRUCTIONS.txt`と共に
zipしてunlistedビルドとしてアップロード、Steamなら同じ実行ファイルを
ビルドの起動対象として登録する。

---

## 19. 想定問答クイックリファレンス

(詳細は口頭試問と別途作成したArtifact「Packman 実装ノート」も参照)

- **「(2N+1)グリッドにした理由は?」** → 外部生成器のセルは壁ビット
  付きの粗い表現で、1マス単位の当たり判定にそのまま使えないため。
  中心とマス間の壁をそれぞれ1グリッドセルとして展開し、「1マス移動=
  1グリッドセル」で統一的に扱えるようにした。
- **「BFSは毎フレーム重くないか?」** → 各ゴーストが直近の
  `(ターゲット, 迷路)`ペアでキャッシュを持ち、SCATTER/EATEN中は
  ターゲット不変なので実質1回のみ。CHASE中は再計算になるが迷路が
  小さくBFS自体が軽い。
- **「Pinky/Inkyの上向き時のズレはバグか?」** → 意図的な再現。本家
  Pac-Manに実在する有名なバグをそのまま踏襲している。
- **「設定ファイルが壊れていたら?」** → ファイル欠損/UTF-8エラー/
  JSON構文エラー/ルートがオブジェクトでない場合は全デフォルトへ、
  キー単位の不正値はそのキーだけデフォルトへフォールバックし、
  他のキーの検証は続行。未知のキーは無視。
- **「なぜbool値を明示的に弾いているのか?」** → Pythonでは`bool`が
  `int`のサブクラスで`isinstance(True, int)`が`True`になるため、
  素朴な型チェックだとJSONの`true`が整数設定・スコアとして通って
  しまう。実際に開発中に踏んだバグで、`parse.py`と`highscore.py`の
  両方で対策している。
- **「迷路生成パッケージは改変していないと言えるか?」** →
  `package/`のwheelをそのまま依存に加えているだけで、ソースは
  一切変更していない。`MazeLoader`が向こうのインターフェース
  (`MazeGenerator(size=..., perfect=False, seed=...)`)に合わせて
  呼び出し、戻り値の変換だけをこちら側で行っている。
- **「タイムリミットに達したら?」** → 要件上は自由裁量。この実装
  ではライフを1つ失い、Pacman・ゴーストを初期配置に戻して同じ
  レベルを最初からやり直す。
- **「なぜ更新と描画を1メソッド(`_render_game`)にまとめたか?」** →
  ライフロスやレベルクリアなどフレーム途中で打ち切りたいケースが
  多く、分離すると打ち切りタイミングの整合を取る方が複雑になるため。
- **「パッケージ版とソース実行の違いは?」** → 設定ファイル引数が
  パッケージ版のみ省略可能(`is_frozen()`で分岐)、リソースパスの
  基準ディレクトリが`sys._MEIPASS`かリポジトリ直下かで切り替わる
  (`resources.py`)。ゲームロジック自体に差はない。
