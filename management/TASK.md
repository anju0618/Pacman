# Packman Project - Task Breakdown & Status

本ドキュメントは、「Packman」プロジェクトの仕様書（Subject）に基づき、必要な役割・タスクをすべて洗い出し、現在の進行状況（Done / Todo）を整理したものです。

---

## 🟢 Done（すでに完了・実装済みのタスク）

- [x] コードレビューで発覚したバグの修正一式（2026-08-08）
  - Ghost AI（`ghoast.py`→`ghost.py`）の `NameError`（タイポ）修正、`get_available_directions` の新設、`Blinky.determine_direction` の未実装ロジックを実装
  - `tests/test_game_state.py` を `PacmanGameContext` の実装に合わせて修正し、pytest全件成功に復旧
  - `Config`（`parse.py`）のデフォルト値不整合（`lives`）を修正、コメント除去処理をJSON文字列リテラル対応に変更、設定バリデーションをフィールド単位の安全なデフォルトへのフォールバック方式に変更
  - パックマンの初期位置を迷路中央（連結された通路セル）に修正し、壁の当たり判定半径と描画半径を統一して「壁にめり込んで見える」表示バグを修正
  - `--cheat` フラグを `game_context.is_cheat_mode_active` に反映
  - `MazeLoader` の迷路二重生成を解消し、レベル1のみ固定シード・以降はランダムシードに対応
  - `flake8` / `mypy`（Makefileの`lint`ターゲット指定オプション）のエラーをすべて解消
- [x] プロジェクトの初期環境構築（`uv`、`pyproject.toml`、仮想環境、ディレクトリ構造）
- [x] Makefile の自動化設定（`install`、`run`、`debug`、`clean`、`lint`、`lint-strict`）
- [x] 静的解析・型チェック環境の整備（`flake8`、`mypy --strict` 対応、コード全体の型ヒント付与）
- [x] ゲームステータス・Enum（`GameState`、`Direction`、`GhostMode`、`GhostType` など）の定義
- [x] 外部迷路生成パッケージ（A-Maze-ing）のローダー実装（`perfect=False` 対応）と単体テスト
- [x] プロジェクト管理の土台作成（Git履歴の管理、カンバン、ガントチャートの雛形作成）
- [x] パックマンの4方向移動・壁判定・キー入力（`Character.move_forward`, `pac-man.py`のpygameループ）の基礎実装（2026-08-10）
- [x] 矢印キーに加えWASDでの移動入力に対応（`display.py`のイベント処理、takawaka実装・2026-08-10）
- [x] 4匹のゴースト（Blinky/Pinky/Inky/Clyde）のクラス実装と、四隅からの出現・ゲームループへの統合（`display.py`でのゴースト生成・`update`呼び出し・描画、2026-08-10）
- [x] Config駆動のレベル進行システム（`DEFAULT_LEVELS`による最低10レベルの補完、`Display.advance_to_next_level`でのレベル遷移、`level`をdict形式で保持、takawaka実装・2026-08-10）
- [x] ゴーストAIのバグ修正一式（2026-08-10、Claude Codeによるレビュー・修正）
  - パックマンが静止している時、ゴーストが迷路内の小さなループ通路を無限に周回し続けて「行ったり来たり」に見えるバグを修正。原因は(1)`Ghost.update`が毎フレームAI判断をやり直していたため交差点でない場所でも判断が揺れ動いていたこと、(2)直線距離だけで進む先を決める貪欲法が、目的地が動かないと小さな環状通路を永久にループしてしまう性質を持っていたこと。(1)は「新しいマスに入った時だけ判断する」ように変更、(2)は直近に通ったマスへは行き止まりでない限り戻らないようにする短期記憶を追加して解消（`src/character/ghost.py`）
  - Inky（水色）のターゲット計算が本家Wikiの仕様と異なっていたバグを修正。旧実装は「パックマン前方2マスの基準点」をそのままターゲットにしていたが、本家は「Blinkyの現在地から基準点へのベクトルを2倍延長した先のマス」（`target = 2 * pivot - blinky_pos`）が正しい仕様。Blinkyの位置を参照できるよう`Ghost.update`/`determine_direction`のシグネチャに`ghosts`（全ゴーストのリスト）を追加し、Inkyがその中からBlinkyを検索して計算するよう修正（`src/character/inky.py`、`specification/specification_original.md`は元々正しい記述だったため今回はコード側を仕様に合わせた）
  - 上記の回帰テストを追加（`tests/test_ghost.py`）

---

## 📋 Todo（これから実装するタスク一覧）

### 1. 設定ファイル（Config）関連
- [x] JSON設定ファイルのパーサー実装（`#` などのコメント行を無視する仕様の対応）
- [x] 不正値や欠損値に対する堅牢なバリデーションと、安全なデフォルト値へのフォールバック処理

### 2. ハイスコアシステム
- [ ] JSON等を用いたハイスコアの永続化（ロード・セーブ機能）※`config.json`に`highscore_filename`項目はあるが読み書き未実装
- [ ] トップ10のランキング管理と、プレイヤー名（最大10文字、英数字・スペースのみ）のバリデーション
- [ ] ゲーム終了時（Win/Lose）の名前入力・スコア記録プロンプトの実装

### 3. グラフィック ＆ メインループ
- [x] グラフィックライブラリの選定・導入（pygame）
- [x] ウィンドウ描画とゲームのメインループの基礎構築（`src/graphic/display.py`：壁描画・イベント処理・pacman描画）
- [ ] UI / HUD の実装（メインメニュー、ポーズ画面、ゲームオーバー／勝利画面、インゲームHUD：スコア・残機・レベル・残り時間）※現状スコア等は`game_state.py`にあるが画面に未表示

### 4. ゲームプレイ・ロジック（プレイヤー＆迷路）
- [x] プレイヤーの4方向移動・壁判定（`Character.move_forward`、Uターン許容ロジック含む）
- [x] 複数レベル（Configで指定、最低10レベルに自動補完）の進行の土台（`Display.advance_to_next_level`、takawaka実装）
- [ ] ワープトンネルの処理（迷路端での折り返し）※未実装、現状は端も壁扱い
- [ ] パグム（小ドット）とスーパーパグム（パワーペレット）の配置・回収・スコア加算処理（未着手、`add_score`の呼び出し元がまだない）
- [ ] レベルクリア判定（`Display.is_cleared`が常に`False`固定で未実装）と制限時間管理

### 5. ゴーストAIとキャラクター挙動
- [x] Blinky（追跡ゴースト）のターゲット計算・方向決定ロジック（`Ghost`基底クラス＋`Blinky.determine_direction`）
- [x] Blinky以外の3匹（Pinky/Inky/Clyde）のクラス実装（Pinky: takawaka実装、Clyde: Anjou実装、Inkyのターゲット計算は2026-08-10にClaude Codeが本家Wiki仕様に合わせて修正）
- [x] ゴーストのゲームループへの統合（`display.py`で4体を生成・`update`・描画）
- [x] 4匹のゴーストの四隅からの出現ロジック（`MazeLoader.find_corner_positions`）
- [x] ゴーストAIの判断タイミングを「新しいマスに入った瞬間」に限定し、直近訪問マスへの回帰を避ける短期記憶を追加（無限ループ・振動対策、2026-08-10）
- [ ] 追跡モード（Chase）／縄張り巡回（Scatter）／イジケモード（Frightened：スーパーパグム吃食後）／リスポーン（Eaten）の切り替えAI（現状`GhostMode`はSCATTER固定で未切り替え）
- [ ] ゴーストとプレイヤーの接触判定（残機減少、中央リスポーン、ゲームオーバー判定）

### 6. チートモード
- [ ] ピアレビュー用のチート機能実装（無敵、レベルスキップ、ゴースト停止、残機増加など）※`--cheat`フラグと`is_cheat_mode_active`は存在するが効果は未実装

### 7. テスト・ドキュメント・パッケージング
- [ ] テストの拡充（pytestによる単体テスト・結合テストの追加）
- [ ] README.md の執筆（指定の1行目斜体、Configuration、Highscore、Maze Generation、Implementation、Architecture、Project Management、AI使用目的等の必須セクション網羅）
- [ ] パブリックプラットフォーム（Steam / Itch.io等）へのデプロイに向けたパッケージング・ビルドの確認
