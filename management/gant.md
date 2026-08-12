2026
0806 amakino enums.py game_state.py maze_loader.py作成
0806 takawaka 書いて！！後でAIにまとめさせよう！！
0807 amakino バグ修正、configデータ格納　キャラクタのbasemodell class開始
0808 amakino blinkyとかpacmanのクラス作ってて、順番違うなって気づいて中断。グラッフィック開始。　config.jsonのコメントアウト全対応を試みる(reを使用)
0808 amakino Claude Codeにレビューさせてバグ一斉修正。ghoast.pyのNameError、blinky未実装、テスト崩壊、config.livesデフォルト不整合、コメント除去の文字列破壊、config検証の全滅フォールバック、パックマン初期位置が真ん中じゃない、壁にめり込む表示バグ(当たり判定と描画の半径不一致)など。flake8/mypy/pytest全部通るようになった。
0810 amakino 進捗棚卸し。pygameでのメインループ・パックマン4方向移動＆壁判定は動く状態。Blinkyの追跡ロジックは実装済みだがまだdisplay.pyのループに1体も出現させてない（統合待ち）。ドット/パワーペレット・スコア加算・ハイスコア永続化・HUD・ゴースト接触判定は未着手。Windows側の改行コード(CRLF)がまざってた分をコミットで正規化。次はBlinky統合→残り3体のゴースト実装→モード切替の順で着手予定。
ピンキー作った
0810 amakino Clyde実装、display.pyにゴースト4体を統合（四隅出現・毎フレームupdate・描画）
0810 takawaka WASD移動対応、Configでレベルごとの幅・高さを指定できるレベル進行の仕組みを追加（DEFAULT_LEVELSで最低10レベルに自動補完、Display.advance_to_next_levelでレベル遷移）
0812 takawaka ghostの動きを改善し個性に合わせしっかりと追跡するようにした。pacmanの動きを改善


```mermaid
gantt
    title Packman Project Timeline - Member Work Division & Tasks
    dateFormat  YYYY-MM-DD

    section Anjou Makino (amakino)
    Project Setup (uv, toml, Makefile) :done, a1, 2026-08-06, 2026-08-06
    Specification & Research           :done, a2, 2026-08-06, 2026-08-06
    Enums & Game State Implementation  :done, a3, 2026-08-06, 2026-08-06
    Maze Loader & Test Suite           :done, a4, 2026-08-06, 2026-08-06
    Player Movement & Collision        :done, a5, 2026-08-07, 2026-08-10
    Ghost Integration (4体・四隅出現)   :done, a5b, 2026-08-10, 2026-08-10
    Warp Tunnel                        :        a5c, 2026-08-11, 2026-08-12
    Ghost AI Bugfix (振動・Inky)        :done, a6a, 2026-08-10, 2026-08-10
    Ghost AI & Behavior Logic (Mode切替) :active, a6, 2026-08-10, 2026-08-14
    Level Progression & Rules          :active, a7, 2026-08-10, 2026-08-16

    section Taiyo Kawakami (takawaka)
    Config Parser (JSON w/ comments)   :done, t1, 2026-08-06, 2026-08-07
    Config Validation & Fallback       :done, t2, 2026-08-06, 2026-08-07
    WASD Input                         :done, t2b, 2026-08-10, 2026-08-10
    Config-driven Level Progression    :done, t2c, 2026-08-10, 2026-08-10
    Highscore System (Persistence)     :crit, t3, 2026-08-08, 2026-08-12
    Cheat Mode Implementation          :        t4, 2026-08-12, 2026-08-14

    section Collaborative / Both
    Graphic Library & Window Setup     :done, j1, 2026-08-08, 2026-08-10
    Dots, Pellets & Scoring            :        j1b, 2026-08-10, 2026-08-12
    Game Loop & UI/HUD Integration     :        j2, 2026-08-12, 2026-08-16
    Testing, README & Packaging        :        j3, 2026-08-15, 2026-08-19
```
