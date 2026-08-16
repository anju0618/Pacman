*This project has been created as part of the 42 curriculum by amakino, takawaka.*

# Packman

[English](#english) | [日本語](#日本語)

---

## English

### Description

Packman is a Pac-Man clone built for the 42 school "Packman" project. Written in
Python 3 with `pygame`, it generates a fresh, loop-filled maze every level using a
partner team's external `A-Maze-ing` generator package, and reimplements the four
ghosts' classic personalities (Blinky, Pinky, Inky, Clyde) with Scatter / Chase /
Frightened / Eaten AI modes. The game persists a top-10 high score table, supports
at least 10 levels per run, and ships a cheat mode for peer review.

### Instructions

**Running the game**

```sh
make install   # uv sync — installs dependencies into .venv
make run       # uv run python pac-man.py config.json
```

or directly:

```sh
python3 pac-man.py <config.json> [--cheat]
```

- `<config.json>` (required): path to a JSON configuration file (see Configuration
  below).
- `--cheat` (optional): enables cheat mode for peer review.

Other Makefile targets:

- `make debug` — runs the game under `pdb`.
- `make lint` / `make lint-strict` — `flake8` + `mypy`.
- `make test` — runs the `pytest` suite.
- `make clean` / `make fclean` — remove caches, or remove the virtual environment
  as well.

**Controls**

| Key | Action |
| --- | --- |
| Arrow keys / WASD | Move Pac-Man |
| Enter | Confirm a menu selection |
| Esc | Pause / go back |
| M (while paused) | Return to the main menu |

**Cheat mode (`--cheat`)**

- Invincibility: ghosts can no longer cost you a life.
- +2 starting lives.
- 1.5x Pac-Man speed.
- `F`: freeze / unfreeze all ghosts.
- `N`: instantly clear the current level.

**Goal**

Eat every pacgum on a level to clear it. Eating a super pacgum makes every ghost
edible for a few seconds — eat them for bonus points before they recover.
Touching a dangerous ghost costs a life; losing all lives ends the game. Clearing
every level wins the game.

### Configuration

The game is configured with a single JSON file passed as the first command-line
argument (see `config.json` for a working example). Lines starting with `#` are
treated as comments and stripped before parsing. Unknown keys are ignored, and any
missing or invalid value falls back to a safe default with a message printed to
the console — a malformed config file never crashes the game.

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `highscore_filename` | string | `"highscores.json"` | Where the high score table is persisted. |
| `seed` | int | `42` | Fixed seed for level 1's maze. |
| `lives` | int (≥1) | `3` | Starting lives. |
| `level_max_time` | int (≥1) | `90` | Seconds allowed per level before it counts as a life lost. |
| `pacgum` | int (≥1) | `42` | Target number of normal pacgums per level (clamped to the corridors actually available). |
| `points_per_pacgum` | int (≥0) | `10` | Score for eating a normal pacgum. |
| `points_per_super_pacgum` | int (≥0) | `50` | Score for eating a super pacgum. |
| `points_per_ghost` | int (≥0) | `200` | Score for eating a frightened ghost. |
| `level` | array of `{id, width, height}` | — | Per-level maze dimensions. |

The `level` array only needs as many entries as you want to customize; it is
automatically padded with built-in defaults up to a minimum of 10 levels
(`DEFAULT_LEVELS` in `src/parse.py`). Level 1 always uses the fixed `seed`; every
later level is generated with a random seed.

### High Score

`src/highscore.py` implements a small, dependency-free persistence layer:

- Scores are stored as a JSON array of `{"name": ..., "score": ...}` objects at
  the path configured by `highscore_filename`.
- Only the top 10 scores are kept; on a tie, the earlier entry wins.
- Player names must be 1–10 ASCII letters, digits, or spaces.
- The table is loaded once when the game starts, and re-saved (atomically, via a
  temporary file + `os.replace`) whenever a new score is submitted.
- A missing file, corrupt JSON, or invalid entries never crash the game — the
  loader logs a message and falls back to an empty table.
- On Game Over or Victory, the game prompts for a name and shows the updated top
  10.

### Maze Generation

Mazes are produced by the `A-Maze-ing` package (`mazegenerator`, distributed as
the wheel in `package/`), which was assigned by another team and is used
unmodified. `src/maze_loader.py` wraps it:

- `MazeLoader` calls `MazeGenerator(size=(width, height), perfect=False,
  seed=seed)` so the generator leaves loops in the maze instead of a perfect
  tree, matching the Pac-Man requirement.
- `get_binary_grid()` converts the generator's compact cell/wall-bitmask
  representation into a `0`/`1` grid (`0` = corridor, `1` = wall) that the rest
  of the game consumes directly.
- `find_center_start_position()` / `find_corner_positions()` locate the nearest
  open cell to the maze's center (Pac-Man's spawn/respawn point) and to its four
  corners (the ghosts' home corners, and the super pacgum locations).
- Level 1 is generated with the fixed `seed` from the config; every later level
  passes `seed=0`, which the generator treats as "use true randomness".
- Because the generated maze always walls off its outer boundary,
  `Display._load_level()` additionally opens Pac-Man's spawn row all the way
  across as a **warp tunnel**: reaching either end of that row teleports you to
  the opposite side (`Display._apply_tunnel_wrap`).

### Implementation

Key modules, roughly in dependency order:

- `src/enums.py` — `GameState`, `Direction`, `GhostMode`, `GhostType`.
- `src/parse.py` — `Config` (a validated `pydantic` model) and `Parsing`
  (comment-stripping JSON loader with per-key fallback to defaults).
- `src/maze_loader.py` — wraps the external maze generator (see Maze
  Generation).
- `src/character/base.py` — shared movement/collision physics (`Character`):
  sub-cell movement, wall collision via a shared hit-radius, corner-cutting.
- `src/character/pacman.py` — player input buffering on top of `Character`.
- `src/character/ghost.py` — `Ghost` base class: BFS pathfinding toward a target
  cell, anti-oscillation short-term memory, and the `GhostMode` state machine
  (Scatter/Chase/Frightened/Eaten) with per-mode speed changes.
- `src/character/{blinky,pinky,inky,clyde}.py` — one personality each, only
  responsible for picking a Chase-mode target cell; mode switching itself lives
  in the base class.
- `src/pacgum.py` — `Pacgum`: places normal/super pacgums on the open cells of a
  maze (excluding the spawn point and the four corners) and tracks which remain.
- `src/highscore.py` — persistent top-10 table (see High Score).
- `src/game_state.py` — `PacmanGameContext`: score, lives, timer, current
  `GameState`, cheat flag.
- `src/graphic/display.py` — `Display`: the pygame window, main loop,
  state-machine rendering (menu / highscores / instructions / in-game / paused /
  game-over / victory), the Scatter/Chase schedule and Frightened timer,
  collision handling, HUD, and cheat-mode effects.
- `pac-man.py` — CLI entry point (`argparse`), wires a parsed `Config` into a
  `PacmanGameContext` and hands it to `Display`.

### General Software Architecture

The codebase is organized around a small number of composable, independently
testable pieces rather than one large game-loop file:

- **`Character` → `Pacman` / `Ghost`**: shared movement physics live once in the
  base class; `Ghost` adds AI, and each of the four ghost subclasses overrides a
  single method (`determine_direction`) to express its personality, so behaviour
  differences never touch movement code.
- **`GameState` (enum) drives `Display.run()`**: every screen (menu, highscores,
  instructions, in-game, paused, game over/victory) is a pair of
  `_handle_..._event` / `_render_...` methods dispatched on the current
  `GameState`, keeping the finite-state machine explicit instead of scattering
  flags.
- **`PacmanGameContext`** owns everything that must survive across a `Display`
  reload (score, lives, timer, cheat flag) so that advancing a level or losing a
  life never has to reconstruct state that should persist.
- **Composition over inheritance for gameplay systems**: `MazeLoader`, `Pacgum`,
  and `HighScoreSystem` are independent, single-responsibility collaborators
  that `Display` orchestrates each frame, rather than being mixed into a god
  object.
- **Config validation is centralized**: `pydantic` enforces field types/ranges
  once in `Config`; `Parsing` guarantees that a broken config file degrades to
  safe defaults instead of raising.
- Every module has type hints and is checked with `mypy
  --disallow-untyped-defs --check-untyped-defs` (and optionally `mypy --strict`)
  plus `flake8`, both wired into `make lint` / `make lint-strict`.

### Project Management

Project management artifacts live in `management/`:

- `management/TASK.md` — the full requirement breakdown with a running
  Done/Todo status.
- `management/gant.md` — a per-day work log plus a Mermaid Gantt chart of task
  ownership and timing between the two team members.
- The git history itself documents iterative progress, including several
  AI-assisted review/bugfix passes (see Resources below).

### Resources

**AI usage**

This project was built with heavy use of **Claude Code** (Anthropic) as a
pair-programming/reviewing tool throughout development, not just for one-off
fixes. Concretely, Claude Code was used to:

- review the codebase and fix bugs (ghost AI infinite-looping, a `NameError`
  typo, broken tests, config defaults, wall-collision rendering, etc.);
- design and implement whole subsystems end-to-end (pacgum placement/collection,
  ghost mode switching, ghost-player collision, the warp tunnel, the in-game
  HUD, and the cheat mode effects);
- write and update the accompanying unit tests.

All AI-assisted changes are visible in the git history and summarized in
`management/TASK.md` / `management/gant.md`.

**Pac-Man references**

- [パックマン 解析プログラム動画から見る 追跡アルゴリズム](https://www.webcyou.com/?p=10440)
  — ghost-chasing algorithm research.
- [追跡アルゴリズムを考える パックマンをJavaScript/TypeScriptでつくる (その5)](https://lets-csharp.com/pacman-js-approach/)

---

## 日本語

### 概要

Packmanは、42のカリキュラム課題「Packman」向けに作られたパックマンのクローンです。
Python 3と`pygame`で実装しており、他チームが提供する外部の迷路生成パッケージ
`A-Maze-ing`を使ってレベルごとにループ構造のある迷路を生成します。4匹のゴースト
(Blinky/Pinky/Inky/Clyde)はそれぞれ本家の個性を再現し、Scatter(縄張り巡回)/
Chase(追跡)/Frightened(イジケ)/Eaten(目玉で帰還)のAIモードを切り替えます。
上位10件のハイスコアを永続化し、最低10レベルの進行に対応し、ピアレビュー用の
チートモードも備えています。

### 遊び方

**実行方法**

```sh
make install   # uv sync — 依存関係を.venvにインストール
make run       # uv run python pac-man.py config.json
```

または直接:

```sh
python3 pac-man.py <config.json> [--cheat]
```

- `<config.json>`(必須): JSON形式の設定ファイルのパス(詳細は下の「設定」を参照)。
- `--cheat`(任意): ピアレビュー用のチートモードを有効化。

その他のMakefileターゲット:

- `make debug` — `pdb`上でゲームを実行。
- `make lint` / `make lint-strict` — `flake8` + `mypy`。
- `make test` — `pytest`によるテストスイートを実行。
- `make clean` / `make fclean` — キャッシュを削除、または仮想環境ごと削除。

**操作方法**

| キー | 動作 |
| --- | --- |
| 矢印キー / WASD | パックマンの移動 |
| Enter | メニュー項目の決定 |
| Esc | ポーズ / 戻る |
| M(ポーズ中) | メインメニューへ戻る |

**チートモード(`--cheat`)**

- 無敵: ゴーストに触れても残機が減らない。
- 初期残機+2。
- パックマンの移動速度1.5倍。
- `F`: 全ゴーストの凍結/解除をトグル。
- `N`: 現在のレベルを即座にクリア。

**ゲームの目的**

レベル内の全てのパグムを食べればクリア。スーパーパグムを食べると数秒間全ゴースト
が食べられる状態(Frightened)になり、その間に触れるとボーナス得点でゴーストを
倒せる。通常状態のゴーストに触れると残機が1減り、残機が0になるとゲームオーバー。
全レベルをクリアするとゲームクリア。

### 設定

ゲームはコマンドライン引数として渡す1つのJSONファイルで設定する(具体例は
`config.json`を参照)。`#`で始まる行はコメントとしてパース前に除去される。
未知のキーは無視され、値が欠落・不正な場合は安全なデフォルト値へフォールバック
した上でコンソールにメッセージを出力する — 設定ファイルが壊れていてもゲームは
クラッシュしない。

| キー | 型 | デフォルト | 意味 |
| --- | --- | --- | --- |
| `highscore_filename` | string | `"highscores.json"` | ハイスコア表の保存先ファイル。 |
| `seed` | int | `42` | レベル1の迷路を生成する固定シード。 |
| `lives` | int(≥1) | `3` | 初期残機。 |
| `level_max_time` | int(≥1) | `90` | 1レベルの制限時間(秒)。超えると残機が1減る。 |
| `pacgum` | int(≥1) | `42` | 1レベルあたりの通常パグムの目標個数(実際に配置できる通路数でクランプされる)。 |
| `points_per_pacgum` | int(≥0) | `10` | 通常パグムを食べた時の得点。 |
| `points_per_super_pacgum` | int(≥0) | `50` | スーパーパグムを食べた時の得点。 |
| `points_per_ghost` | int(≥0) | `200` | イジケ状態のゴーストを食べた時の得点。 |
| `level` | `{id, width, height}`の配列 | — | レベルごとの迷路サイズ。 |

`level`配列は変更したい分だけ書けばよく、`src/parse.py`の`DEFAULT_LEVELS`により
自動的に最低10レベルまで補完される。レベル1は常に固定`seed`で生成され、以降の
レベルはランダムシードで生成される。

### ハイスコア

`src/highscore.py`が外部ライブラリに依存しない永続化処理を実装している。

- `highscore_filename`で指定したパスに`{"name": ..., "score": ...}`のJSON配列
  として保存する。
- 保持するのは上位10件のみ。同点の場合は先に記録された方を優先する。
- プレイヤー名は半角英数字とスペースのみ、1〜10文字。
- ゲーム起動時に一度読み込み、新しいスコアが登録されるたびに保存し直す
  (一時ファイル＋`os.replace`によるアトミックな書き込み)。
- ファイルの欠損・JSONの破損・不正なエントリがあってもクラッシュせず、
  メッセージを出力した上で空のテーブルにフォールバックする。
- ゲームオーバー/勝利画面で名前入力を求め、更新後の上位10件を表示する。

### 迷路生成

迷路は他チームから割り当てられた外部パッケージ`A-Maze-ing`(`mazegenerator`、
`package/`内のwheelとして配布)を改変せずに使用して生成する。`src/maze_loader.py`
がこれをラップしている。

- `MazeLoader`は`MazeGenerator(size=(width, height), perfect=False, seed=seed)`
  を呼び出し、完全な木構造ではなくループを含む迷路を生成させる(パックマンの
  要件に合わせるため)。
- `get_binary_grid()`は、ジェネレータのコンパクトなセル/壁ビットマスク表現を
  `0`/`1`のグリッド(`0`=通路、`1`=壁)に変換し、ゲーム側はこれをそのまま使う。
- `find_center_start_position()` / `find_corner_positions()`は、迷路の中心
  (パックマンの出現・リスポーン地点)と四隅(ゴーストの出現地点、かつ
  スーパーパグムの設置位置)に最も近い通路セルを求める。
- レベル1はConfigの固定`seed`で生成し、以降のレベルは`seed=0`を渡す
  (ジェネレータは`seed<=0`の時に真の乱数を使う仕様)。
- 生成される迷路は外周が必ず壁になるため、`Display._load_level()`はパックマン
  の出現行をまるごと開通させて**ワープトンネル**にしている。この行の端まで
  到達すると反対側へテレポートする(`Display._apply_tunnel_wrap`)。

### 実装

主要モジュール(おおよそ依存順):

- `src/enums.py` — `GameState`、`Direction`、`GhostMode`、`GhostType`。
- `src/parse.py` — バリデーション付きの`pydantic`モデル`Config`と、コメント除去
  ・キー単位フォールバック対応のJSONローダー`Parsing`。
- `src/maze_loader.py` — 外部迷路生成パッケージのラッパー(詳細は「迷路生成」)。
- `src/character/base.py` — 移動・当たり判定の物理演算を共有する`Character`
  (マス目未満の移動、共通の当たり判定半径による壁衝突、コーナーカット)。
- `src/character/pacman.py` — `Character`の上にプレイヤー入力の予約処理を追加。
- `src/character/ghost.py` — `Ghost`基底クラス。ターゲットマスへのBFS経路探索、
  行ったり来たり防止の短期記憶、`GhostMode`のステートマシン(Scatter/Chase/
  Frightened/Eaten)とモードごとの速度変化を持つ。
- `src/character/{blinky,pinky,inky,clyde}.py` — 各ゴーストの個性。Chaseモード
  時のターゲットマスを決めるだけに専念しており、モード切替自体は基底クラスの
  責務。
- `src/pacgum.py` — `Pacgum`。迷路の通路セル(出現地点と四隅を除く)にパグム/
  スーパーパグムを配置し、残数を管理する。
- `src/highscore.py` — 上位10件の永続化(詳細は「ハイスコア」)。
- `src/game_state.py` — `PacmanGameContext`。スコア・残機・タイマー・現在の
  `GameState`・チートフラグを保持する。
- `src/graphic/display.py` — `Display`。pygameウィンドウ、メインループ、状態
  ごとの描画(メニュー/ハイスコア/操作説明/イン・ゲーム/ポーズ/ゲームオーバー
  ・勝利)、Scatter/Chaseスケジュールとイジケタイマー、当たり判定、HUD、
  チートモードの効果を担う。
- `pac-man.py` — CLIエントリポイント(`argparse`)。パース済みの`Config`を
  `PacmanGameContext`に組み込み、`Display`に渡す。

### ソフトウェア全体構成

ゲームループを1ファイルに詰め込むのではなく、単体でテスト可能な小さな部品を
組み合わせる構成にしている。

- **`Character` → `Pacman` / `Ghost`**: 移動の物理演算は基底クラスに一箇所だけ
  実装し、`Ghost`がAIを追加、4種のゴーストはそれぞれ`determine_direction`と
  いう1つのメソッドだけをオーバーライドして個性を表現する。挙動の違いが移動
  処理そのものに影響しない構造。
- **`GameState`(enum)が`Display.run()`を駆動する**: 各画面(メニュー/
  ハイスコア/操作説明/イン・ゲーム/ポーズ/ゲームオーバー・勝利)は
  `_handle_..._event` / `_render_...`のペアとして実装され、現在の`GameState`
  で振り分けられる。フラグを分散させず、状態遷移を明示的に保つ設計。
- **`PacmanGameContext`**は、`Display`の再構築(レベル遷移など)をまたいで
  残す必要がある値(スコア・残機・タイマー・チートフラグ)を一手に持つ。
- **ゲームプレイ系は継承より合成**: `MazeLoader`・`Pacgum`・`HighScoreSystem`
  はそれぞれ単一責務の独立したクラスで、`Display`が毎フレーム協調させる形。
  巨大な1クラスに機能を詰め込まない。
- **Config検証を一箇所に集約**: `pydantic`が`Config`内でフィールドの型・範囲を
  一括検証し、`Parsing`が「壊れた設定ファイルは例外を投げずに安全な
  デフォルトへ縮退する」ことを保証する。
- 全モジュールに型ヒントを付与し、`mypy --disallow-untyped-defs
  --check-untyped-defs`(および`mypy --strict`)と`flake8`でチェックしている。
  それぞれ`make lint` / `make lint-strict`に組み込み済み。

### プロジェクト管理

プロジェクト管理の記録は`management/`ディレクトリにまとめている。

- `management/TASK.md` — 要件の全洗い出しと、Done/Todoの進捗状況。
- `management/gant.md` — 日ごとの作業ログと、2人のメンバー間のタスク分担・
  タイミングを示すMermaid製ガントチャート。
- Git履歴そのものが反復的な開発の証跡になっており、AIを活用したレビュー・
  バグ修正の記録も含まれている(詳細は下の「参考資料」)。

### 参考資料

**AIの使用目的**

本プロジェクトは開発全体を通じて**Claude Code**(Anthropic製)をペア
プログラミング・コードレビューのツールとして積極的に活用した。単発の修正
だけでなく、以下のような形で使用している。

- コードベースをレビューしてバグを修正(ゴーストAIの無限ループ、`NameError`
  のタイポ、崩れたテスト、config のデフォルト値不整合、壁の当たり判定と
  描画のズレ、など)。
- サブシステムを一から設計・実装(パグムの配置・回収、ゴーストのモード切替、
  ゴーストとの接触判定、ワープトンネル、イン・ゲームHUD、チートモードの
  効果など)。
- 付随する単体テストの作成・更新。

AIを使った変更は全てGit履歴から確認でき、`management/TASK.md` /
`management/gant.md`にも要約している。

**パックマン本家の参考資料**

- [パックマン 解析プログラム動画から見る 追跡アルゴリズム](https://www.webcyou.com/?p=10440)
  — パックマン自体のアルゴリズムなどの勉強。
- [追跡アルゴリズムを考える パックマンをJavaScript/TypeScriptでつくる (その5)](https://lets-csharp.com/pacman-js-approach/)
